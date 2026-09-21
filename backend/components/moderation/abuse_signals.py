from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Account
from components.message.model import PrivateMessage
from components.moderation.abuse_model import TrustSafetyAbuseSignal
from components.moderation.abuse_settings import abuse_signal_config
from components.moderation.protective_hold import maybe_apply_protective_hold
from components.space.model import SpaceInvitation
from utils.logger import setup_logger


_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
logger = setup_logger(__name__)


async def _account_for_legacy_uid(db: AsyncSession, legacy_user_uid: UUID) -> Account | None:
    result = await db.execute(
        select(Account)
        .where(
            Account.legacy_user_uid == legacy_user_uid,
            Account.deleted_at.is_(None),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


def _dedupe_key(
    *,
    account_uid: UUID,
    signal_type: str,
    surface: str,
    scope_uid: UUID | None,
    bucket_seconds: int,
    now: datetime,
) -> str:
    bucket = int(now.timestamp()) // max(1, bucket_seconds)
    raw = f"{account_uid}:{signal_type}:{surface}:{scope_uid or '-'}:{bucket}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def emit_abuse_signal(
    db: AsyncSession,
    *,
    account_uid: UUID,
    signal_type: str,
    surface: str,
    observed_count: int,
    window_seconds: int,
    severity: str = "medium",
    scope_uid: UUID | None = None,
    details: dict | None = None,
    dedupe_seconds: int | None = None,
) -> UUID:
    """Upsert one advisory signal into a bounded time bucket.

    No message body, attachment URL, account handle or private-dialog transcript
    belongs in details. Callers should pass counts/thresholds only.
    """
    now = datetime.utcnow()
    dedupe_seconds = dedupe_seconds or window_seconds
    key = _dedupe_key(
        account_uid=account_uid,
        signal_type=signal_type,
        surface=surface,
        scope_uid=scope_uid,
        bucket_seconds=dedupe_seconds,
        now=now,
    )
    safe_details = details or {}
    stmt = (
        pg_insert(TrustSafetyAbuseSignal)
        .values(
            account_uid=account_uid,
            signal_type=signal_type,
            surface=surface,
            scope_uid=scope_uid,
            severity=severity,
            observed_count=max(1, int(observed_count)),
            window_seconds=max(1, int(window_seconds)),
            dedupe_key=key,
            details=safe_details,
            status="open",
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            constraint="uq_trust_safety_abuse_signal_dedupe",
            set_={
                "observed_count": func.greatest(
                    TrustSafetyAbuseSignal.observed_count,
                    max(1, int(observed_count)),
                ),
                "last_seen_at": now,
                "updated_at": now,
                "severity": severity,
                "details": safe_details,
            },
        )
        .returning(TrustSafetyAbuseSignal.uid)
    )
    uid = (await db.execute(stmt)).scalar_one()
    await db.commit()
    try:
        await maybe_apply_protective_hold(db, signal_uid=uid)
    except Exception:
        # Signal collection remains advisory and available even if optional
        # automation is misconfigured or temporarily fails.
        logger.exception("Protective-hold evaluation failed for signal=%s", uid)
    return uid


async def record_rate_limit_signal(
    db: AsyncSession,
    *,
    legacy_user_uid: UUID,
    surface: str,
    scope_uid: UUID | None = None,
) -> UUID | None:
    account = await _account_for_legacy_uid(db, legacy_user_uid)
    if not account:
        return None
    return await emit_abuse_signal(
        db,
        account_uid=account.uid,
        signal_type="message_rate_limit",
        surface=surface,
        scope_uid=scope_uid,
        observed_count=1,
        window_seconds=abuse_signal_config.rate_limit_dedupe_seconds,
        severity="medium",
        details={"source": "server_rate_limit"},
        dedupe_seconds=abuse_signal_config.rate_limit_dedupe_seconds,
    )


async def detect_dm_recipient_burst(
    db: AsyncSession,
    *,
    sender_legacy_uid: UUID,
) -> UUID | None:
    account = await _account_for_legacy_uid(db, sender_legacy_uid)
    if not account:
        return None
    cutoff = datetime.utcnow() - timedelta(seconds=abuse_signal_config.dm_recipient_window_seconds)
    result = await db.execute(
        select(func.count(func.distinct(PrivateMessage.receiver_uid))).where(
            PrivateMessage.sender_uid == sender_legacy_uid,
            PrivateMessage.receiver_uid != sender_legacy_uid,
            PrivateMessage.created_at >= cutoff,
        )
    )
    count = int(result.scalar_one() or 0)
    if count < abuse_signal_config.dm_distinct_recipient_threshold:
        return None
    return await emit_abuse_signal(
        db,
        account_uid=account.uid,
        signal_type="dm_distinct_recipient_burst",
        surface="messenger",
        observed_count=count,
        window_seconds=abuse_signal_config.dm_recipient_window_seconds,
        severity="high" if count >= abuse_signal_config.dm_distinct_recipient_threshold * 2 else "medium",
        details={
            "distinct_recipients": count,
            "threshold": abuse_signal_config.dm_distinct_recipient_threshold,
        },
    )


async def detect_invitation_burst(
    db: AsyncSession,
    *,
    inviter_account_uid: UUID,
) -> UUID | None:
    cutoff = datetime.utcnow() - timedelta(seconds=abuse_signal_config.invite_window_seconds)
    result = await db.execute(
        select(func.count(func.distinct(SpaceInvitation.invitee_account_uid))).where(
            SpaceInvitation.inviter_account_uid == inviter_account_uid,
            SpaceInvitation.updated_at >= cutoff,
        )
    )
    count = int(result.scalar_one() or 0)
    if count < abuse_signal_config.invite_distinct_recipient_threshold:
        return None
    return await emit_abuse_signal(
        db,
        account_uid=inviter_account_uid,
        signal_type="space_invite_recipient_burst",
        surface="space_invitation",
        observed_count=count,
        window_seconds=abuse_signal_config.invite_window_seconds,
        severity="high" if count >= abuse_signal_config.invite_distinct_recipient_threshold * 2 else "medium",
        details={
            "distinct_recipients": count,
            "threshold": abuse_signal_config.invite_distinct_recipient_threshold,
        },
    )


def signal_projection(item: TrustSafetyAbuseSignal) -> dict:
    return {
        "uid": str(item.uid),
        "account_uid": str(item.account_uid),
        "signal_type": item.signal_type,
        "surface": item.surface,
        "scope_uid": str(item.scope_uid) if item.scope_uid else None,
        "severity": item.severity,
        "observed_count": item.observed_count,
        "window_seconds": item.window_seconds,
        "details": item.details or {},
        "status": item.status,
        "review_note": item.review_note,
        "calibration_label": item.calibration_label,
        "reviewed_by_account_uid": str(item.reviewed_by_account_uid) if item.reviewed_by_account_uid else None,
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        "first_seen_at": item.first_seen_at.isoformat(),
        "last_seen_at": item.last_seen_at.isoformat(),
        "created_at": item.created_at.isoformat(),
    }


async def list_abuse_signals(
    db: AsyncSession,
    *,
    status_value: str = "open",
    limit: int = 100,
) -> list[dict]:
    query = select(TrustSafetyAbuseSignal)
    if status_value:
        query = query.where(TrustSafetyAbuseSignal.status == status_value)
    query = query.order_by(
        TrustSafetyAbuseSignal.last_seen_at.desc(),
    ).limit(limit)
    result = await db.execute(query)
    return [signal_projection(item) for item in result.scalars().all()]


async def review_abuse_signal(
    db: AsyncSession,
    *,
    signal_uid: UUID,
    reviewer_account_uid: UUID,
    decision: str,
    note: str | None = None,
    calibration_label: str | None = None,
) -> dict | None:
    result = await db.execute(
        select(TrustSafetyAbuseSignal)
        .where(TrustSafetyAbuseSignal.uid == signal_uid)
        .with_for_update()
    )
    item = result.scalar_one_or_none()
    if not item:
        return None
    if calibration_label not in {None, "true_positive", "false_positive", "unclear"}:
        raise ValueError("invalid calibration label")
    if calibration_label == "false_positive" and decision != "dismissed":
        raise ValueError("false_positive calibration label requires dismissed decision")
    if calibration_label in {"true_positive", "unclear"} and decision != "reviewed":
        raise ValueError(f"{calibration_label} calibration label requires reviewed decision")
    item.status = decision
    item.review_note = (note or "").strip()[:1000] or None
    if calibration_label is not None:
        item.calibration_label = calibration_label
    item.reviewed_by_account_uid = reviewer_account_uid
    item.reviewed_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    return signal_projection(item)
