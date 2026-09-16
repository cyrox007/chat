from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from components.identity.model import Account, AccountRelationship, Credential, Persona, PrivacySettings
from components.message.model import PrivateMessage
from components.notification.model import (
    ExternalDeliveryLedger,
    MessageNotificationPreference,
    NotificationWorkerState,
)
from components.realtime import realtime_service
from components.room.model import RoomMember
from components.user.model import User
from settings import config
from utils.logger import setup_logger


logger = setup_logger(__name__)

WORKER_NAME_UNREAD_DM_EMAIL = "unread-dm-email-nudge"
DELIVERY_CHANNEL_EMAIL = "email"
DEFAULT_WORKER_BATCH_SIZE = 100
MAX_WORKER_BATCH_SIZE = 250
DEFAULT_MAX_BATCHES = 20
MAX_WORKER_BATCHES = 100
MAX_UNREAD_MESSAGES_PER_ACCOUNT = 500


@dataclass
class EmailNudgeWorkerStats:
    acquired: bool = False
    infrastructure_ready: bool = False
    wrapped: bool = False
    batches: int = 0
    accounts_seen: int = 0
    queued: int = 0
    skipped: int = 0
    failed: int = 0


def utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def cooldown_slot(now: datetime, cooldown_minutes: int) -> int:
    seconds = max(60, int(cooldown_minutes) * 60)
    normalized = utc_naive(now).replace(tzinfo=timezone.utc)
    return int(normalized.timestamp()) // seconds


def email_nudge_dedupe_key(latest_message_uid: UUID | str, now: datetime, cooldown_minutes: int) -> str:
    return f"unread-dm:{latest_message_uid}:slot:{cooldown_slot(now, cooldown_minutes)}"


def should_queue_again(
    *,
    previous_aggregate_key: str | None,
    previous_created_at: datetime | None,
    aggregate_key: str,
    now: datetime,
    cooldown_minutes: int,
) -> bool:
    if not previous_aggregate_key or previous_created_at is None:
        return True
    if previous_aggregate_key != aggregate_key:
        return True
    cooldown = timedelta(minutes=max(60, int(cooldown_minutes)))
    return utc_naive(now) - utc_naive(previous_created_at) >= cooldown


async def _external_dm_delivery_allowed(
    db: AsyncSession,
    sender_uid: UUID,
    receiver_uid: UUID,
) -> bool:
    """Re-check current Account block/privacy rules before external re-engagement."""
    if sender_uid == receiver_uid:
        return True

    blocked = await db.execute(
        select(AccountRelationship.id)
        .where(
            AccountRelationship.relation_type == "block",
            or_(
                and_(
                    AccountRelationship.from_account_uid == sender_uid,
                    AccountRelationship.to_account_uid == receiver_uid,
                ),
                and_(
                    AccountRelationship.from_account_uid == receiver_uid,
                    AccountRelationship.to_account_uid == sender_uid,
                ),
            ),
        )
        .limit(1)
    )
    if blocked.scalar_one_or_none() is not None:
        return False

    policy_result = await db.execute(
        select(PrivacySettings.dm_policy)
        .join(Persona, Persona.uid == PrivacySettings.persona_uid)
        .where(
            Persona.account_uid == receiver_uid,
            Persona.is_primary.is_(True),
        )
        .limit(1)
    )
    dm_policy = policy_result.scalar_one_or_none() or "shared_spaces"
    if dm_policy == "everyone":
        return True
    if dm_policy == "nobody":
        return False

    if dm_policy == "mutual":
        reciprocal = await db.execute(
            select(func.count(AccountRelationship.id)).where(
                AccountRelationship.relation_type == "friend",
                or_(
                    and_(
                        AccountRelationship.from_account_uid == sender_uid,
                        AccountRelationship.to_account_uid == receiver_uid,
                    ),
                    and_(
                        AccountRelationship.from_account_uid == receiver_uid,
                        AccountRelationship.to_account_uid == sender_uid,
                    ),
                ),
            )
        )
        return (reciprocal.scalar_one() or 0) >= 2

    if dm_policy == "shared_spaces":
        shared_space = await db.execute(
            select(RoomMember.room_uid)
            .where(
                RoomMember.user_uid.in_([sender_uid, receiver_uid]),
                RoomMember.is_banned.is_(False),
            )
            .group_by(RoomMember.room_uid)
            .having(func.count(func.distinct(RoomMember.user_uid)) >= 2)
            .limit(1)
        )
        return shared_space.scalar_one_or_none() is not None

    return False


