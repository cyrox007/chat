from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


ReportCategory = Literal["spam", "harassment", "sexual", "violence", "privacy", "other"]
ReportStatus = Literal["open", "reviewing", "resolved", "dismissed"]
ModerationActionType = Literal["warning", "restrict"]
AppealResolution = Literal["uphold", "overturn"]


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
