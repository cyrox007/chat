import argparse
import asyncio

from components.model_registry import ensure_models_registered
from components.notification.unread_dm_email import (
    DEFAULT_MAX_BATCHES,
    DEFAULT_WORKER_BATCH_SIZE,
    MAX_WORKER_BATCHES,
    MAX_WORKER_BATCH_SIZE,
    run_email_nudge_worker,
)
from components.realtime import realtime_service
from database import Database
from utils.logger import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Queue durable unread-Messenger email nudge delivery records.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_WORKER_BATCH_SIZE,
        help=f"Accounts per page (1..{MAX_WORKER_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=DEFAULT_MAX_BATCHES,
        help=f"Maximum pages per run (1..{MAX_WORKER_BATCHES}).",
    )
    return parser


async def run(batch_size: int, max_batches: int) -> int:
    ensure_models_registered()
    try:
        stats = await run_email_nudge_worker(
            Database.sessionmaker(),
            batch_size=batch_size,
            max_batches=max_batches,
        )
        logger.info(
            "Unread-DM email nudge worker complete: ready=%s acquired=%s batches=%s seen=%s queued=%s skipped=%s failed=%s",
            stats.infrastructure_ready,
            stats.acquired,
            stats.batches,
            stats.accounts_seen,
            stats.queued,
            stats.skipped,
            stats.failed,
        )
        if not stats.infrastructure_ready:
            return 2
        return 1 if stats.failed else 0
    finally:
        await realtime_service.stop()
        await Database.dispose()


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(run(args.batch_size, args.max_batches))


if __name__ == "__main__":
    raise SystemExit(main())
