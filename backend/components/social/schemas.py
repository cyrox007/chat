from typing import Literal

from pydantic import BaseModel


FriendAction = Literal["request", "accept", "reject", "remove"]
RequestDirection = Literal["incoming", "outgoing"]


class FriendActionRequest(BaseModel):
    action: FriendAction
