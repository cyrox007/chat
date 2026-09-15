from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from components.engagement.model import SpaceActivity
from components.engagement.occurrence_model import ActivityOccurrence
from components.engagement.recurrence import occurrences_between, utc_iso, utc_naive
from components.space.membership_service import _load_room, _require_active_member


OCCURRENCE_HORIZON_DAYS = 45
OCCURRENCE_GRACE_MINUTES = 15
MAX_MATERIALIZED_PER_ACTIVITY = 100


def occurrence_projection(item: ActivityOccurrence) -> dict:
    return {
        "uid": str(item.uid),
        "activity_uid": str(item.activity_uid),
        "starts_at": utc_iso(item.starts_at),
        "status": item.status,
        "created_at": utc_iso(item.created_at),
        "updated_at": utc_iso(item.updated_at),
    }


async def materialize_activity_occurrences(
    db: AsyncSession,
    activity: SpaceActivity,
    *,
    now: datetime | None = None,
    horizon_days: int = OCCURRENCE_HORIZON_DAYS,
) -> list[ActivityOccurrence]:
    """Materialize a bounded rolling window with DB-level race protection."""
    if activity.status != "scheduled":
        return []

    current = utc_naive(now or datetime.now(timezone.utc))
    window_start = current - timedelta(minutes=OCCURRENCE_GRACE_MINUTES)
    window_end = current + timedelta(days=max(1, min(horizon_days, OCCURRENCE_HORIZON_DAYS)))
    starts = occurrences_between(
        activity.starts_at,
        activity.recurrence,
        window_start,
        window_end,
        limit=MAX_MATERIALIZED_PER_ACTIVITY,
    )
    if not starts:
        return []

    rows = [
        {
            "uid": uuid4(),
            "activity_uid": activity.uid,
            "starts_at": starts_at,
            "status": "scheduled",
            "created_at": current,
            "updated_at": current,
        }
        for starts_at in starts
    ]
    await db.execute(
        insert(ActivityOccurrence)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_activity_occurrence_start")
    )
    await db.flush()

    result = await db.execute(
        select(ActivityOccurrence)
        .where(
            ActivityOccurrence.activity_uid == activity.uid,
            ActivityOccurrence.starts_at >= window_start,
            ActivityOccurrence.starts_at <= window_end,
        )
        .order_by(ActivityOccurrence.starts_at.asc())
    )
    return result.scalars().all()


async def list_activity_occurrences(
    db: AsyncSession,
    activity_uid: UUID,
    viewer_uid: UUID | str,
    *,
    limit: int = 20,
) -> list[dict]:
    activity = await db.get(SpaceActivity, activity_uid)
    if not activity:
        raise HTTPException(status_code=404, detail={"error_type": "activity_not_found"})
    room = await _load_room(db, activity.room_uid)
    await _require_active_member(db, room, viewer_uid)

    occurrences = await materialize_activity_occurrences(db, activity)
    await db.commit()
    return [occurrence_projection(item) for item in occurrences[:limit]]
