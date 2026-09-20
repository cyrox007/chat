from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.moderation.abuse_model import TrustSafetyAbuseSignal
from components.moderation.automation_settings import (
    ModerationAutomationConfig,
    moderation_automation_config,
)
from components.moderation.model import PlatformRestriction, PlatformRestrictionAuditEvent
from components.moderation.policy import effective_authority_level, restriction_projection
from components.notification.model import UserNotification


# Intentionally narrower than normal moderation capabilities.
_SIGNAL_CAPABILITY: dict[str, str] = {
    "dm_distinct_recipient_burst": "messenger.send",
    "space_invite_recipient_burst": "invitation.send",
}
_ALLOWED_CAPABILITIES = frozenset(_SIGNAL_CAPABILITY.values())


async def maybe_apply_protective_hold(
    db: AsyncSession,
    *,
    signal_uid: UUID,
    config: ModerationAutomationConfig | None = None,
) -> dict | None:
    """Apply a short reversible hold only after corroborated high-risk signals."""
    cfg = config or moderation_automation_config
    if not cfg.enabled:
        return None

    signal = await db.get(TrustSafetyAbuseSignal, signal_uid)
    if (
        signal is None
        or signal.status != "open"
        or signal.severity not in {"high", "critical"}
        or signal.signal_type not in _SIGNAL_CAPABILITY
    ):
        return None

    target_authority = await effective_authority_level(db, signal.account_uid)
    if target_authority != 0:
        return None

    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=cfg.corroboration_lookback_seconds)
    corroboration_result = await db.execute(
        select(func.count(func.distinct(TrustSafetyAbuseSignal.dedupe_key))).where(
            TrustSafetyAbuseSignal.account_uid == signal.account_uid,
            TrustSafetyAbuseSignal.status == "open",
            TrustSafetyAbuseSignal.severity.in_(["high", "critical"]),
            TrustSafetyAbuseSignal.signal_type.in_(tuple(_SIGNAL_CAPABILITY)),
            TrustSafetyAbuseSignal.last_seen_at >= cutoff,
        )
    )
    corroboration_count = int(corroboration_result.scalar_one() or 0)
    if corroboration_count < cfg.min_high_signals:
        return None

    capability = _SIGNAL_CAPABILITY[signal.signal_type]
    if capability not in _ALLOWED_CAPABILITIES:
        return None

    existing_result = await db.execute(
        select(PlatformRestriction)
        .where(
            PlatformRestriction.target_account_uid == signal.account_uid,
            PlatformRestriction.origin == "automation",
            PlatformRestriction.capability == capability,
            PlatformRestriction.scope_type == "platform",
            PlatformRestriction.status == "active",
            PlatformRestriction.starts_at <= now,
            or_(
                PlatformRestriction.expires_at.is_(None),
                PlatformRestriction.expires_at > now,
            ),
        )
        .order_by(PlatformRestriction.created_at.desc())
        .limit(1)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return restriction_projection(existing)

    expires_at = now + timedelta(minutes=cfg.hold_minutes)
    restriction = PlatformRestriction(
        report_uid=None,
        actor_account_uid=None,
        target_account_uid=signal.account_uid,
        capability=capability,
        scope_type="platform",
        scope_uid=None,
        reason_code=f"protective_hold.{signal.signal_type}"[:48],
        public_explanation=(
            "Эта возможность временно ограничена автоматической защитой от "
            "повторяющегося спама. Ограничение короткое и истечёт автоматически."
        ),
        origin="automation",
        status="active",
        actor_authority_level=0,
        target_authority_level=0,
        starts_at=now,
        expires_at=expires_at,
    )
    db.add(restriction)
    await db.flush()
    db.add(
        PlatformRestrictionAuditEvent(
            restriction_uid=restriction.uid,
            actor_account_uid=None,
            event_type="protective_hold_issued",
            note=(
                f"signal={signal.signal_type};corroboration={corroboration_count};"
                f"duration_minutes={cfg.hold_minutes}"
            ),
        )
    )
    db.add(
        UserNotification(
            account_uid=signal.account_uid,
            kind="platform_protective_hold",
            dedupe_key=f"protective-hold:{restriction.uid}",
            title="Временная защита от спама",
            body=restriction.public_explanation,
        )
    )
    await db.commit()
    await db.refresh(restriction)
    return restriction_projection(restriction)
