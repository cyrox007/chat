from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


EventStatus = Literal["scheduled", "cancelled"]


def _clean_required(value: str) -> str:
    normalized = " ".join(str(value).split())
    if not normalized:
        raise ValueError("Value cannot be blank")
    return normalized


class SpaceRuleCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    body: str = Field(min_length=2, max_length=4000)
    position: int = Field(default=0, ge=0, le=1000)

    @field_validator("title", "body")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return _clean_required(value)


class SpaceRuleUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=120)
    body: Optional[str] = Field(default=None, min_length=2, max_length=4000)
    position: Optional[int] = Field(default=None, ge=0, le=1000)

    @field_validator("title", "body")
    @classmethod
    def clean_text(cls, value: Optional[str]) -> Optional[str]:
        return _clean_required(value) if value is not None else None


class SpaceEventCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=4000)
    starts_at: datetime
    ends_at: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return _clean_required(value)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_times(self):
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class SpaceEventUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, max_length=4000)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    status: Optional[EventStatus] = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: Optional[str]) -> Optional[str]:
        return _clean_required(value) if value is not None else None

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
