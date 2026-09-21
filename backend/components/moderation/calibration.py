from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from components.moderation.abuse_model import (
    ProtectiveHoldEvaluation,
    TrustSafetyAbuseSignal,
)
from components.moderation.automation_settings import ModerationAutomationConfig


CALIBRATED_SIGNAL_TYPES = (
    "dm_distinct_recipient_burst",
    "space_invite_recipient_burst",
)
CALIBRATION_LABELS = frozenset({"true_positive", "false_positive", "unclear"})


async def record_protective_hold_evaluation(
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
    now = datetime.utcnow()
    stmt = (
        pg_insert(ProtectiveHoldEvaluation)
        .values(
            signal_uid=signal.uid,
            account_uid=signal.account_uid,
            signal_type=signal.signal_type,
            capability=capability,
            mode=mode,
            decision=decision,
            would_hold=would_hold,
            corroboration_count=max(0, int(corroboration_count)),
            min_high_signals=config.min_high_signals,
            lookback_seconds=config.corroboration_lookback_seconds,
            hold_minutes=config.hold_minutes,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            constraint="uq_protective_hold_evaluation_signal",
            set_={
                "account_uid": signal.account_uid,
                "signal_type": signal.signal_type,
                "capability": capability,
                "mode": mode,
                "decision": decision,
                "would_hold": would_hold,
                "corroboration_count": max(0, int(corroboration_count)),
                "min_high_signals": config.min_high_signals,
                "lookback_seconds": config.corroboration_lookback_seconds,
                "hold_minutes": config.hold_minutes,
                "updated_at": now,
            },
        )
    )
    await db.execute(stmt)


async def protective_hold_calibration_summary(
    db: AsyncSession,
    *,
    config: ModerationAutomationConfig,
    window_days: int = 30,
) -> dict:
    """Compare shadow/enforcement candidates with explicit human labels.

    This is a calibration report, not a global abuse-recall measurement. It only
    measures emitted server-owned signals that received an explicit human label.
    """
    window_days = max(1, min(365, int(window_days)))
    cutoff = datetime.utcnow() - timedelta(days=window_days)

    rows = (
        await db.execute(
            select(
                ProtectiveHoldEvaluation.signal_type,
                ProtectiveHoldEvaluation.would_hold,
                TrustSafetyAbuseSignal.calibration_label,
            )
            .join(
                TrustSafetyAbuseSignal,
                TrustSafetyAbuseSignal.uid == ProtectiveHoldEvaluation.signal_uid,
            )
            .where(
                ProtectiveHoldEvaluation.created_at >= cutoff,
                TrustSafetyAbuseSignal.calibration_label.in_(
                    ["true_positive", "false_positive", "unclear"]
                ),
            )
        )
    ).all()

    per_type = defaultdict(
        lambda: {
            "labeled_count": 0,
            "would_hold_labeled_count": 0,
            "would_hold_true_positive_count": 0,
            "would_hold_false_positive_count": 0,
            "confirmed_signal_count": 0,
            "confirmed_would_hold_count": 0,
            "unclear_count": 0,
        }
    )

    for signal_type, would_hold, label in rows:
        bucket = per_type[signal_type]
        bucket["labeled_count"] += 1
        if label == "unclear":
            bucket["unclear_count"] += 1
            continue
        if label == "true_positive":
            bucket["confirmed_signal_count"] += 1
            if would_hold:
                bucket["confirmed_would_hold_count"] += 1
        if would_hold:
            bucket["would_hold_labeled_count"] += 1
            if label == "true_positive":
                bucket["would_hold_true_positive_count"] += 1
            elif label == "false_positive":
                bucket["would_hold_false_positive_count"] += 1

    type_reports: dict[str, dict] = {}
    data_ready = True
    for signal_type in CALIBRATED_SIGNAL_TYPES:
        bucket = dict(per_type[signal_type])
        decisive_would_hold = (
            bucket["would_hold_true_positive_count"]
            + bucket["would_hold_false_positive_count"]
        )
        false_positive_percent = (
            round(
                100.0
                * bucket["would_hold_false_positive_count"]
                / decisive_would_hold,
                2,
            )
            if decisive_would_hold
            else 0.0
        )
        capture_percent = (
            round(
                100.0
                * bucket["confirmed_would_hold_count"]
                / bucket["confirmed_signal_count"],
                2,
            )
            if bucket["confirmed_signal_count"]
            else 0.0
        )
        enough_labels = (
            decisive_would_hold >= config.calibration_min_labels_per_type
        )
        acceptable_false_positive_rate = (
            decisive_would_hold > 0
            and false_positive_percent
            <= config.calibration_max_false_positive_percent
        )
        type_ready = enough_labels and acceptable_false_positive_rate
        data_ready = data_ready and type_ready
        type_reports[signal_type] = {
            **bucket,
            "false_positive_percent": false_positive_percent,
            "confirmed_candidate_capture_percent": capture_percent,
            "enough_labels": enough_labels,
            "acceptable_false_positive_rate": acceptable_false_positive_rate,
            "data_ready": type_ready,
        }

    enforcement_ready = data_ready and config.enforcement_approved
    return {
        "window_days": window_days,
        "min_labels_per_type": config.calibration_min_labels_per_type,
        "max_false_positive_percent": (
            config.calibration_max_false_positive_percent
        ),
        "data_ready": data_ready,
        "enforcement_approved": config.enforcement_approved,
        "enforcement_ready": enforcement_ready,
        "signal_types": type_reports,
        "limitations": (
            "Metrics cover only emitted, human-labeled server-owned signals; "
            "confirmed_candidate_capture_percent is not global recall."
        ),
    }
