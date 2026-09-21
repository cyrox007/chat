from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.moderation.abuse_model import TrustSafetyAbuseSignal
from components.moderation.ai_model import ModerationAIRecommendation
from components.moderation.automation_settings import moderation_automation_config
from components.moderation.media_model import ModerationMediaRecord
from settings import config

from components.moderation.model import (
    PlatformRestriction,
    PlatformRestrictionAppeal,
    TrustSafetyReport,
)


def _counter(values) -> dict[str, int]:
    return dict(Counter(value for value in values if value))


async def trust_safety_metrics(
    db: AsyncSession,
    *,
    window_hours: int = 168,
) -> dict:
    """Return aggregate operational metrics without content or subject IDs."""
    window_hours = max(1, min(720, int(window_hours)))
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=window_hours)

    queue_result = await db.execute(
        select(func.count(TrustSafetyReport.uid), func.min(TrustSafetyReport.created_at)).where(
            TrustSafetyReport.status.in_(["triage", "in_review", "escalated"])
        )
    )
    queue_count, oldest_created_at = queue_result.one()
    oldest_age_seconds = (
        max(0, int((now - oldest_created_at).total_seconds()))
        if oldest_created_at
        else 0
    )

    resolved_reports = (
        await db.execute(
            select(TrustSafetyReport.created_at, TrustSafetyReport.resolved_at).where(
                TrustSafetyReport.resolved_at.is_not(None),
                TrustSafetyReport.resolved_at >= cutoff,
            )
        )
    ).all()
    decision_seconds = [
        max(0, int((resolved_at - created_at).total_seconds()))
        for created_at, resolved_at in resolved_reports
        if created_at and resolved_at
    ]

    appeals = (
        await db.execute(
            select(PlatformRestrictionAppeal.status).where(
                or_(
                    PlatformRestrictionAppeal.created_at >= cutoff,
                    PlatformRestrictionAppeal.resolved_at >= cutoff,
                )
            )
        )
    ).scalars().all()
    appeal_counts = _counter(appeals)
    decided_appeals = appeal_counts.get("upheld", 0) + appeal_counts.get("overturned", 0)
    overturn_rate_percent = (
        round(100 * appeal_counts.get("overturned", 0) / decided_appeals, 1)
        if decided_appeals
        else 0.0
    )

    ai_outcomes = (
        await db.execute(
            select(ModerationAIRecommendation.outcome).where(
                or_(
                    ModerationAIRecommendation.created_at >= cutoff,
                    ModerationAIRecommendation.outcome_at >= cutoff,
                )
            )
        )
    ).scalars().all()

    signal_statuses = (
        await db.execute(
            select(TrustSafetyAbuseSignal.status).where(
                or_(
                    TrustSafetyAbuseSignal.created_at >= cutoff,
                    TrustSafetyAbuseSignal.reviewed_at >= cutoff,
                )
            )
        )
    ).scalars().all()

    open_signal_count = int(
        (
            await db.execute(
                select(func.count(TrustSafetyAbuseSignal.uid)).where(
                    TrustSafetyAbuseSignal.status == "open"
                )
            )
        ).scalar_one()
        or 0
    )

    restriction_origins = (
        await db.execute(
            select(PlatformRestriction.origin).where(
                PlatformRestriction.created_at >= cutoff
            )
        )
    ).scalars().all()
    active_auto_holds = int(
        (
            await db.execute(
                select(func.count(PlatformRestriction.uid)).where(
                    PlatformRestriction.origin == "automation",
                    PlatformRestriction.status == "active",
                    PlatformRestriction.starts_at <= now,
                    PlatformRestriction.expires_at > now,
                )
            )
        ).scalar_one()
        or 0
    )

    due_media_evidence = int(
        (
            await db.execute(
                select(func.count(ModerationMediaRecord.uid)).where(
                    ModerationMediaRecord.status == "removed",
                    ModerationMediaRecord.purged_at.is_(None),
                    ModerationMediaRecord.retention_due_at.is_not(None),
                    ModerationMediaRecord.retention_due_at <= now,
                )
            )
        ).scalar_one()
        or 0
    )
    purged_media_evidence = int(
        (
            await db.execute(
                select(func.count(ModerationMediaRecord.uid)).where(
                    ModerationMediaRecord.purged_at.is_not(None),
                    ModerationMediaRecord.purged_at >= cutoff,
                )
            )
        ).scalar_one()
        or 0
    )

    return {
        "window_hours": window_hours,
        "queue": {
            "open_count": int(queue_count or 0),
            "oldest_age_seconds": oldest_age_seconds,
            "resolved_count": len(decision_seconds),
            "average_decision_seconds": (
                round(sum(decision_seconds) / len(decision_seconds), 1)
                if decision_seconds
                else 0.0
            ),
        },
        "appeals": {
            "status_counts": appeal_counts,
            "overturn_rate_percent": overturn_rate_percent,
        },
        "ai": {"outcome_counts": _counter(ai_outcomes)},
        "abuse_signals": {
            "status_counts": _counter(signal_statuses),
            "open_count": open_signal_count,
        },
        "restrictions": {
            "origin_counts": _counter(restriction_origins),
            "active_automation_holds": active_auto_holds,
        },
        "automation": {
            "enabled": moderation_automation_config.enabled,
            "hold_minutes": moderation_automation_config.hold_minutes,
            "lookback_seconds": moderation_automation_config.corroboration_lookback_seconds,
            "min_high_signals": moderation_automation_config.min_high_signals,
            "allowed_capabilities": ["invitation.send", "messenger.send"],
        },
        "media_retention": {
            "removed_retention_days": config.MODERATION_MEDIA_REMOVED_RETENTION_DAYS,
            "due_count": due_media_evidence,
            "purged_count": purged_media_evidence,
        },
    }
