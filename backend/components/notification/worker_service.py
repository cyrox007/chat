from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from components.identity.model import Account
from components.notification.model import ActivityReminderPreference
from components.notification.service import sync_activity_reminders
from utils.logger import setup_logger


logger = setup_logger(__name__)

DEFAULT_WORKER_BATCH_SIZE = 100
MAX_WORKER_BATCH_SIZE = 250
DEFAULT_MAX_BATCHES = 20
MAX_WORKER_BATCHES = 100


@dataclass
class ReminderWorkerStats:
    batches: int = 0
    accounts_seen: int = 0
    accounts_synced: int = 0
    accounts_failed: int = 0


async def reminder_account_page(
    db: AsyncSession,
    *,
    after_uid: UUID | None = None,
    limit: int = DEFAULT_WORKER_BATCH_SIZE,
) -> list[UUID]:
    bounded_limit = max(1, min(int(limit), MAX_WORKER_BATCH_SIZE))
    stmt = (
        select(ActivityReminderPreference.account_uid)
        .join(Account, Account.uid == ActivityReminderPreference.account_uid)
        .where(
            ActivityReminderPreference.enabled.is_(True),
            Account.status == "active",
            Account.deleted_at.is_(None),
        )
        .distinct()
        .order_by(ActivityReminderPreference.account_uid.asc())
        .limit(bounded_limit)
    )
    if after_uid is not None:
        stmt = stmt.where(ActivityReminderPreference.account_uid > after_uid)

    result = await db.execute(stmt)
    return [account_uid for (account_uid,) in result.all()]


async def reconcile_reminder_accounts(
    session_factory: async_sessionmaker[AsyncSession],
    account_uids: list[UUID],
    *,
    now: datetime | None = None,
) -> tuple[int, int]:
    synced = 0
    failed = 0

    for account_uid in account_uids:
        async with session_factory() as db:
            try:
                await sync_activity_reminders(db, account_uid, now=now)
                synced += 1
            except HTTPException as exc:
                await db.rollback()
                failed += 1
                logger.warning(
                    "Reminder reconciliation skipped account %s: %s",
                    account_uid,
                    getattr(exc, "detail", exc),
                )
            except Exception:
                await db.rollback()
                failed += 1
                logger.exception("Reminder reconciliation failed for account %s", account_uid)

    return synced, failed


async def run_reminder_worker(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    batch_size: int = DEFAULT_WORKER_BATCH_SIZE,
    max_batches: int = DEFAULT_MAX_BATCHES,
    now: datetime | None = None,
) -> ReminderWorkerStats:
    bounded_batch_size = max(1, min(int(batch_size), MAX_WORKER_BATCH_SIZE))
    bounded_max_batches = max(1, min(int(max_batches), MAX_WORKER_BATCHES))

    stats = ReminderWorkerStats()
    cursor: UUID | None = None

    for _ in range(bounded_max_batches):
        async with session_factory() as index_db:
            account_uids = await reminder_account_page(
                index_db,
                after_uid=cursor,
                limit=bounded_batch_size,
            )

        if not account_uids:
            break

        stats.batches += 1
        stats.accounts_seen += len(account_uids)
        synced, failed = await reconcile_reminder_accounts(
            session_factory,
            account_uids,
            now=now,
        )
        stats.accounts_synced += synced
        stats.accounts_failed += failed
        cursor = account_uids[-1]

        if len(account_uids) < bounded_batch_size:
            break

    return stats
