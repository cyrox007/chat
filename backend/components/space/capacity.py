from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.room.model import Room
from components.space.model import SpaceMembership, SpaceSettings


async def assert_space_capacity_available(
    db: AsyncSession,
    room_uid: UUID,
    *,
    default_member_limit: int,
) -> tuple[int, int]:
    """Serialize all membership activations for a Space and enforce capacity.

    The Room row is the canonical lock key because every current/legacy Space has
    one, while SpaceSettings can be absent for historical rows. The lock remains
    held until the caller commits or rolls back, so join/request approval/invite
    acceptance cannot all consume the same final slot concurrently.
    """
    lock_result = await db.execute(
        select(Room.uid)
        .where(
            Room.uid == room_uid,
            Room.is_active.is_(True),
        )
        .with_for_update()
    )
    if lock_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "space_not_found"},
        )

    settings_result = await db.execute(
        select(SpaceSettings.member_limit)
        .where(SpaceSettings.room_uid == room_uid)
        .limit(1)
    )
    member_limit = settings_result.scalar_one_or_none()
    if member_limit is None:
        member_limit = default_member_limit

    count_result = await db.execute(
        select(func.count(SpaceMembership.uid)).where(
            SpaceMembership.room_uid == room_uid,
            SpaceMembership.status == "active",
        )
    )
    active_count = int(count_result.scalar_one() or 0)
    if active_count >= int(member_limit):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "space_full"},
        )
    return active_count, int(member_limit)
