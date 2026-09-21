import argparse
import asyncio
import json

from components.model_registry import ensure_models_registered
from components.moderation.automation_settings import moderation_automation_config
from components.moderation.calibration import protective_hold_calibration_summary
from database import Database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report human-reviewed protective-hold calibration quality.",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Human-label/evaluation window, bounded to 1-365 days.",
    )
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Exit non-zero unless the data calibration gate is ready.",
    )
    return parser


async def run(window_days: int, require_ready: bool) -> int:
    ensure_models_registered()
    try:
        async with Database.sessionmaker()() as db:
            summary = await protective_hold_calibration_summary(
                db,
                config=moderation_automation_config,
                window_days=window_days,
            )
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        if require_ready and not summary["data_ready"]:
            return 2
        return 0
    finally:
        await Database.dispose()


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(run(args.window_days, args.require_ready))


if __name__ == "__main__":
    raise SystemExit(main())
