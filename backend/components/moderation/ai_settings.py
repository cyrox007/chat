from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModerationAIConfig:
    provider: str
    endpoint: str
    api_key: str
    model: str
    timeout_seconds: float
    max_text_chars: int
    max_assessments_per_report: int

    def configured(self) -> bool:
        if self.provider == "disabled":
            return False
        if self.provider == "http_json":
            return bool(self.endpoint)
        return False


def load_moderation_ai_config() -> ModerationAIConfig:
    provider = os.getenv("MODERATION_AI_PROVIDER", "disabled").strip().lower() or "disabled"
    return ModerationAIConfig(
        provider=provider,
        endpoint=os.getenv("MODERATION_AI_ENDPOINT", "").strip(),
        api_key=os.getenv("MODERATION_AI_API_KEY", ""),
        model=os.getenv("MODERATION_AI_MODEL", "").strip(),
        timeout_seconds=max(1.0, float(os.getenv("MODERATION_AI_TIMEOUT_SECONDS", "15"))),
        max_text_chars=max(256, min(20000, int(os.getenv("MODERATION_AI_MAX_TEXT_CHARS", "4000")))),
        max_assessments_per_report=max(
            1,
            min(20, int(os.getenv("MODERATION_AI_MAX_ASSESSMENTS_PER_REPORT", "3"))),
        ),
    )


moderation_ai_config = load_moderation_ai_config()
