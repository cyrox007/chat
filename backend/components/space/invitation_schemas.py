from typing import Literal

from pydantic import BaseModel


InvitationAction = Literal["accept", "decline"]


class SpaceInvitationActionRequest(BaseModel):
    action: InvitationAction
