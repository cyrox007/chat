import argparse
import asyncio
import json

from components.realtime.pool_metrics import run_realtime_pool_profile
from components.realtime.service import RealtimeService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a bounded privacy-safe realtime Redis pool profile.",
    )
    parser.add_argument("--operations", type=int, default=120)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--max-error-rate-percent", type=float, default=0.0)
    parser.add_argument("--max-p95-ms", type=float, default=2000.0)
    parser.add_argument("--max-saturation-samples", type=int, default=0)
    parser.add_argument(
        "--require-healthy",
        action="store_true",
        help="Exit non-zero when configured profile gates are exceeded.",
    )
    return parser


async def run(args: argparse.Namespace) -> int:
    service = RealtimeService()
    try:
        await service.start()
        if not service.distributed:
            print(json.dumps({"status": "error", "error": "redis_not_connected"}))
            return 3

        report = await run_realtime_pool_profile(
            service,
            operations=args.operations,
            concurrency=args.concurrency,
        )
        violations = []
        if report["error_rate_percent"] > max(0.0, args.max_error_rate_percent):
            violations.append("error_rate")
        if report["latency_ms"]["p95"] > max(1.0, args.max_p95_ms):
            violations.append("p95_latency")
        if report["pool"]["saturation_samples"] > max(0, args.max_saturation_samples):
            violations.append("pool_saturation")

        report["gates"] = {
            "max_error_rate_percent": max(0.0, args.max_error_rate_percent),
            "max_p95_ms": max(1.0, args.max_p95_ms),
            "max_saturation_samples": max(0, args.max_saturation_samples),
            "healthy": not violations,
            "violations": violations,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        if args.require_healthy and violations:
            return 2
        return 0
    finally:
        await service.stop()


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
