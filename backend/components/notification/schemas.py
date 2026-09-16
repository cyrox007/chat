from typing import Literal

from pydantic import BaseModel, Field


ReminderLeadMinutes = Literal[15, 60, 1440]


class ActivityReminderUpdateRequest(BaseModel):
    lead_minutes: ReminderLeadMinutes = 60


class MessageNotificationPreferenceUpdateRequest(BaseModel):
    messenger_in_app: bool | None = None
    space_in_app: bool | None = None
    messenger_sound: bool | None = None
    space_sound: bool | None = None
    email_unread_dm_nudge: bool | None = None
    web_push_messenger: bool | None = None
    web_push_space: bool | None = None


class WebPushKeys(BaseModel):
    p256dh: str = Field(min_length=16, max_length=256)
    auth: str = Field(min_length=8, max_length=128)


class WebPushSubscriptionUpsertRequest(BaseModel):
    endpoint: str = Field(min_length=16, max_length=4096)
    keys: WebPushKeys


class WebPushSubscriptionRemoveRequest(BaseModel):
    endpoint: str = Field(min_length=16, max_length=4096)
