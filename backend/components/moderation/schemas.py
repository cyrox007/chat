from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


ReportCategory = Literal["spam", "harassment", "sexual", "violence", "privacy", "other"]
ReportStatus = Literal["open", "reviewing", "resolved", "dismissed"]
ModerationActionType = Literal["warning", "restrict"]
AppealResolution = Literal["uphold", "overturn"]

TrustSafetySourceType = Literal["persona", "messenger_message", "space_message"]
TrustSafetyCategory = Literal[
    "spam",
    "harassment",
    "sexual",
    "violence",
    "privacy",
    "impersonation",
    "fraud",
    "hate",
    "self_harm",
    "minor_safety",
    "other",
]
TrustSafetyStatus = Literal["triage", "in_review", "escalated", "resolved", "dismissed"]
TrustSafetyPriority = Literal["high", "normal", "low"]
TrustSafetyResolutionCode = Literal[
    "no_violation",
    "handled",
    "needs_platform_action",
    "duplicate",
    "insufficient_context",
    "other",
]


class ModerationReportCreateRequest(BaseModel):
    target_account_uid: Optional[UUID] = None
    message_uid: Optional[UUID] = None
    category: ReportCategory
    description: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_target(self):
        if self.target_account_uid is None and self.message_uid is None:
            raise ValueError("target_account_uid or message_uid is required")
        if self.description is not None:
            self.description = self.description.strip() or None
        return self


class ModerationReportStatusRequest(BaseModel):
    status: Literal["reviewing", "dismissed"]


class ModerationActionCreateRequest(BaseModel):
    target_account_uid: UUID
    action_type: ModerationActionType
    reason: str = Field(min_length=3, max_length=2000)
    report_uid: Optional[UUID] = None
    duration_minutes: Optional[int] = Field(default=None, ge=5, le=43200)

    @model_validator(mode="after")
    def validate_action(self):
        self.reason = " ".join(self.reason.split())
        if self.action_type == "warning" and self.duration_minutes is not None:
            raise ValueError("warning does not accept duration_minutes")
        return self


class ModerationAppealCreateRequest(BaseModel):
    body: str = Field(min_length=10, max_length=4000)

    @model_validator(mode="after")
    def clean_body(self):
        self.body = self.body.strip()
        return self


class ModerationAppealResolveRequest(BaseModel):
    decision: AppealResolution
    resolution: str = Field(min_length=3, max_length=4000)

    @model_validator(mode="after")
    def clean_resolution(self):
        self.resolution = self.resolution.strip()
        return self


class TrustSafetyReportCreateRequest(BaseModel):
    """User-submitted platform report. Target/priority are always server-derived."""

    model_config = ConfigDict(extra="forbid")

    source_type: TrustSafetySourceType
    source_uid: UUID
    category: TrustSafetyCategory
    description: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def clean_description(self):
        if self.description is not None:
            self.description = self.description.strip() or None
        return self


class TrustSafetyDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["resolved", "dismissed", "escalated"]
    resolution_code: TrustSafetyResolutionCode
    public_explanation: str = Field(min_length=3, max_length=1000)

    @model_validator(mode="after")
    def clean_explanation(self):
        self.public_explanation = " ".join(self.public_explanation.split())
        if self.status == "escalated" and self.resolution_code != "needs_platform_action":
            raise ValueError("escalated reports require needs_platform_action")
        if self.status == "dismissed" and self.resolution_code == "needs_platform_action":
            raise ValueError("dismissed reports cannot require platform action")
        return self