async def email_nudge_account_page(
    db: AsyncSession,
    *,
    now: datetime,
    after_uid: UUID | None = None,
    limit: int = DEFAULT_WORKER_BATCH_SIZE,
) -> list[UUID]:
    bounded_limit = max(1, min(int(limit), MAX_WORKER_BATCH_SIZE))
    cutoff = utc_naive(now) - timedelta(minutes=config.MESSAGE_EMAIL_NUDGE_INACTIVITY_MINUTES)
    unread_exists = exists(
        select(PrivateMessage.id).where(
            PrivateMessage.receiver_uid == Account.uid,
            PrivateMessage.is_read.is_(False),
        )
    )

    stmt = (
        select(Account.uid)
        .join(MessageNotificationPreference, MessageNotificationPreference.account_uid == Account.uid)
        .join(User, User.uid == Account.legacy_user_uid)
        .join(
            Credential,
            and_(
                Credential.account_uid == Account.uid,
                Credential.kind == "email",
                Credential.verified_at.is_not(None),
            ),
        )
        .where(
            Account.status == "active",
            Account.deleted_at.is_(None),
            MessageNotificationPreference.email_unread_dm_nudge.is_(True),
            unread_exists,
            or_(
                User.last_online <= cutoff,
                and_(User.last_online.is_(None), Account.created_at <= cutoff),
            ),
        )
        .distinct()
        .order_by(Account.uid.asc())
        .limit(bounded_limit)
    )
    if after_uid is not None:
        stmt = stmt.where(Account.uid > after_uid)

    result = await db.execute(stmt)
    return [account_uid for (account_uid,) in result.all()]


async def queue_unread_dm_email_nudge(
    db: AsyncSession,
    account_uid: UUID,
    *,
    now: datetime,
) -> bool:
    """Create one privacy-minimal pending ledger item when the Account is eligible."""
    if not realtime_service.distributed and not config.DEBUG:
        return False
    if await realtime_service.is_online(account_uid):
        return False

    preference = await db.get(MessageNotificationPreference, account_uid)
    if not preference or not preference.email_unread_dm_nudge:
        return False

    verified_email = await db.execute(
        select(Credential.uid)
        .where(
            Credential.account_uid == account_uid,
            Credential.kind == "email",
            Credential.verified_at.is_not(None),
        )
        .limit(1)
    )
    if verified_email.scalar_one_or_none() is None:
        return False

    result = await db.execute(
        select(PrivateMessage)
        .where(
            PrivateMessage.receiver_uid == account_uid,
            PrivateMessage.is_read.is_(False),
        )
        .order_by(PrivateMessage.created_at.desc(), PrivateMessage.id.desc())
        .limit(MAX_UNREAD_MESSAGES_PER_ACCOUNT)
    )
    unread = list(result.scalars().all())
    if not unread:
        return False

    allowed_senders: set[UUID] = set()
    denied_senders: set[UUID] = set()
    for message in unread:
        sender_uid = UUID(str(message.sender_uid))
        if sender_uid in allowed_senders or sender_uid in denied_senders:
            continue
        if await _external_dm_delivery_allowed(db, sender_uid, account_uid):
            allowed_senders.add(sender_uid)
        else:
            denied_senders.add(sender_uid)

    eligible = [item for item in unread if UUID(str(item.sender_uid)) in allowed_senders]
    if not eligible:
        return False

    latest = eligible[0]
    current = utc_naive(now)
    aggregate_key = f"unread-dm:{latest.uid}"
    previous_result = await db.execute(
        select(ExternalDeliveryLedger.aggregate_key, ExternalDeliveryLedger.created_at)
        .where(
            ExternalDeliveryLedger.account_uid == account_uid,
            ExternalDeliveryLedger.channel == DELIVERY_CHANNEL_EMAIL,
        )
        .order_by(ExternalDeliveryLedger.created_at.desc())
        .limit(1)
    )
    previous = previous_result.first()
    if previous and not should_queue_again(
        previous_aggregate_key=previous.aggregate_key,
        previous_created_at=previous.created_at,
        aggregate_key=aggregate_key,
        now=current,
        cooldown_minutes=config.MESSAGE_EMAIL_NUDGE_COOLDOWN_MINUTES,
    ):
        return False

    dedupe_key = email_nudge_dedupe_key(
        latest.uid,
        current,
        config.MESSAGE_EMAIL_NUDGE_COOLDOWN_MINUTES,
    )
    statement = (
        insert(ExternalDeliveryLedger)
        .values(
            account_uid=account_uid,
            channel=DELIVERY_CHANNEL_EMAIL,
            aggregate_key=aggregate_key,
            dedupe_key=dedupe_key,
            status="pending",
            unread_count=len(eligible),
            dialog_count=len(allowed_senders),
            attempt_count=0,
            next_attempt_at=current,
            created_at=current,
            updated_at=current,
        )
        .on_conflict_do_nothing(constraint="uq_external_delivery_dedupe")
        .returning(ExternalDeliveryLedger.uid)
    )
    inserted = (await db.execute(statement)).scalar_one_or_none()
    await db.commit()
    return inserted is not None


