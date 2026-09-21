from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Account
from components.moderation.abuse_model import TrustSafetyAbuseSignal
from components.moderation.automation_settings import (
    ModerationAutomationConfig,
    automation_mode,
    moderation_automation_config,
)
from components.moderation.calibration import (
    protective_hold_calibration_summary,
    record_protective_hold_evaluation,
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


async def _record_and_commit_evaluation(
    db: AsyncSession,
    *,
    signal: TrustSafetyAbuseSignal,
    mode: str,
    capability: str | None,
    decision: str,
    would_hold: bool,
    corroboration_count: int,
    config: ModerationAutomationConfig,
) -> None:
    await record_protective_hold_evaluation(
        db,
        signal=signal,
        mode=mode,
        capability=capability,
        decision=decision,
        would_hold=would_hold,
        corroboration_count=corroboration_count,
        config=config,
    )
    await db.commit()


async def maybe_apply_protective_hold(
    db: AsyncSession,
    *,
    signal_uid: UUID,
    config: ModerationAutomationConfig | None = None,
) -> dict | None:
    """Evaluate a short protective hold and enforce only after calibration.

    off:
        no calibration row and no restriction.
    shadow:
        persist the privacy-minimal decision, never create a restriction.
    enforce:
        persist the decision and create a hold only when the human-reviewed
        calibration gate is ready and explicit operational approval is enabled.
    """
    cfg = config or moderation_automation_config
    mode = automation_mode(cfg)
    if mode == "off":
        return None

    signal = await db.get(TrustSafetyAbuseSignal, signal_uid)
    if signal is None:
        return None

    capability = _SIGNAL_CAPABILITY.get(signal.signal_type)
    if (
        signal.status != "open"
        or signal.severity not in {"high", "critical"}
        or capability is None
    ):
        await _record_and_commit_evaluation(
            db,
            signal=signal,
            mode=mode,
            capability=capability,
            decision="ineligible_signal",
            would_hold=False,
            corroboration_count=0,
            config=cfg,
        )
        return None

    # Serialize decisions per Account so shadow observations and actual holds use
    # the same policy snapshot and concurrent detectors cannot stack duplicates.
    await db.execute(
        select(Account.uid)
        .where(Account.uid == signal.account_uid)
        .with_for_update()
    )

    target_authority = await effective_authority_level(db, signal.account_uid)
    if target_authority != 0:
        await _record_and_commit_evaluation(
            db,
            signal=signal,
            mode=mode,
            capability=capability,
            decision="privileged_target",
            would_hold=False,
            corroboration_count=0,
            config=cfg,
        )
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
        await _record_and_commit_evaluation(
            db,
            signal=signal,
            mode=mode,
            capability=capability,
            decision="insufficient_corroboration",
            would_hold=False,
            corroboration_count=corroboration_count,
            config=cfg,
        )
        return None

    if capability not in _ALLOWED_CAPABILITIES:
        await _record_and_commit_evaluation(
            db,
            signal=signal,
            mode=mode,
            capability=capability,
            decision="capability_not_allowed",
            would_hold=False,
            corroboration_count=corroboration_count,
            config=cfg,
        )
        return None

    await record_protective_hold_evaluation(
        db,
        signal=signal,
        mode=mode,
        capability=capability,
        decision="candidate",
        would_hold=True,
        corroboration_count=corroboration_count,
        config=cfg,
    )

    # Shadow mode is the production calibration default: keep the durable
    # decision for later human comparison, but never change user capabilities.
    if mode == "shadow":
        await db.commit()
        return None

    # Production-loaded enforce mode is fail-closed behind both measured data and
    # an explicit human operational approval bit. Custom test configs can opt out
    # of this gate by leaving calibration_gate_required=False.
    if cfg.calibration_gate_required:
        gate = await protective_hold_calibration_summary(db, config=cfg)
        if not gate["enforcement_ready"]:
            await db.commit()
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
        await db.commit()
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
                f"signal_uid={signal.uid};signal_type={signal.signal_type};"
                f"corroboration={corroboration_count};duration_minutes={cfg.hold_minutes}"
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
