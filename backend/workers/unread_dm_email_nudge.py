import argparse
import asyncio

from components.model_registry import ensure_models_registered
from components.notification.unread_dm_email import (
    DEFAULT_MAX_BATCHES,
    DEFAULT_WORKER_BATCH_SIZE,
    MAX_WORKER_BATCHES,
    MAX_WORKER_BATCH_SIZE,
    run_email_delivery_worker,
    run_email_nudge_worker,
)
from components.realtime import realtime_service
from database import Database
from settings import config
from utils.logger import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Queue and deliver privacy-safe unread-Messenger email nudges.",
    )
    parser.add_argument(
        "--stage",
        choices=("queue", "deliver", "all"),
        default="all",
        help="Run candidate queueing, SMTP delivery, or both.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_WORKER_BATCH_SIZE,
        help=f"Accounts per candidate page (1..{MAX_WORKER_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=DEFAULT_MAX_BATCHES,
        help=f"Maximum candidate pages per run (1..{MAX_WORKER_BATCHES}).",
    )
    parser.add_argument(
        "--delivery-batch-size",
        type=int,
        default=config.MESSAGE_EMAIL_DELIVERY_BATCH_SIZE,
        help="Maximum durable delivery records claimed in this run.",
    )
    return parser


async def run(stage: str, batch_size: int, max_batches: int, delivery_batch_size: int) -> int:
    ensure_models_registered()
    exit_code = 0
    try:
        if stage in {"queue", "all"}:
            queue_stats = await run_email_nudge_worker(
                Database.sessionmaker(),
                batch_size=batch_size,
                max_batches=max_batches,
            )
            logger.info(
                "Unread-DM email queue complete: ready=%s acquired=%s batches=%s seen=%s queued=%s skipped=%s failed=%s",
                queue_stats.infrastructure_ready,
                queue_stats.acquired,
                queue_stats.batches,
                queue_stats.accounts_seen,
                queue_stats.queued,
                queue_stats.skipped,
                queue_stats.failed,
            )
            if not queue_stats.infrastructure_ready:
                exit_code = max(exit_code, 2)
            elif queue_stats.failed:
                exit_code = max(exit_code, 1)

        if stage in {"deliver", "all"}:
            delivery_stats = await run_email_delivery_worker(
                Database.sessionmaker(),
                batch_size=delivery_batch_size,
            )
            logger.info(
                "Unread-DM email delivery complete: ready=%s claimed=%s delivered=%s retried=%s failed=%s suppressed=%s deferred_online=%s",
                delivery_stats.infrastructure_ready,
                delivery_stats.claimed,
                delivery_stats.delivered,
                delivery_stats.retried,
                delivery_stats.failed,
                delivery_stats.suppressed,
                delivery_stats.deferred_online,
            )
            if not delivery_stats.infrastructure_ready:
                exit_code = max(exit_code, 2)
            elif delivery_stats.failed:
                exit_code = max(exit_code, 1)

        return exit_code
    finally:
        await realtime_service.stop()
        await Database.dispose()


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(
        run(
            args.stage,
            args.batch_size,
            args.max_batches,
            args.delivery_batch_size,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
