import argparse
import asyncio
import json

from components.model_registry import ensure_models_registered
from components.notification.operations_metrics import external_delivery_metrics
from database import Database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report privacy-safe external delivery health.",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=24,
        help="Recent metrics window, bounded to 1..720 hours.",
    )
    parser.add_argument(
        "--require-healthy",
        action="store_true",
        help="Exit non-zero on stale due backlog or expired processing claims.",
    )
    return parser


async def run(window_hours: int, require_healthy: bool) -> int:
    ensure_models_registered()
    try:
        async with Database.sessionmaker()() as db:
            metrics = await external_delivery_metrics(
                db,
                window_hours=window_hours,
            )
        print(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True))
        if require_healthy and not metrics["healthy"]:
            return 2
        return 0
    finally:
        await Database.dispose()


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(run(args.window_hours, args.require_healthy))


if __name__ == "__main__":
    raise SystemExit(main())
