from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


RealtimeTarget = Literal["room", "messenger"]


class RealtimeTicketRequest(BaseModel):
    target: RealtimeTarget
    room_uid: Optional[UUID] = None

    @model_validator(mode="after")
    def validate_target_resource(self):
        if self.target == "room" and self.room_uid is None:
            raise ValueError("room_uid is required for room realtime tickets")
        if self.target == "messenger" and self.room_uid is not None:
            raise ValueError("room_uid is not allowed for messenger realtime tickets")
        return self


class RealtimeAuthFrame(BaseModel):
    type: Literal["auth"]
    ticket: str = Field(min_length=20, max_length=256)
    resume_token: Optional[str] = Field(default=None, max_length=256)
