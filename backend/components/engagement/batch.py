from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.engagement.model import SpaceAppearance
from components.room.model import Room
from components.space.model import SpaceMembership, SpaceSettings
from components.space.service import DEFAULT_VISIBILITY, _get_account


class SpaceAppearanceBatchRequest(BaseModel):
    space_uids: list[UUID] = Field(min_length=1, max_length=100)

    @field_validator("space_uids")
    @classmethod
    def deduplicate_space_uids(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))


def _projection(item: SpaceAppearance | None, space_uid: UUID) -> dict:
    return {
        "space_uid": str(space_uid),
        "theme_preset": item.theme_preset if item else "lounge",
        "cover_preset": item.cover_preset if item else "soft-gradient",
        "ambient_icon": item.ambient_icon if item else None,
        "welcome_line": item.welcome_line if item else None,
        "updated_at": f"{item.updated_at.isoformat()}Z" if item and item.updated_at else None,
    }


async def get_space_appearance_batch(
    db: AsyncSession,
    viewer_uid: UUID | str,
    requested_space_uids: list[UUID],
) -> list[dict]:
    """Return appearance only for Spaces the viewer may resolve directly.

    Public and unlisted Spaces are addressable by UID. Private Spaces require
    ownership or an active canonical membership. Inaccessible UIDs are omitted
    rather than exposing whether a private Space exists.
    """
    account = await _get_account(db, viewer_uid)
    requested = list(dict.fromkeys(requested_space_uids))
    if not requested:
        return []

    active_membership_exists = (
        select(SpaceMembership.uid)
        .where(
            SpaceMembership.room_uid == Room.uid,
            SpaceMembership.account_uid == account.uid,
            SpaceMembership.status == "active",
        )
        .exists()
    )

    visible_result = await db.execute(
        select(Room.uid)
        .outerjoin(SpaceSettings, SpaceSettings.room_uid == Room.uid)
        .where(
            Room.uid.in_(requested),
            Room.is_active.is_(True),
            or_(
                func.coalesce(SpaceSettings.visibility, DEFAULT_VISIBILITY) != "private",
                Room.owner_uid == account.legacy_user_uid,
                active_membership_exists,
            ),
        )
    )
    visible = set(visible_result.scalars().all())
    if not visible:
        return []

    appearance_result = await db.execute(
        select(SpaceAppearance).where(SpaceAppearance.room_uid.in_(visible))
    )
    by_space = {item.room_uid: item for item in appearance_result.scalars().all()}
    return [
        _projection(by_space.get(space_uid), space_uid)
        for space_uid in requested
        if space_uid in visible
    ]
