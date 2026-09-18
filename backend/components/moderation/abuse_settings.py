from __future__ import annotations

import os
from dataclasses import dataclass


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.getenv(name, str(default)))
    return max(minimum, min(maximum, value))


@dataclass(frozen=True, slots=True)
class AbuseSignalConfig:
    dm_recipient_window_seconds: int
    dm_distinct_recipient_threshold: int
    invite_window_seconds: int
    invite_distinct_recipient_threshold: int
    rate_limit_dedupe_seconds: int


def load_abuse_signal_config() -> AbuseSignalConfig:
    return AbuseSignalConfig(
        dm_recipient_window_seconds=_bounded_int("ABUSE_DM_RECIPIENT_WINDOW_SECONDS", 600, 60, 86400),
        dm_distinct_recipient_threshold=_bounded_int("ABUSE_DM_DISTINCT_RECIPIENT_THRESHOLD", 8, 3, 1000),
        invite_window_seconds=_bounded_int("ABUSE_INVITE_WINDOW_SECONDS", 600, 60, 86400),
        invite_distinct_recipient_threshold=_bounded_int("ABUSE_INVITE_DISTINCT_RECIPIENT_THRESHOLD", 12, 3, 1000),
        rate_limit_dedupe_seconds=_bounded_int("ABUSE_RATE_LIMIT_DEDUPE_SECONDS", 600, 60, 86400),
    )


abuse_signal_config = load_abuse_signal_config()
