from __future__ import annotations

import json
import logging
from typing import Any


_SENSITIVE_KEY_FRAGMENTS = (
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "cookie",
    "email",
    "destination",
    "endpoint",
    "p256dh",
    "message_body",
    "private_message",
    "content",
)


def structured_event(event: str, **fields: Any) -> str:
    """Serialize a small operational event while rejecting sensitive field names."""
    normalized_event = str(event or "").strip()
    if not normalized_event:
        raise ValueError("structured log event name is required")

    for key in fields:
        lowered = str(key).lower()
        if any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS):
            raise ValueError(f"sensitive structured-log field is not allowed: {key}")

    payload = {"event": normalized_event, **fields}
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    )


def log_structured(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    logger.log(level, structured_event(event, **fields))
