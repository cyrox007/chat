from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.room.model import Room
from components.space.model import SpaceMembership, SpaceSettings


@dataclass(frozen=True, slots=True)
class SpaceAdmissionPolicy:
    join_policy: str
    member_limit: int


async def lock_space_admission_policy(
    db: AsyncSession,
    room_uid: UUID,
    *,
    default_join_policy: str,
    default_member_limit: int,
) -> SpaceAdmissionPolicy:
    """Serialize capacity-changing membership transitions per Space.

    The SpaceSettings row is the canonical admission lock. Historical/partial
    data without settings falls back to locking the Room row so the invariant
    remains safe instead of silently reverting to a racy COUNT check.
    """
    result = await db.execute(
        select(SpaceSettings)
        .where(SpaceSettings.room_uid == room_uid)
        .with_for_update()
    )
    settings = result.scalar_one_or_none()
    if settings is not None:
        return SpaceAdmissionPolicy(
            join_policy=settings.join_policy,
            member_limit=max(1, int(settings.member_limit)),
        )

    room_lock = await db.execute(
        select(Room.uid)
        .where(Room.uid == room_uid)
        .with_for_update()
    )
    if room_lock.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "space_not_found"},
        )
    return SpaceAdmissionPolicy(
        join_policy=default_join_policy,
        member_limit=max(1, int(default_member_limit)),
    )


async def assert_space_has_capacity(
    db: AsyncSession,
    room_uid: UUID,
    *,
    member_limit: int,
) -> int:
    """Count active memberships while the caller owns the admission lock."""
    count_result = await db.execute(
        select(func.count(SpaceMembership.uid)).where(
            SpaceMembership.room_uid == room_uid,
            SpaceMembership.status == "active",
        )
    )
    active_count = int(count_result.scalar_one() or 0)
    if active_count >= member_limit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "space_full"},
        )
    return active_count
