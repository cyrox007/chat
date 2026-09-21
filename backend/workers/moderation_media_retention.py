import argparse
import asyncio
from pathlib import Path

from components.model_registry import ensure_models_registered
from components.moderation.media_retention import expire_due_media_evidence
from database import Database
from settings import config
from utils.logger import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Expire due private Trust & Safety media evidence.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=config.MODERATION_MEDIA_RETENTION_BATCH_SIZE,
        help="Maximum due evidence records processed in one run.",
    )
    return parser


async def run(batch_size: int) -> int:
    ensure_models_registered()
    config.ensure_moderation_media_retention_settings()
    try:
        async with Database.sessionmaker()() as db:
            stats = await expire_due_media_evidence(
                db,
                batch_size=batch_size,
                private_root=Path(config.MODERATION_MEDIA_ROOT),
            )
        logger.info(
            "Moderation media retention complete: candidates=%s purged=%s "
            "already_missing=%s deferred_active_report=%s "
            "deferred_pending_appeal=%s failed=%s",
            stats.candidates,
            stats.purged,
            stats.already_missing,
            stats.deferred_active_report,
            stats.deferred_pending_appeal,
            stats.failed,
        )
        return 1 if stats.failed else 0
    finally:
        await Database.dispose()


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(run(args.batch_size))


if __name__ == "__main__":
    raise SystemExit(main())
