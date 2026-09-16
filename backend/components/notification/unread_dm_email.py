from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from components.identity.model import Account, AccountRelationship, Credential, Persona, PrivacySettings
from components.message.model import PrivateMessage
from components.notification.email_provider import (
    EmailDeliveryRequest,
    EmailProviderError,
    SmtpEmailProvider,
)
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


@dataclass(frozen=True)
class UnreadSummary:
    latest_message_uid: UUID
    unread_count: int
    dialog_count: int


@dataclass(frozen=True)
class DeliveryClaim:
    uid: UUID
    account_uid: UUID
    claim_token: str
    attempt_count: int


@dataclass
class DeliveryWorkerStats:
    infrastructure_ready: bool = False
    claimed: int = 0
    delivered: int = 0
    retried: int = 0
    failed: int = 0
    suppressed: int = 0
    deferred_online: int = 0


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


def retry_delay_seconds(attempt_count: int) -> int:
    exponent = max(0, int(attempt_count) - 1)
    raw = config.MESSAGE_EMAIL_DELIVERY_RETRY_BASE_SECONDS * (2**min(exponent, 12))
    return min(raw, config.MESSAGE_EMAIL_DELIVERY_RETRY_MAX_SECONDS)


async def _sender_account_uid(db: AsyncSession, sender_legacy_uid: UUID) -> UUID | None:
    result = await db.execute(
        select(Account.uid)
        .where(Account.legacy_user_uid == sender_legacy_uid, Account.deleted_at.is_(None))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _external_dm_delivery_allowed(
    db: AsyncSession,
    sender_legacy_uid: UUID,
    receiver_account_uid: UUID,
    receiver_legacy_uid: UUID,
) -> bool:
    """Re-check Account policy while legacy message/Space rows still use User UIDs."""
    if sender_legacy_uid == receiver_legacy_uid:
        return True

    sender_account_uid = await _sender_account_uid(db, sender_legacy_uid)
    if sender_account_uid is None:
        return False

    blocked = await db.execute(
        select(AccountRelationship.id)
        .where(
            AccountRelationship.relation_type == "block",
            or_(
                and_(
                    AccountRelationship.from_account_uid == sender_account_uid,
                    AccountRelationship.to_account_uid == receiver_account_uid,
                ),
                and_(
                    AccountRelationship.from_account_uid == receiver_account_uid,
                    AccountRelationship.to_account_uid == sender_account_uid,
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
            Persona.account_uid == receiver_account_uid,
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
                        AccountRelationship.from_account_uid == sender_account_uid,
                        AccountRelationship.to_account_uid == receiver_account_uid,
                    ),
                    and_(
                        AccountRelationship.from_account_uid == receiver_account_uid,
                        AccountRelationship.to_account_uid == sender_account_uid,
                    ),
                ),
            )
        )
        return (reciprocal.scalar_one() or 0) >= 2

    if dm_policy == "shared_spaces":
        shared_space = await db.execute(
            select(RoomMember.room_uid)
            .where(
                RoomMember.user_uid.in_([sender_legacy_uid, receiver_legacy_uid]),
                RoomMember.is_banned.is_(False),
            )
            .group_by(RoomMember.room_uid)
            .having(func.count(func.distinct(RoomMember.user_uid)) >= 2)
            .limit(1)
        )
        return shared_space.scalar_one_or_none() is not None

    return False


async def _eligible_unread_summary(db: AsyncSession, account_uid: UUID) -> UnreadSummary | None:
    account = await db.get(Account, account_uid)
    if not account or account.status != "active" or account.deleted_at is not None or not account.legacy_user_uid:
        return None

    receiver_legacy_uid = UUID(str(account.legacy_user_uid))
    result = await db.execute(
        select(PrivateMessage)
        .where(
            PrivateMessage.receiver_uid == receiver_legacy_uid,
            PrivateMessage.is_read.is_(False),
        )
        .order_by(PrivateMessage.created_at.desc(), PrivateMessage.id.desc())
        .limit(MAX_UNREAD_MESSAGES_PER_ACCOUNT)
    )
    unread = list(result.scalars().all())
    if not unread:
        return None

    allowed_senders: set[UUID] = set()
    denied_senders: set[UUID] = set()
    for message in unread:
        sender_legacy_uid = UUID(str(message.sender_uid))
        if sender_legacy_uid in allowed_senders or sender_legacy_uid in denied_senders:
            continue
        allowed = await _external_dm_delivery_allowed(
            db,
            sender_legacy_uid,
            account_uid,
            receiver_legacy_uid,
        )
        (allowed_senders if allowed else denied_senders).add(sender_legacy_uid)

    eligible = [item for item in unread if UUID(str(item.sender_uid)) in allowed_senders]
    if not eligible:
        return None

    return UnreadSummary(
        latest_message_uid=UUID(str(eligible[0].uid)),
        unread_count=len(eligible),
        dialog_count=len(allowed_senders),
    )


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
            PrivateMessage.receiver_uid == Account.legacy_user_uid,
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
                Credential.value_normalized.is_not(None),
                Credential.verified_at.is_not(None),
            ),
        )
        .where(
            Account.status == "active",
            Account.deleted_at.is_(None),
            Account.legacy_user_uid.is_not(None),
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
            Credential.value_normalized.is_not(None),
            Credential.verified_at.is_not(None),
        )
        .limit(1)
    )
    if verified_email.scalar_one_or_none() is None:
        return False

    summary = await _eligible_unread_summary(db, account_uid)
    if summary is None:
        return False

    current = utc_naive(now)
    aggregate_key = f"unread-dm:{summary.latest_message_uid}"
    previous_result = await db.execute(
        select(ExternalDeliveryLedger.aggregate_key, ExternalDeliveryLedger.created_at)
        .where(
            ExternalDeliveryLedger.account_uid == account_uid,
            ExternalDeliveryLedger.channel == DELIVERY_CHANNEL_EMAIL,
            ExternalDeliveryLedger.status != "suppressed",
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
        summary.latest_message_uid,
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
            unread_count=summary.unread_count,
            dialog_count=summary.dialog_count,
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


async def claim_pending_email_deliveries(
    db: AsyncSession,
    *,
    now: datetime,
    limit: int,
) -> list[DeliveryClaim]:
    current = utc_naive(now)
    bounded_limit = max(1, min(int(limit), 250))
    pending = and_(
        ExternalDeliveryLedger.status == "pending",
        or_(
            ExternalDeliveryLedger.next_attempt_at.is_(None),
            ExternalDeliveryLedger.next_attempt_at <= current,
        ),
    )
    expired_claim = and_(
        ExternalDeliveryLedger.status == "processing",
        or_(
            ExternalDeliveryLedger.claim_expires_at.is_(None),
            ExternalDeliveryLedger.claim_expires_at <= current,
        ),
    )
    result = await db.execute(
        select(ExternalDeliveryLedger)
        .where(
            ExternalDeliveryLedger.channel == DELIVERY_CHANNEL_EMAIL,
            or_(pending, expired_claim),
        )
        .order_by(ExternalDeliveryLedger.next_attempt_at.asc().nullsfirst(), ExternalDeliveryLedger.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(bounded_limit)
    )
    rows = list(result.scalars().all())
    claims: list[DeliveryClaim] = []
    expires_at = current + timedelta(seconds=config.MESSAGE_EMAIL_DELIVERY_LEASE_SECONDS)
    for row in rows:
        token = uuid4().hex
        row.status = "processing"
        row.claim_token = token
        row.claim_expires_at = expires_at
        row.attempt_count = int(row.attempt_count or 0) + 1
        row.attempted_at = current
        row.updated_at = current
        claims.append(
            DeliveryClaim(
                uid=UUID(str(row.uid)),
                account_uid=UUID(str(row.account_uid)),
                claim_token=token,
                attempt_count=row.attempt_count,
            )
        )
    await db.commit()
    return claims


async def _claimed_row(db: AsyncSession, claim: DeliveryClaim) -> ExternalDeliveryLedger | None:
    result = await db.execute(
        select(ExternalDeliveryLedger)
        .where(
            ExternalDeliveryLedger.uid == claim.uid,
            ExternalDeliveryLedger.status == "processing",
            ExternalDeliveryLedger.claim_token == claim.claim_token,
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def _release_online_claim(db: AsyncSession, claim: DeliveryClaim, *, now: datetime) -> None:
    row = await _claimed_row(db, claim)
    if row is None:
        await db.rollback()
        return
    row.status = "pending"
    row.attempt_count = max(0, int(row.attempt_count or 0) - 1)
    row.next_attempt_at = utc_naive(now) + timedelta(seconds=config.MESSAGE_EMAIL_ONLINE_RECHECK_SECONDS)
    row.claim_token = None
    row.claim_expires_at = None
    row.failure_class = None
    row.updated_at = utc_naive(now)
    await db.commit()


async def _suppress_claim(db: AsyncSession, claim: DeliveryClaim, *, reason: str, now: datetime) -> None:
    row = await _claimed_row(db, claim)
    if row is None:
        await db.rollback()
        return
    row.status = "suppressed"
    row.next_attempt_at = None
    row.claim_token = None
    row.claim_expires_at = None
    row.failure_class = reason[:80]
    row.updated_at = utc_naive(now)
    await db.commit()


async def _complete_claim(
    db: AsyncSession,
    claim: DeliveryClaim,
    *,
    provider_message_id: str,
    now: datetime,
) -> None:
    row = await _claimed_row(db, claim)
    if row is None:
        await db.rollback()
        return
    current = utc_naive(now)
    row.status = "delivered"
    row.delivered_at = current
    row.next_attempt_at = None
    row.provider_message_id = provider_message_id[:180]
    row.failure_class = None
    row.claim_token = None
    row.claim_expires_at = None
    row.updated_at = current
    await db.commit()


async def _fail_claim(
    db: AsyncSession,
    claim: DeliveryClaim,
    *,
    failure_class: str,
    retryable: bool,
    now: datetime,
) -> bool:
    row = await _claimed_row(db, claim)
    if row is None:
        await db.rollback()
        return False
    current = utc_naive(now)
    exhausted = int(row.attempt_count or 0) >= config.MESSAGE_EMAIL_DELIVERY_MAX_ATTEMPTS
    retry = bool(retryable and not exhausted)
    row.failure_class = failure_class[:80]
    row.claim_token = None
    row.claim_expires_at = None
    row.updated_at = current
    if retry:
        row.status = "pending"
        row.next_attempt_at = current + timedelta(seconds=retry_delay_seconds(row.attempt_count))
    else:
        row.status = "failed"
        row.failed_at = current
        row.next_attempt_at = None
    await db.commit()
    return retry


async def _verified_email(db: AsyncSession, account_uid: UUID) -> str | None:
    result = await db.execute(
        select(Credential.value_normalized)
        .where(
            Credential.account_uid == account_uid,
            Credential.kind == "email",
            Credential.value_normalized.is_not(None),
            Credential.verified_at.is_not(None),
        )
        .order_by(Credential.is_primary.desc(), Credential.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def run_email_delivery_worker(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    provider: SmtpEmailProvider | None = None,
    batch_size: int | None = None,
    now: datetime | None = None,
) -> DeliveryWorkerStats:
    current = utc_naive(now or datetime.now(timezone.utc))
    stats = DeliveryWorkerStats()
    provider = provider or SmtpEmailProvider()
    if not provider.configured:
        logger.error("Unread-DM email delivery skipped: SMTP provider is not configured")
        return stats

    if not realtime_service.distributed:
        await realtime_service.start()
    if not realtime_service.distributed and not config.DEBUG:
        logger.error("Unread-DM email delivery skipped: distributed Redis presence is unavailable")
        return stats
    stats.infrastructure_ready = True

    async with session_factory() as claim_db:
        claims = await claim_pending_email_deliveries(
            claim_db,
            now=current,
            limit=batch_size or config.MESSAGE_EMAIL_DELIVERY_BATCH_SIZE,
        )
    stats.claimed = len(claims)

    for claim in claims:
        try:
            try:
                online = await realtime_service.is_online(claim.account_uid)
            except Exception:
                logger.exception("Presence check failed for email delivery account=%s", claim.account_uid)
                async with session_factory() as db:
                    retried = await _fail_claim(
                        db,
                        claim,
                        failure_class="presence_unavailable",
                        retryable=True,
                        now=current,
                    )
                stats.retried += int(retried)
                stats.failed += int(not retried)
                continue

            if online:
                async with session_factory() as db:
                    await _release_online_claim(db, claim, now=current)
                stats.deferred_online += 1
                continue

            async with session_factory() as db:
                preference = await db.get(MessageNotificationPreference, claim.account_uid)
                if not preference or not preference.email_unread_dm_nudge:
                    await _suppress_claim(db, claim, reason="email_opt_out", now=current)
                    stats.suppressed += 1
                    continue

                recipient = await _verified_email(db, claim.account_uid)
                if not recipient:
                    await _suppress_claim(db, claim, reason="verified_email_missing", now=current)
                    stats.suppressed += 1
                    continue

                summary = await _eligible_unread_summary(db, claim.account_uid)
                if summary is None:
                    await _suppress_claim(db, claim, reason="no_eligible_unread_dm", now=current)
                    stats.suppressed += 1
                    continue

            request = EmailDeliveryRequest(
                delivery_uid=claim.uid,
                recipient=recipient,
                unread_count=summary.unread_count,
                dialog_count=summary.dialog_count,
            )
            try:
                result = await provider.send(request)
            except EmailProviderError as exc:
                async with session_factory() as db:
                    retried = await _fail_claim(
                        db,
                        claim,
                        failure_class=exc.failure_class,
                        retryable=exc.retryable,
                        now=current,
                    )
                stats.retried += int(retried)
                stats.failed += int(not retried)
                continue
            except Exception:
                logger.exception("Unexpected email provider failure for delivery=%s", claim.uid)
                async with session_factory() as db:
                    retried = await _fail_claim(
                        db,
                        claim,
                        failure_class="provider_error",
                        retryable=True,
                        now=current,
                    )
                stats.retried += int(retried)
                stats.failed += int(not retried)
                continue

            async with session_factory() as db:
                await _complete_claim(
                    db,
                    claim,
                    provider_message_id=result.provider_message_id,
                    now=current,
                )
            stats.delivered += 1
        except Exception:
            logger.exception("Unread-DM email delivery claim failed: delivery=%s", claim.uid)
            async with session_factory() as db:
                retried = await _fail_claim(
                    db,
                    claim,
                    failure_class="delivery_worker_error",
                    retryable=True,
                    now=current,
                )
            stats.retried += int(retried)
            stats.failed += int(not retried)

    return stats
