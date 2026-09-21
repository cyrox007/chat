import argparse
import logging
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
from utils.observability import log_structured


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
            log_structured(
                logger,
                logging.INFO,
                "external_delivery.email.queue_complete",
                infrastructure_ready=queue_stats.infrastructure_ready,
                acquired=queue_stats.acquired,
                batches=queue_stats.batches,
                accounts_seen=queue_stats.accounts_seen,
                queued=queue_stats.queued,
                skipped=queue_stats.skipped,
                failed=queue_stats.failed,
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
            log_structured(
                logger,
                logging.INFO,
                "external_delivery.email.delivery_complete",
                infrastructure_ready=delivery_stats.infrastructure_ready,
                claimed=delivery_stats.claimed,
                delivered=delivery_stats.delivered,
                retried=delivery_stats.retried,
                failed=delivery_stats.failed,
                suppressed=delivery_stats.suppressed,
                deferred_online=delivery_stats.deferred_online,
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
