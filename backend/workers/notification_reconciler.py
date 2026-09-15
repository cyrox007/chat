import argparse
import asyncio

from components.notification.worker_service import (
    DEFAULT_MAX_BATCHES,
    DEFAULT_WORKER_BATCH_SIZE,
    MAX_WORKER_BATCHES,
    MAX_WORKER_BATCH_SIZE,
    run_reminder_worker,
)
from database import Database
from utils.logger import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile PubChat Activity reminders into the private notification inbox.",
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
    try:
        stats = await run_reminder_worker(
            Database.sessionmaker(),
            batch_size=batch_size,
            max_batches=max_batches,
        )
        logger.info(
            "Reminder worker complete: batches=%s seen=%s synced=%s failed=%s",
            stats.batches,
            stats.accounts_seen,
            stats.accounts_synced,
            stats.accounts_failed,
        )
        return 1 if stats.accounts_failed else 0
    finally:
        await Database.dispose()


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(run(args.batch_size, args.max_batches))


if __name__ == "__main__":
    raise SystemExit(main())
