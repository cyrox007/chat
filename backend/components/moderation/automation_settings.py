from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.getenv(name, str(default)))
    return max(minimum, min(maximum, value))


@dataclass(frozen=True, slots=True)
class ModerationAutomationConfig:
    enabled: bool
    hold_minutes: int
    corroboration_lookback_seconds: int
    min_high_signals: int


def load_moderation_automation_config() -> ModerationAutomationConfig:
    """Load the deliberately narrow protective-hold policy."""
    return ModerationAutomationConfig(
        enabled=_env_bool("MODERATION_PROTECTIVE_HOLDS_ENABLED", False),
        hold_minutes=_bounded_int("MODERATION_PROTECTIVE_HOLD_MINUTES", 10, 5, 15),
        corroboration_lookback_seconds=_bounded_int(
            "MODERATION_PROTECTIVE_HOLD_LOOKBACK_SECONDS", 1800, 300, 86400
        ),
        min_high_signals=_bounded_int(
            "MODERATION_PROTECTIVE_HOLD_MIN_HIGH_SIGNALS", 2, 2, 10
        ),
    )


moderation_automation_config = load_moderation_automation_config()
