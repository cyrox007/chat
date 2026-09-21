from __future__ import annotations

import os
from dataclasses import dataclass


_VALID_MODES = frozenset({"off", "shadow", "enforce"})


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.getenv(name, str(default)))
    return max(minimum, min(maximum, value))


def _bounded_float(name: str, default: float, minimum: float, maximum: float) -> float:
    value = float(os.getenv(name, str(default)))
    return max(minimum, min(maximum, value))


@dataclass(frozen=True, slots=True)
class ModerationAutomationConfig:
    # `enabled` stays for compatibility with existing callers/tests. Production
    # policy should use `mode`: off -> no evaluation, shadow -> evaluate only,
    # enforce -> evaluate and potentially issue a short hold after calibration.
    enabled: bool
    hold_minutes: int
    corroboration_lookback_seconds: int
    min_high_signals: int
    mode: str = "off"
    calibration_min_labels_per_type: int = 25
    calibration_max_false_positive_percent: float = 5.0
    calibration_gate_required: bool = False
    enforcement_approved: bool = False


def automation_mode(config: ModerationAutomationConfig) -> str:
    """Return the effective mode while preserving legacy explicit test configs."""
    if config.mode in {"shadow", "enforce"}:
        return config.mode
    if config.enabled:
        return "enforce"
    return "off"


def load_moderation_automation_config() -> ModerationAutomationConfig:
    """Load the deliberately narrow protective-hold policy.

    `MODERATION_PROTECTIVE_HOLDS_MODE` is the canonical control. The old
    `MODERATION_PROTECTIVE_HOLDS_ENABLED=true` remains a compatibility alias
    for enforce mode when MODE is not set, but production enforcement is still
    calibration-gated and requires explicit human approval.
    """
    raw_mode = os.getenv("MODERATION_PROTECTIVE_HOLDS_MODE", "").strip().lower()
    legacy_enabled = _env_bool("MODERATION_PROTECTIVE_HOLDS_ENABLED", False)
    mode = raw_mode or ("enforce" if legacy_enabled else "off")
    if mode not in _VALID_MODES:
        raise RuntimeError(
            "MODERATION_PROTECTIVE_HOLDS_MODE must be one of: off, shadow, enforce"
        )

    return ModerationAutomationConfig(
        enabled=mode == "enforce",
        mode=mode,
        hold_minutes=_bounded_int("MODERATION_PROTECTIVE_HOLD_MINUTES", 10, 5, 15),
        corroboration_lookback_seconds=_bounded_int(
            "MODERATION_PROTECTIVE_HOLD_LOOKBACK_SECONDS", 1800, 300, 86400
        ),
        min_high_signals=_bounded_int(
            "MODERATION_PROTECTIVE_HOLD_MIN_HIGH_SIGNALS", 2, 2, 10
        ),
        calibration_min_labels_per_type=_bounded_int(
            "MODERATION_PROTECTIVE_HOLD_CALIBRATION_MIN_LABELS_PER_TYPE",
            25,
            5,
            10000,
        ),
        calibration_max_false_positive_percent=_bounded_float(
            "MODERATION_PROTECTIVE_HOLD_CALIBRATION_MAX_FALSE_POSITIVE_PERCENT",
            5.0,
            0.0,
            50.0,
        ),
        calibration_gate_required=mode == "enforce",
        enforcement_approved=_env_bool(
            "MODERATION_PROTECTIVE_HOLD_ENFORCEMENT_APPROVED", False
        ),
    )


moderation_automation_config = load_moderation_automation_config()
