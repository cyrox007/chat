from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


GiftTarget = Literal["persona", "space"]


class SupportSettingsUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=280)

    @model_validator(mode="after")
    def normalize_note(self):
        if self.note is not None:
            self.note = " ".join(self.note.split()) or None
        return self


class GiftSendRequest(BaseModel):
    gift_code: str = Field(min_length=1, max_length=32)
    message: Optional[str] = Field(default=None, max_length=280)

    @model_validator(mode="after")
    def normalize_payload(self):
        self.gift_code = self.gift_code.strip().casefold()
        if self.message is not None:
            self.message = " ".join(self.message.split()) or None
        return self
