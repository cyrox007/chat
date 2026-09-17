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

PlatformCapability = Literal[
    "messenger.send",
    "space.chat.send",
    "media.upload",
    "space.create",
    "space.join",
    "invitation.send",
    "profile.edit",
    "discovery.publish",
    "account.access",
]
PlatformRestrictionScope = Literal["platform", "space"]

ModerationAISeverity = Literal["low", "medium", "high", "critical"]
ModerationAIAction = Literal["none", "temporary_restriction"]
ModerationAICapability = Literal[
    "messenger.send",
    "space.chat.send",
    "media.upload",
    "space.create",
    "space.join",
    "invitation.send",
    "profile.edit",
    "discovery.publish",
]
ModerationAIOutcome = Literal["not_used", "accepted", "modified", "rejected"]
ModerationAIDurationMinutes = Literal[60, 1440, 10080, 43200]


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


class PlatformRestrictionCreateRequest(BaseModel):
    """Human platform action; authority and permissions are resolved server-side."""

    model_config = ConfigDict(extra="forbid")

    target_account_uid: UUID
    capability: PlatformCapability
    scope_type: PlatformRestrictionScope = "platform"
    scope_uid: Optional[UUID] = None
    reason_code: str = Field(min_length=2, max_length=48, pattern=r"^[a-z0-9_.-]+$")
    public_explanation: str = Field(min_length=3, max_length=1000)
    duration_minutes: Optional[int] = Field(default=None, ge=5, le=525600)
    report_uid: Optional[UUID] = None

    @model_validator(mode="after")
    def validate_scope(self):
        self.public_explanation = " ".join(self.public_explanation.split())
        if self.scope_type == "platform" and self.scope_uid is not None:
            raise ValueError("platform scope must not contain scope_uid")
        if self.scope_type == "space" and self.scope_uid is None:
            raise ValueError("space scope requires scope_uid")
        if self.capability == "account.access" and self.scope_type != "platform":
            raise ValueError("account.access restriction must be platform-scoped")
        return self


class PlatformRestrictionRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=1000)

    @model_validator(mode="after")
    def clean_reason(self):
        self.reason = " ".join(self.reason.split())
        return self


class PlatformRestrictionAppealCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=10, max_length=4000)

    @model_validator(mode="after")
    def clean_body(self):
        self.body = self.body.strip()
        return self


class PlatformRestrictionAppealResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: AppealResolution
    resolution: str = Field(min_length=3, max_length=4000)

    @model_validator(mode="after")
    def clean_resolution(self):
        self.resolution = " ".join(self.resolution.split())
        return self


class ModerationAIAssessment(BaseModel):
    """Structured provider output. It is advisory and never a moderation action."""

    model_config = ConfigDict(extra="forbid")

    category: TrustSafetyCategory
    severity: ModerationAISeverity
    confidence_percent: int = Field(ge=0, le=100)
    summary: str = Field(min_length=3, max_length=1000)
    recommended_action: ModerationAIAction
    suggested_capability: Optional[ModerationAICapability] = None
    suggested_scope_type: PlatformRestrictionScope = "platform"
    suggested_duration_minutes: Optional[ModerationAIDurationMinutes] = None
    rationale: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def validate_recommendation(self):
        self.summary = " ".join(self.summary.split())
        self.rationale = " ".join(self.rationale.split())
        if self.recommended_action == "none":
            if self.suggested_capability is not None or self.suggested_duration_minutes is not None:
                raise ValueError("none action cannot contain a restriction suggestion")
        else:
            if self.suggested_capability is None or self.suggested_duration_minutes is None:
                raise ValueError("temporary_restriction requires capability and duration")
        return self


class ModerationAIOutcomeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: ModerationAIOutcome
    note: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def clean_note(self):
        if self.note is not None:
            self.note = " ".join(self.note.split()) or None
        return self
