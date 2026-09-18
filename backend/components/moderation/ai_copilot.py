from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Persona
from components.message.model import Message, PrivateMessage
from components.moderation.ai_model import ModerationAIRecommendation
from components.moderation.ai_settings import moderation_ai_config
from components.moderation.model import TrustSafetyReport
from components.moderation.schemas import (
    ModerationAIAssessment,
    ModerationAIOutcomeRequest,
)
from components.moderation.trust_safety import _audit, _require_claim_owner


AI_SCHEMA_VERSION = "v1"
AI_PROVIDER_DISABLED = "disabled"
AI_PROVIDER_HTTP_JSON = "http_json"


class ModerationAIProviderError(RuntimeError):
    pass


class ModerationAIProvider(Protocol):
    key: str
    model_name: str | None

    async def assess(self, payload: dict) -> ModerationAIAssessment:
        ...


@dataclass(slots=True)
class DisabledModerationAIProvider:
    key: str = AI_PROVIDER_DISABLED
    model_name: str | None = None

    async def assess(self, payload: dict) -> ModerationAIAssessment:
        raise ModerationAIProviderError("moderation AI provider is disabled")


@dataclass(slots=True)
class HttpJsonModerationAIProvider:
    endpoint: str
    api_key: str = ""
    model_name: str | None = None
    timeout_seconds: float = 15.0
    key: str = AI_PROVIDER_HTTP_JSON

    def _request_sync(self, payload: dict) -> dict:
        body = json.dumps(
            {
                "task": "pubchat_moderation_assessment",
                "schema_version": AI_SCHEMA_VERSION,
                "model": self.model_name,
                "input": payload,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "PubChat-Moderation-AI/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(256 * 1024)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            raise ModerationAIProviderError("moderation AI provider request failed") from exc

        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModerationAIProviderError("moderation AI provider returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise ModerationAIProviderError("moderation AI provider returned invalid envelope")
        assessment = parsed.get("assessment", parsed)
        if not isinstance(assessment, dict):
            raise ModerationAIProviderError("moderation AI provider returned invalid assessment")
        return assessment

    async def assess(self, payload: dict) -> ModerationAIAssessment:
        raw = await asyncio.to_thread(self._request_sync, payload)
        try:
            return ModerationAIAssessment.model_validate(raw)
        except ValidationError as exc:
            raise ModerationAIProviderError("moderation AI provider response failed schema validation") from exc


def build_moderation_ai_provider() -> ModerationAIProvider:
    provider = moderation_ai_config.provider
    if provider in {"", AI_PROVIDER_DISABLED}:
        return DisabledModerationAIProvider()
    if provider == AI_PROVIDER_HTTP_JSON:
        if not moderation_ai_config.configured():
            raise ModerationAIProviderError("moderation AI provider configuration is incomplete")
        return HttpJsonModerationAIProvider(
            endpoint=moderation_ai_config.endpoint,
            api_key=moderation_ai_config.api_key,
            model_name=moderation_ai_config.model or None,
            timeout_seconds=moderation_ai_config.timeout_seconds,
        )
    raise ModerationAIProviderError("unsupported moderation AI provider")


def moderation_ai_public_config() -> dict:
    provider = moderation_ai_config.provider or AI_PROVIDER_DISABLED
    enabled = provider != AI_PROVIDER_DISABLED and moderation_ai_config.configured()
    return {
        "enabled": enabled,
        "provider": provider if enabled else AI_PROVIDER_DISABLED,
        "schema_version": AI_SCHEMA_VERSION,
        "max_assessments_per_report": moderation_ai_config.max_assessments_per_report,
    }


def _bounded_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value[: moderation_ai_config.max_text_chars]


async def _ai_evidence_payload(db: AsyncSession, report: TrustSafetyReport) -> dict:
    """Build the minimum evidence envelope needed by the copilot.

    No account identifiers, handles, sender/recipient identities, private-dialog history,
    attachment URLs or unrelated context are sent to the provider.
    """
    if report.source_type == "persona":
        persona = await db.get(Persona, report.source_uid)
        if not persona:
            return {"source_type": "persona", "available": False}
        return {
            "source_type": "persona",
            "available": True,
            "profile": {
                "bio": _bounded_text(persona.bio),
                "social_intent": _bounded_text(persona.social_intent),
            },
        }

    if report.source_type == "messenger_message":
        result = await db.execute(
            select(PrivateMessage).where(PrivateMessage.uid == report.source_uid).limit(1)
        )
        message = result.scalar_one_or_none()
        return {
            "source_type": "messenger_message",
            "available": bool(message),
            "message": (
                {
                    "content_type": message.content_type,
                    "content": _bounded_text(message.text),
                }
                if message
                else None
            ),
            "context_policy": "reported_message_only",
        }

    if report.source_type == "space_message":
        message = await db.get(Message, report.source_uid)
        return {
            "source_type": "space_message",
            "available": bool(message),
            "message": (
                {
                    "content_type": message.content_type,
                    "content": _bounded_text(message.text),
                }
                if message
                else None
            ),
            "context_policy": "reported_message_only",
        }

    return {"source_type": report.source_type, "available": False}


def _recommendation_projection(item: ModerationAIRecommendation) -> dict:
    return {
        "uid": str(item.uid),
        "report_uid": str(item.report_uid),
        "provider": item.provider_key,
        "model": item.model_name,
        "schema_version": item.schema_version,
        "category": item.category,
        "severity": item.severity,
        "confidence_percent": item.confidence_percent,
        "summary": item.summary,
        "recommended_action": item.recommended_action,
        "suggested_capability": item.suggested_capability,
        "suggested_scope_type": item.suggested_scope_type,
        "suggested_duration_minutes": item.suggested_duration_minutes,
        "rationale": item.rationale,
        "outcome": item.outcome,
        "outcome_note": item.outcome_note,
        "outcome_by_account_uid": (
            str(item.outcome_by_account_uid) if item.outcome_by_account_uid else None
        ),
        "outcome_at": item.outcome_at.isoformat() if item.outcome_at else None,
        "created_at": item.created_at.isoformat(),
    }


async def create_moderation_ai_assessment(
    db: AsyncSession,
    report_uid: UUID,
    moderator_account_uid: UUID,
    *,
    provider: ModerationAIProvider | None = None,
) -> dict:
    report = await _require_claim_owner(db, report_uid, moderator_account_uid)
    try:
        provider = provider or build_moderation_ai_provider()
    except ModerationAIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "moderation_ai_not_configured"},
        ) from exc
    if provider.key == AI_PROVIDER_DISABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "moderation_ai_not_configured"},
        )

    assessment_count = int(
        (
            await db.execute(
                select(func.count(ModerationAIRecommendation.uid)).where(
                    ModerationAIRecommendation.report_uid == report.uid
                )
            )
        ).scalar_one()
        or 0
    )
    if assessment_count >= moderation_ai_config.max_assessments_per_report:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_type": "moderation_ai_assessment_limit_reached",
                "max_assessments_per_report": moderation_ai_config.max_assessments_per_report,
            },
        )

    evidence = await _ai_evidence_payload(db, report)
    provider_payload = {
        "report": {
            "source_type": report.source_type,
            "reported_category": report.category,
            "priority": report.priority,
        },
        "evidence": evidence,
        "constraints": {
            "human_decision_required": True,
            "punitive_authority": False,
            "allowed_actions": ["none", "temporary_restriction"],
            "forbidden_capabilities": ["account.access"],
            "allowed_durations_minutes": [60, 1440, 10080, 43200],
        },
    }

    try:
        assessment = await provider.assess(provider_payload)
    except ModerationAIProviderError as exc:
        await _audit(
            db,
            report.uid,
            moderator_account_uid,
            "ai_assessment_failed",
            note=f"provider={provider.key}",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_type": "moderation_ai_provider_unavailable"},
        ) from exc

    item = ModerationAIRecommendation(
        report_uid=report.uid,
        requested_by_account_uid=moderator_account_uid,
        provider_key=provider.key,
        model_name=provider.model_name,
        schema_version=AI_SCHEMA_VERSION,
        category=assessment.category,
        severity=assessment.severity,
        confidence_percent=assessment.confidence_percent,
        summary=assessment.summary,
        recommended_action=assessment.recommended_action,
        suggested_capability=assessment.suggested_capability,
        suggested_scope_type=assessment.suggested_scope_type,
        suggested_duration_minutes=assessment.suggested_duration_minutes,
        rationale=assessment.rationale,
        outcome="not_used",
    )
    db.add(item)
    await db.flush()
    await _audit(
        db,
        report.uid,
        moderator_account_uid,
        "ai_assessment_created",
        note=f"recommendation={item.uid};provider={provider.key}",
    )
    await db.commit()
    await db.refresh(item)
    return _recommendation_projection(item)


