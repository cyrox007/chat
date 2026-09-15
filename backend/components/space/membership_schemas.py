from typing import Literal

from pydantic import BaseModel


SpaceMembershipAction = Literal["approve", "reject", "remove"]
SpaceMembershipStatusFilter = Literal["active", "pending"]
SpaceMembershipRoleFilter = Literal["owner", "moderator", "member"]


class SpaceMembershipActionRequest(BaseModel):
    action: SpaceMembershipAction
