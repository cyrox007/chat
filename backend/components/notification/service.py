from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from components.engagement.model import SpaceActivity
from components.engagement.occurrence_model import ActivityOccurrence
from components.engagement.occurrence_service import (
    OCCURRENCE_GRACE_MINUTES,
    materialize_activity_occurrences,
)
from components.engagement.recurrence import utc_iso, utc_naive
from components.notification.model import ActivityReminderPreference, UserNotification
from components.notification.schemas import ActivityReminderUpdateRequest
from components.room.model import Room
from components.space.membership_service import _load_room, _require_active_member
from components.space.model import SpaceMembership
from components.space.service import _get_account


NOTIFICATION_KIND_ACTIVITY_REMINDER = "activity_reminder"
MAX_REMINDER_PREFERENCES_PER_SYNC = 200


def reminder_projection(item: ActivityReminderPreference) -> dict:
    return {
        "activity_uid": str(item.activity_uid),
        "lead_minutes": item.lead_minutes,
        "enabled": bool(item.enabled),
        "updated_at": utc_iso(item.updated_at),
    }


def notification_projection(
    item: UserNotification,
    occurrence_starts_at: datetime | None = None,
) -> dict:
    return {
        "uid": str(item.uid),
        "kind": item.kind,
        "title": item.title,
        "body": item.body,
        "context_space_uid": str(item.context_room_uid) if item.context_room_uid else None,
        "activity_uid": str(item.activity_uid) if item.activity_uid else None,
        "occurrence_uid": str(item.occurrence_uid) if item.occurrence_uid else None,
        "occurrence_starts_at": utc_iso(occurrence_starts_at),
        "is_read": item.read_at is not None,
        "read_at": utc_iso(item.read_at),
        "created_at": utc_iso(item.created_at),
    }


async def set_activity_reminder(
    db: AsyncSession,
    activity_uid: UUID,
    viewer_uid: UUID | str,
    payload: ActivityReminderUpdateRequest,
) -> dict:
    activity = await db.get(SpaceActivity, activity_uid)
    if not activity:
        raise HTTPException(status_code=404, detail={"error_type": "activity_not_found"})
    if activity.status != "scheduled":
        raise HTTPException(status_code=409, detail={"error_type": "activity_cancelled"})

    room = await _load_room(db, activity.room_uid)
    account = await _require_active_member(db, room, viewer_uid)
    item = await db.get(ActivityReminderPreference, (activity.uid, account.uid))
    if item is None:
        item = ActivityReminderPreference(
            activity_uid=activity.uid,
            account_uid=account.uid,
            lead_minutes=payload.lead_minutes,
            enabled=True,
        )
        db.add(item)
    else:
        item.lead_minutes = payload.lead_minutes
        item.enabled = True
        item.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(item)
    return reminder_projection(item)


async def delete_activity_reminder(
    db: AsyncSession,
    activity_uid: UUID,
    viewer_uid: UUID | str,
) -> None:
    activity = await db.get(SpaceActivity, activity_uid)
    if not activity:
        raise HTTPException(status_code=404, detail={"error_type": "activity_not_found"})
    room = await _load_room(db, activity.room_uid)
    account = await _require_active_member(db, room, viewer_uid)
    await db.execute(
        delete(ActivityReminderPreference).where(
            ActivityReminderPreference.activity_uid == activity.uid,
            ActivityReminderPreference.account_uid == account.uid,
        )
    )
    await db.commit()


async def list_space_reminders(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
) -> list[dict]:
    room = await _load_room(db, space_uid)
    account = await _require_active_member(db, room, viewer_uid)
    result = await db.execute(
        select(ActivityReminderPreference)
        .join(SpaceActivity, SpaceActivity.uid == ActivityReminderPreference.activity_uid)
        .where(
            SpaceActivity.room_uid == room.uid,
            ActivityReminderPreference.account_uid == account.uid,
            ActivityReminderPreference.enabled.is_(True),
        )
        .order_by(ActivityReminderPreference.updated_at.desc())
    )
    return [reminder_projection(item) for item in result.scalars().all()]