async def list_moderation_ai_assessments(
    db: AsyncSession,
    report_uid: UUID,
    moderator_account_uid: UUID,
    *,
    limit: int = 10,
) -> list[dict]:
    await _require_claim_owner(db, report_uid, moderator_account_uid)
    result = await db.execute(
        select(ModerationAIRecommendation)
        .where(ModerationAIRecommendation.report_uid == report_uid)
        .order_by(ModerationAIRecommendation.created_at.desc())
        .limit(limit)
    )
    return [_recommendation_projection(item) for item in result.scalars().all()]


async def set_moderation_ai_outcome(
    db: AsyncSession,
    report_uid: UUID,
    recommendation_uid: UUID,
    moderator_account_uid: UUID,
    payload: ModerationAIOutcomeRequest,
) -> dict:
    report = await _require_claim_owner(db, report_uid, moderator_account_uid)
    result = await db.execute(
        select(ModerationAIRecommendation)
        .where(
            ModerationAIRecommendation.uid == recommendation_uid,
            ModerationAIRecommendation.report_uid == report.uid,
        )
        .with_for_update()
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "moderation_ai_recommendation_not_found"},
        )

    item.outcome = payload.outcome
    item.outcome_note = payload.note
    item.outcome_by_account_uid = moderator_account_uid
    item.outcome_at = datetime.utcnow()
    await _audit(
        db,
        report.uid,
        moderator_account_uid,
        "ai_recommendation_outcome",
        note=f"recommendation={item.uid};outcome={payload.outcome}",
    )
    await db.commit()
    await db.refresh(item)
    return _recommendation_projection(item)
