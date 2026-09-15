from typing import Literal

from pydantic import BaseModel


ReminderLeadMinutes = Literal[15, 60, 1440]


class ActivityReminderUpdateRequest(BaseModel):
    lead_minutes: ReminderLeadMinutes = 60
