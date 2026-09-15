import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


SpacePurpose = Literal["community", "conversation", "meet_people", "games", "local"]
SpaceVisibility = Literal["public", "unlisted", "private"]
SpaceJoinPolicy = Literal["open", "request", "invite"]


class SpaceCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    purpose: SpacePurpose = "community"
    visibility: SpaceVisibility = "public"
    join_policy: SpaceJoinPolicy = "open"
    language: Optional[str] = Field(default=None, min_length=2, max_length=16)
    member_limit: int = Field(default=250, ge=2, le=5000)
    region: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("name", "description", "region", "country", "language")
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = re.sub(r"\s+", " ", value).strip()
        return normalized or None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        normalized: list[str] = []
        seen = set()
        for raw_tag in tags:
            tag = re.sub(r"\s+", " ", str(raw_tag)).strip()
            if not tag:
                continue
            if len(tag) > 40:
                raise ValueError("Each tag must be at most 40 characters")
            key = tag.casefold()
            if key not in seen:
                seen.add(key)
                normalized.append(tag)
        return normalized[:8]

    @model_validator(mode="after")
    def validate_visibility_policy(self):
        if self.visibility == "private" and self.join_policy == "open":
            raise ValueError("Private spaces cannot use open join policy")
        return self


class SpaceUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    purpose: Optional[SpacePurpose] = None
    visibility: Optional[SpaceVisibility] = None
    join_policy: Optional[SpaceJoinPolicy] = None
    language: Optional[str] = Field(default=None, min_length=2, max_length=16)
    member_limit: Optional[int] = Field(default=None, ge=2, le=5000)
    region: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[list[str]] = Field(default=None, max_length=8)

    @field_validator("name", "description", "region", "country", "language")
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = re.sub(r"\s+", " ", value).strip()
        return normalized or None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: Optional[list[str]]) -> Optional[list[str]]:
        if tags is None:
            return None
        normalized: list[str] = []
        seen = set()
        for raw_tag in tags:
            tag = re.sub(r"\s+", " ", str(raw_tag)).strip()
            if not tag:
                continue
            if len(tag) > 40:
                raise ValueError("Each tag must be at most 40 characters")
            key = tag.casefold()
            if key not in seen:
                seen.add(key)
                normalized.append(tag)
        return normalized[:8]


class SpaceMembershipRoleUpdateRequest(BaseModel):
    role: Literal["member", "moderator"]
