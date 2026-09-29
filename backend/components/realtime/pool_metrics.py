from __future__ import annotations

import asyncio
import math
import time
from collections import Counter
from dataclasses import dataclass
from statistics import median
from typing import Any
from uuid import uuid4

from components.realtime.service import RealtimeService
from settings import config


@dataclass(slots=True)
class PoolPeak:
    in_use: int = 0
    available: int = 0
    created: int = 0
    utilization_percent: float = 0.0
    saturation_samples: int = 0


def _safe_len(value: Any) -> int:
    try:
        return len(value)
    except Exception:
        return 0


def redis_pool_snapshot(service: RealtimeService) -> dict:
    client = service.redis
    if client is None:
        return {
            "connected": False,
            "mode": service.redis_mode,
            "max_connections": int(config.REDIS_MAX_CONNECTIONS),
            "in_use_connections": 0,
            "available_connections": 0,
            "created_connections": 0,
            "headroom_connections": int(config.REDIS_MAX_CONNECTIONS),
            "utilization_percent": 0.0,
            "near_capacity": False,
        }

    pool = client.connection_pool
    max_connections = int(
        getattr(pool, "max_connections", config.REDIS_MAX_CONNECTIONS)
        or config.REDIS_MAX_CONNECTIONS
    )
    in_use = _safe_len(getattr(pool, "_in_use_connections", ()))
    available = _safe_len(getattr(pool, "_available_connections", ()))
    created = in_use + available
    headroom = max(0, max_connections - in_use)
    utilization = round((in_use / max_connections) * 100.0, 2) if max_connections else 0.0
    near_capacity = bool(
        utilization >= config.REDIS_POOL_ALERT_UTILIZATION_PERCENT
        or headroom <= config.REDIS_POOL_MIN_HEADROOM_CONNECTIONS
    )
    return {
        "connected": True,
        "mode": service.redis_mode,
        "max_connections": max_connections,
        "in_use_connections": in_use,
        "available_connections": available,
        "created_connections": created,
        "headroom_connections": headroom,
        "utilization_percent": utilization,
        "near_capacity": near_capacity,
    }


def realtime_pool_health(service: RealtimeService) -> dict:
    snapshot = redis_pool_snapshot(service)
    attention_reasons: list[str] = []
    if not snapshot["connected"]:
        attention_reasons.append("redis.not_connected")
    elif snapshot["near_capacity"]:
        attention_reasons.append("redis.pool_near_capacity")
    return {
        "healthy": not attention_reasons,
        "attention_reasons": attention_reasons,
        "pool": snapshot,
        "thresholds": {
            "alert_utilization_percent": config.REDIS_POOL_ALERT_UTILIZATION_PERCENT,
            "min_headroom_connections": config.REDIS_POOL_MIN_HEADROOM_CONNECTIONS,
        },
        "privacy": {
            "contains_redis_url": False,
            "contains_credentials": False,
            "contains_ticket_values": False,
            "contains_account_ids": False,
        },
    }


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[rank]


async def run_realtime_pool_profile(
    service: RealtimeService,
    *,
    operations: int = 120,
    concurrency: int = 12,
    sample_interval_seconds: float = 0.002,
) -> dict:
    """Exercise production realtime primitives with bounded concurrent load.

    The report is intentionally privacy-minimal: generated identifiers and Redis
    keys never leave this function. This is a staging/CI capacity rehearsal, not
    a universal throughput benchmark.
    """
    operations = max(1, min(5000, int(operations)))
    concurrency = max(1, min(500, int(concurrency)))
    sample_interval_seconds = max(0.001, min(0.1, float(sample_interval_seconds)))

    if not service.distributed:
        raise RuntimeError("Redis-backed realtime service is required for pool profiling")

    latencies_ms: list[float] = []
    errors: Counter[str] = Counter()
    completed = 0
    peak = PoolPeak()
    stop_sampling = asyncio.Event()
    semaphore = asyncio.Semaphore(concurrency)
    run_marker = uuid4().hex

    def observe() -> None:
        snapshot = redis_pool_snapshot(service)
        peak.in_use = max(peak.in_use, snapshot["in_use_connections"])
        peak.available = max(peak.available, snapshot["available_connections"])
        peak.created = max(peak.created, snapshot["created_connections"])
        peak.utilization_percent = max(
            peak.utilization_percent,
            float(snapshot["utilization_percent"]),
        )
        if snapshot["max_connections"] and (
            snapshot["in_use_connections"] >= snapshot["max_connections"]
        ):
            peak.saturation_samples += 1

    async def sampler() -> None:
        while not stop_sampling.is_set():
            observe()
            try:
                await asyncio.wait_for(
                    stop_sampling.wait(),
                    timeout=sample_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass
        observe()

    async def exercise(index: int) -> None:
        nonlocal completed
        async with semaphore:
            started = time.perf_counter()
            account_uid = uuid4()
            connection_id = f"profile-{run_marker}-{index}"
            event_id = f"profile-{run_marker}-{index}"
            try:
                ticket, _ = await service.issue_ticket(account_uid, "messenger")
                payload = await service.consume_ticket(ticket, "messenger")
                if payload is None:
                    raise RuntimeError("ticket_round_trip_failed")

                await service.register_connection(
                    connection_id,
                    account_uid,
                    "messenger",
                )
                await service.touch_connection(connection_id)
                record = await service.unregister_connection(connection_id)
                if record is None:
                    raise RuntimeError("presence_round_trip_failed")

                claimed = await service.claim_event(
                    account_uid,
                    "pool-profile",
                    event_id,
                    ttl_seconds=30,
                )
                if not claimed:
                    raise RuntimeError("idempotency_claim_failed")
                await service.release_event(
                    account_uid,
                    "pool-profile",
                    event_id,
                )
                completed += 1
            except Exception as exc:
                errors[type(exc).__name__] += 1
            finally:
                latencies_ms.append((time.perf_counter() - started) * 1000.0)
                observe()

    wall_started = time.perf_counter()
    sampler_task = asyncio.create_task(sampler(), name="redis-pool-profiler-sampler")
    try:
        await asyncio.gather(*(exercise(index) for index in range(operations)))
    finally:
        stop_sampling.set()
        await sampler_task

    wall_ms = (time.perf_counter() - wall_started) * 1000.0
    failed = operations - completed
    error_rate_percent = round((failed / operations) * 100.0, 3)
    max_connections = redis_pool_snapshot(service)["max_connections"]

    return {
        "operations": operations,
        "concurrency": concurrency,
        "completed": completed,
        "failed": failed,
        "error_rate_percent": error_rate_percent,
        "wall_ms": round(wall_ms, 2),
        "throughput_operations_per_second": round(
            operations / max(wall_ms / 1000.0, 0.001),
            2,
        ),
        "latency_ms": {
            "p50": round(median(latencies_ms), 2) if latencies_ms else 0.0,
            "p95": round(_percentile(latencies_ms, 0.95), 2),
            "p99": round(_percentile(latencies_ms, 0.99), 2),
            "max": round(max(latencies_ms), 2) if latencies_ms else 0.0,
        },
        "pool": {
            "max_connections": max_connections,
            "peak_in_use_connections": peak.in_use,
            "peak_created_connections": peak.created,
            "peak_available_connections": peak.available,
            "peak_utilization_percent": round(peak.utilization_percent, 2),
            "saturation_samples": peak.saturation_samples,
        },
        "error_types": dict(sorted(errors.items())),
        "privacy": {
            "contains_redis_url": False,
            "contains_credentials": False,
            "contains_ticket_values": False,
            "contains_account_ids": False,
        },
    }