def _reminder_copy(activity: SpaceActivity, occurrence: ActivityOccurrence, now: datetime) -> tuple[str, str]:
    starts_at = utc_naive(occurrence.starts_at)
    remaining = starts_at - now
    if remaining <= timedelta(minutes=1):
        body = "Активность начинается сейчас. Откройте пространство, чтобы присоединиться."
    elif remaining < timedelta(hours=1):
        minutes = max(1, int(remaining.total_seconds() // 60))
        body = f"До начала примерно {minutes} мин. Откройте пространство, если планируете участвовать."
    elif remaining < timedelta(days=1):
        hours = max(1, int(remaining.total_seconds() // 3600))
        body = f"До начала примерно {hours} ч. Откройте пространство, чтобы посмотреть детали."
    else:
        body = "Встреча запланирована на ближайший день. Откройте пространство, чтобы посмотреть детали."
    return f"Скоро: {activity.title}", body


async def sync_activity_reminders(
    db: AsyncSession,
    viewer_uid: UUID | str,
    *,
    now: datetime | None = None,
) -> None:
    account = await _get_account(db, viewer_uid)
    current = utc_naive(now or datetime.now(timezone.utc))

    active_membership_exists = (
        select(SpaceMembership.uid)
        .where(
            SpaceMembership.room_uid == SpaceActivity.room_uid,
            SpaceMembership.account_uid == account.uid,
            SpaceMembership.status == "active",
        )
        .exists()
    )

    result = await db.execute(
        select(ActivityReminderPreference, SpaceActivity)
        .join(SpaceActivity, SpaceActivity.uid == ActivityReminderPreference.activity_uid)
        .join(Room, Room.uid == SpaceActivity.room_uid)
        .where(
            ActivityReminderPreference.account_uid == account.uid,
            ActivityReminderPreference.enabled.is_(True),
            SpaceActivity.status == "scheduled",
            Room.is_active.is_(True),
            or_(Room.owner_uid == account.legacy_user_uid, active_membership_exists),
        )
        .order_by(ActivityReminderPreference.updated_at.desc())
        .limit(MAX_REMINDER_PREFERENCES_PER_SYNC)
    )

    for preference, activity in result.all():
        occurrences = await materialize_activity_occurrences(db, activity, now=current)
        lead = timedelta(minutes=preference.lead_minutes)
        grace = timedelta(minutes=OCCURRENCE_GRACE_MINUTES)
        for occurrence in occurrences:
            if occurrence.status != "scheduled":
                continue
            starts_at = utc_naive(occurrence.starts_at)
            if starts_at - lead > current or current > starts_at + grace:
                continue

            title, body = _reminder_copy(activity, occurrence, current)
            dedupe_key = f"activity:{activity.uid}:occurrence:{occurrence.uid}"
            await db.execute(
                insert(UserNotification)
                .values(
                    account_uid=account.uid,
                    kind=NOTIFICATION_KIND_ACTIVITY_REMINDER,
                    dedupe_key=dedupe_key,
                    title=title,
                    body=body,
                    context_room_uid=activity.room_uid,
                    activity_uid=activity.uid,
                    occurrence_uid=occurrence.uid,
                    created_at=current,
                )
                .on_conflict_do_nothing(constraint="uq_user_notification_dedupe")
            )

    await db.commit()


async def list_notifications(
    db: AsyncSession,
    viewer_uid: UUID | str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int, int]:
    account = await _get_account(db, viewer_uid)
    filters = (UserNotification.account_uid == account.uid,)
    total = int((await db.execute(select(func.count(UserNotification.uid)).where(*filters))).scalar_one() or 0)
    unread = int(
        (
            await db.execute(
                select(func.count(UserNotification.uid)).where(
                    *filters,
                    UserNotification.read_at.is_(None),
                )
            )
        ).scalar_one()
        or 0
    )
    result = await db.execute(
        select(UserNotification, ActivityOccurrence.starts_at)
        .outerjoin(ActivityOccurrence, ActivityOccurrence.uid == UserNotification.occurrence_uid)
        .where(*filters)
        .order_by(UserNotification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [notification_projection(item, starts_at) for item, starts_at in result.all()], total, unread


async def unread_notification_count(
    db: AsyncSession,
    viewer_uid: UUID | str,
) -> int:
    account = await _get_account(db, viewer_uid)
    return int(
        (
            await db.execute(
                select(func.count(UserNotification.uid)).where(
                    UserNotification.account_uid == account.uid,
                    UserNotification.read_at.is_(None),
                )
            )
        ).scalar_one()
        or 0
    )


async def mark_notification_read(
    db: AsyncSession,
    notification_uid: UUID,
    viewer_uid: UUID | str,
) -> dict:
    account = await _get_account(db, viewer_uid)
    result = await db.execute(
        select(UserNotification, ActivityOccurrence.starts_at)
        .outerjoin(ActivityOccurrence, ActivityOccurrence.uid == UserNotification.occurrence_uid)
        .where(
            UserNotification.uid == notification_uid,
            UserNotification.account_uid == account.uid,
        )
        .limit(1)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail={"error_type": "notification_not_found"})
    item, starts_at = row
    if item.read_at is None:
        item.read_at = datetime.utcnow()
        await db.commit()
        await db.refresh(item)
    return notification_projection(item, starts_at)


async def mark_all_notifications_read(
    db: AsyncSession,
    viewer_uid: UUID | str,
) -> None:
    account = await _get_account(db, viewer_uid)
    await db.execute(
        update(UserNotification)
        .where(
            UserNotification.account_uid == account.uid,
            UserNotification.read_at.is_(None),
        )
        .values(read_at=datetime.utcnow())
    )
    await db.commit()
