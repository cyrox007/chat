from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


PersonaAccent = Literal["plum", "berry", "forest", "ocean", "sand"]
PersonaBackground = Literal["soft", "paper", "mist", "night"]
PersonaFrame = Literal["none", "soft", "double", "badge"]
SpaceTheme = Literal["lounge", "warm", "garden", "studio", "night"]
SpaceCover = Literal["soft-gradient", "paper", "mist", "linen", "night"]
ActivityType = Literal["hangout", "quiz", "game", "watch", "local", "creative"]
ActivityRecurrence = Literal["none", "daily", "weekly", "monthly"]
ActivityStatus = Literal["scheduled", "cancelled"]
RSVPStatus = Literal["interested", "going"]


def _require_timezone(value: datetime | None) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("starts_at must include an explicit timezone")


class PersonaAppearanceUpdateRequest(BaseModel):
    accent_preset: Optional[PersonaAccent] = None
    background_preset: Optional[PersonaBackground] = None
    avatar_frame_preset: Optional[PersonaFrame] = None
    status_line: Optional[str] = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def normalize_status_line(self):
        if self.status_line is not None:
            self.status_line = " ".join(self.status_line.split()) or None
        return self


class SpaceAppearanceUpdateRequest(BaseModel):
    theme_preset: Optional[SpaceTheme] = None
    cover_preset: Optional[SpaceCover] = None
    ambient_icon: Optional[str] = Field(default=None, max_length=16)
    welcome_line: Optional[str] = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def normalize_copy(self):
        if self.ambient_icon is not None:
            self.ambient_icon = self.ambient_icon.strip() or None
        if self.welcome_line is not None:
            self.welcome_line = " ".join(self.welcome_line.split()) or None
        return self


class ActivityCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    activity_type: ActivityType = "hangout"
    starts_at: datetime
    recurrence: ActivityRecurrence = "none"

    @model_validator(mode="after")
    def normalize_text(self):
        self.title = " ".join(self.title.split())
        if self.description is not None:
            self.description = self.description.strip() or None
        _require_timezone(self.starts_at)
        return self


class ActivityUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    activity_type: Optional[ActivityType] = None
    starts_at: Optional[datetime] = None
    recurrence: Optional[ActivityRecurrence] = None
    status: Optional[ActivityStatus] = None

    @model_validator(mode="after")
    def normalize_text(self):
        if self.title is not None:
            self.title = " ".join(self.title.split())
        if self.description is not None:
            self.description = self.description.strip() or None
        _require_timezone(self.starts_at)
        return self


class ActivityRSVPRequest(BaseModel):
    status: RSVPStatus
