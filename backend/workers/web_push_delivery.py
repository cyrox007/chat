import argparse
import asyncio

from components.model_registry import ensure_models_registered
from components.notification.web_push import run_web_push_delivery_worker
from components.realtime import realtime_service
from database import Database
from settings import config
from utils.logger import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deliver privacy-minimal Messenger Web Push notifications.",
    )
    parser.add_argument(
        "--max-deliveries",
        type=int,
        default=config.WEB_PUSH_DELIVERY_BATCH_SIZE,
        help="Maximum durable delivery records processed in this run (1..250).",
    )
    return parser


async def run(max_deliveries: int) -> int:
    ensure_models_registered()
    config.ensure_web_push_settings()
    try:
        stats = await run_web_push_delivery_worker(
            Database.sessionmaker(),
            max_deliveries=max_deliveries,
        )
        logger.info(
            "Web Push worker complete: ready=%s claimed=%s delivered=%s retried=%s failed=%s suppressed=%s terminal_removed=%s",
            stats.infrastructure_ready,
            stats.claimed,
            stats.delivered,
            stats.retried,
            stats.failed,
            stats.suppressed,
            stats.terminal_subscriptions_removed,
        )
        if not stats.infrastructure_ready:
            return 2
        return 1 if stats.failed else 0
    finally:
        await realtime_service.stop()
        await Database.dispose()


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(run(max(1, min(int(args.max_deliveries), 250))))


if __name__ == "__main__":
    raise SystemExit(main())
