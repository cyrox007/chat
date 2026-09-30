from __future__ import annotations

from typing import Any

from database import Database
from settings import config


def _pool_counter(pool: Any, name: str) -> int:
    value = getattr(pool, name, None)
    if not callable(value):
        return 0
    try:
        return max(0, int(value()))
    except Exception:
        return 0


def database_pool_snapshot() -> dict:
    """Return aggregate SQLAlchemy pool capacity without DB URLs or identities."""
    engine = Database.get_engine()
    pool = engine.sync_engine.pool

    pool_size = int(config.DB_POOL_SIZE)
    max_overflow = int(config.DB_POOL_MAX_OVERFLOW)
    max_connections = pool_size + max_overflow
    checked_out = _pool_counter(pool, "checkedout")
    checked_in = _pool_counter(pool, "checkedin")
    current_overflow = _pool_counter(pool, "overflow")
    headroom = max(0, max_connections - checked_out)
    utilization = (
        round((checked_out / max_connections) * 100.0, 2)
        if max_connections
        else 0.0
    )
    near_capacity = bool(
        utilization >= config.DB_POOL_ALERT_UTILIZATION_PERCENT
        or headroom <= config.DB_POOL_MIN_HEADROOM_CONNECTIONS
    )

    return {
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "max_connections": max_connections,
        "checked_out_connections": checked_out,
        "checked_in_connections": checked_in,
        "current_overflow_connections": current_overflow,
        "headroom_connections": headroom,
        "utilization_percent": utilization,
        "near_capacity": near_capacity,
    }


def database_pool_health() -> dict:
    snapshot = database_pool_snapshot()
    attention_reasons: list[str] = []
    if snapshot["near_capacity"]:
        attention_reasons.append("postgres.pool_near_capacity")

    return {
        "healthy": not attention_reasons,
        "attention_reasons": attention_reasons,
        "pool": snapshot,
        "thresholds": {
            "alert_utilization_percent": config.DB_POOL_ALERT_UTILIZATION_PERCENT,
            "min_headroom_connections": config.DB_POOL_MIN_HEADROOM_CONNECTIONS,
        },
        "privacy": {
            "contains_database_url": False,
            "contains_credentials": False,
            "contains_query_text": False,
            "contains_query_parameters": False,
            "contains_account_ids": False,
        },
    }