async def run_email_nudge_worker(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    batch_size: int = DEFAULT_WORKER_BATCH_SIZE,
    max_batches: int = DEFAULT_MAX_BATCHES,
    now: datetime | None = None,
) -> EmailNudgeWorkerStats:
    current = utc_naive(now or datetime.now(timezone.utc))
    bounded_batch_size = max(1, min(int(batch_size), MAX_WORKER_BATCH_SIZE))
    bounded_max_batches = max(1, min(int(max_batches), MAX_WORKER_BATCHES))
    stats = EmailNudgeWorkerStats()

    if not realtime_service.distributed:
        await realtime_service.start()
    if not realtime_service.distributed and not config.DEBUG:
        logger.error("Unread-DM email nudge skipped: distributed Redis presence is unavailable")
        return stats
    stats.infrastructure_ready = True

    async with session_factory() as state_db:
        state_result = await state_db.execute(
            select(NotificationWorkerState)
            .where(NotificationWorkerState.worker_name == WORKER_NAME_UNREAD_DM_EMAIL)
            .with_for_update(skip_locked=True)
        )
        worker_state = state_result.scalar_one_or_none()
        if worker_state is None:
            logger.info("Unread-DM email nudge skipped: another invocation owns the cursor lock")
            return stats

        stats.acquired = True
        cursor = worker_state.cursor_account_uid

        for _ in range(bounded_max_batches):
            async with session_factory() as index_db:
                account_uids = await email_nudge_account_page(
                    index_db,
                    now=current,
                    after_uid=cursor,
                    limit=bounded_batch_size,
                )

            if not account_uids:
                worker_state.cursor_account_uid = None
                worker_state.updated_at = current
                stats.wrapped = cursor is not None
                break

            stats.batches += 1
            stats.accounts_seen += len(account_uids)
            for account_uid in account_uids:
                async with session_factory() as account_db:
                    try:
                        queued = await queue_unread_dm_email_nudge(account_db, account_uid, now=current)
                        if queued:
                            stats.queued += 1
                        else:
                            stats.skipped += 1
                    except Exception:
                        await account_db.rollback()
                        stats.failed += 1
                        logger.exception("Unread-DM email nudge candidate failed for account %s", account_uid)

            cursor = account_uids[-1]
            worker_state.cursor_account_uid = cursor
            worker_state.updated_at = current
            if len(account_uids) < bounded_batch_size:
                worker_state.cursor_account_uid = None
                stats.wrapped = True
                break

        await state_db.commit()

    return stats
