from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


RoundType = Literal["icebreaker", "choice", "story_chain"]
RoundStatusUpdate = Literal["closed"]
RoundChoice = Literal["a", "b"]


class ConversationRoundCreateRequest(BaseModel):
    round_type: RoundType
    prompt: str = Field(min_length=3, max_length=500)
    option_a: Optional[str] = Field(default=None, max_length=120)
    option_b: Optional[str] = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_round(self):
        self.prompt = " ".join(self.prompt.split())
        if self.option_a is not None:
            self.option_a = " ".join(self.option_a.split()) or None
        if self.option_b is not None:
            self.option_b = " ".join(self.option_b.split()) or None

        if self.round_type == "choice":
            if not self.option_a or not self.option_b:
                raise ValueError("choice round requires option_a and option_b")
            if self.option_a.casefold() == self.option_b.casefold():
                raise ValueError("choice options must be different")
        elif self.option_a is not None or self.option_b is not None:
            raise ValueError("options are only allowed for choice rounds")
        return self


class ConversationRoundUpdateRequest(BaseModel):
    status: RoundStatusUpdate


class ConversationRoundResponseRequest(BaseModel):
    choice: Optional[RoundChoice] = None
    body: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def normalize_response(self):
        if self.body is not None:
            self.body = self.body.strip() or None
        if self.choice is None and self.body is None:
            raise ValueError("choice or body is required")
        return self
