from collections import defaultdict
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.achievement.service import grant_achievement
from components.engagement.model import ActivityRSVP, PersonaAppearance, SpaceActivity, SpaceAppearance
from components.engagement.recurrence import next_occurrence as _next_occurrence, utc_iso as _utc_iso, utc_naive as _utc_naive
from components.engagement.round_model import ConversationRound
from components.engagement.schemas import (
    ActivityCreateRequest,
    ActivityRSVPRequest,
    ActivityUpdateRequest,
    PersonaAppearanceUpdateRequest,
    SpaceAppearanceUpdateRequest,
)
from components.identity.model import Persona
from components.social.privacy import can_view_profile
from components.space.membership_service import _load_room, _manager_context, _require_active_member
from components.space.service import _get_account, get_space


def _persona_appearance_projection(item: PersonaAppearance | None, persona_uid: UUID) -> dict:
    return {
        "persona_uid": str(persona_uid),
        "accent_preset": item.accent_preset if item else "plum",
        "background_preset": item.background_preset if item else "soft",
        "avatar_frame_preset": item.avatar_frame_preset if item else "none",
        "status_line": item.status_line if item else None,
        "updated_at": _utc_iso(item.updated_at) if item else None,
    }


def _space_appearance_projection(item: SpaceAppearance | None, space_uid: UUID) -> dict:
    return {
        "space_uid": str(space_uid),
        "theme_preset": item.theme_preset if item else "lounge",
        "cover_preset": item.cover_preset if item else "soft-gradient",
        "ambient_icon": item.ambient_icon if item else None,
        "welcome_line": item.welcome_line if item else None,
        "updated_at": _utc_iso(item.updated_at) if item else None,
    }


async def get_persona_appearance(
    db: AsyncSession,
    persona_uid: UUID,
    viewer_uid: UUID | str,
) -> dict:
    persona = await db.get(Persona, persona_uid)
    if not persona:
        raise HTTPException(status_code=404, detail={"error_type": "persona_not_found"})
    if not await can_view_profile(db, viewer_uid, persona.account_uid):
        raise HTTPException(status_code=404, detail={"error_type": "persona_not_found"})
    item = await db.get(PersonaAppearance, persona.uid)
    return _persona_appearance_projection(item, persona.uid)


async def update_my_persona_appearance(
    db: AsyncSession,
    viewer_uid: UUID | str,
    payload: PersonaAppearanceUpdateRequest,
) -> dict:
    account = await _get_account(db, viewer_uid)
    result = await db.execute(
        select(Persona).where(Persona.account_uid == account.uid, Persona.is_primary.is_(True)).limit(1)
    )
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=409, detail={"error_type": "primary_persona_missing"})

    item = await db.get(PersonaAppearance, persona.uid)
    if not item:
        item = PersonaAppearance(persona_uid=persona.uid)
        db.add(item)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    return _persona_appearance_projection(item, persona.uid)


async def get_space_appearance(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
) -> dict:
    await get_space(db, space_uid, viewer_uid)
    item = await db.get(SpaceAppearance, space_uid)
    return _space_appearance_projection(item, space_uid)


async def update_space_appearance(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    payload: SpaceAppearanceUpdateRequest,
) -> dict:
    room = await _load_room(db, space_uid)
    _, role = await _manager_context(db, room, viewer_uid)
    if role not in {"owner", "moderator"}:
        raise HTTPException(status_code=403, detail={"error_type": "space_appearance_manage_required"})

    item = await db.get(SpaceAppearance, room.uid)
    if not item:
        item = SpaceAppearance(room_uid=room.uid)
        db.add(item)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    return _space_appearance_projection(item, room.uid)


def _activity_projection(
    activity: SpaceActivity,
    counts: dict[str, int] | None = None,
    viewer_rsvp: str | None = None,
) -> dict:
    counts = counts or {}
    next_starts_at = _next_occurrence(
        activity.starts_at,
        activity.recurrence,
        timezone_name=activity.timezone_name or "UTC",
    )
    return {
        "uid": str(activity.uid),
        "space_uid": str(activity.room_uid),
        "created_by_account_uid": str(activity.created_by_account_uid) if activity.created_by_account_uid else None,
        "title": activity.title,
        "description": activity.description,
        "activity_type": activity.activity_type,
        "starts_at": _utc_iso(activity.starts_at),
        "next_starts_at": _utc_iso(next_starts_at),
        "recurrence": activity.recurrence,
        "timezone": activity.timezone_name or "UTC",
        "status": activity.status,
        "rsvp": {
            "interested": counts.get("interested", 0),
            "going": counts.get("going", 0),
            "viewer": viewer_rsvp,
        },
        "created_at": _utc_iso(activity.created_at),
        "updated_at": _utc_iso(activity.updated_at),
    }


async def _single_activity_projection(
    db: AsyncSession,
    activity: SpaceActivity,
    viewer_account_uid: UUID,
) -> dict:
    counts_result = await db.execute(
        select(ActivityRSVP.status, func.count(ActivityRSVP.account_uid))
        .where(ActivityRSVP.activity_uid == activity.uid)
        .group_by(ActivityRSVP.status)
    )
    counts = {key: int(value) for key, value in counts_result.all()}
    viewer_rsvp = await db.get(ActivityRSVP, (activity.uid, viewer_account_uid))
    return _activity_projection(activity, counts, viewer_rsvp.status if viewer_rsvp else None)


async def list_activities(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    account = await _get_account(db, viewer_uid)
    await get_space(db, space_uid, account.uid)
    filters = (SpaceActivity.room_uid == space_uid,)
    total = int((await db.execute(select(func.count(SpaceActivity.uid)).where(*filters))).scalar_one() or 0)
    result = await db.execute(
        select(SpaceActivity)
        .where(*filters)
        .order_by(SpaceActivity.starts_at.asc(), SpaceActivity.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    activities = result.scalars().all()
    if not activities:
        return [], total

    activity_uids = [activity.uid for activity in activities]
    counts_result = await db.execute(
        select(ActivityRSVP.activity_uid, ActivityRSVP.status, func.count(ActivityRSVP.account_uid))
        .where(ActivityRSVP.activity_uid.in_(activity_uids))
        .group_by(ActivityRSVP.activity_uid, ActivityRSVP.status)
    )
    counts_by_activity: dict[UUID, dict[str, int]] = defaultdict(dict)
    for activity_uid, rsvp_status, count in counts_result.all():
        counts_by_activity[activity_uid][rsvp_status] = int(count)

    viewer_result = await db.execute(
        select(ActivityRSVP.activity_uid, ActivityRSVP.status).where(
            ActivityRSVP.activity_uid.in_(activity_uids),
            ActivityRSVP.account_uid == account.uid,
        )
    )
    viewer_by_activity = {activity_uid: rsvp_status for activity_uid, rsvp_status in viewer_result.all()}

    projected = [
        _activity_projection(
            activity,
            counts_by_activity.get(activity.uid),
            viewer_by_activity.get(activity.uid),
        )
        for activity in activities
    ]
    projected.sort(key=lambda item: item["next_starts_at"] or item["starts_at"])
    return projected, total


async def create_activity(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    payload: ActivityCreateRequest,
) -> dict:
    room = await _load_room(db, space_uid)
    account = await _require_active_member(db, room, viewer_uid)
    activity = SpaceActivity(
        room_uid=room.uid,
        created_by_account_uid=account.uid,
        title=payload.title,
        description=payload.description,
        activity_type=payload.activity_type,
        starts_at=_utc_naive(payload.starts_at),
        timezone_name=payload.timezone,
        recurrence=payload.recurrence,
        status="scheduled",
    )
    db.add(activity)
    await db.flush()
    await grant_achievement(
        db,
        account_uid=account.uid,
        code="first_host",
        source_kind="activity_created",
        source_uid=activity.uid,
        context_room_uid=room.uid,
    )
    await db.commit()
    await db.refresh(activity)
    return await _single_activity_projection(db, activity, account.uid)


async def update_activity(
    db: AsyncSession,
    space_uid: UUID,
    activity_uid: UUID,
    viewer_uid: UUID | str,
    payload: ActivityUpdateRequest,
) -> dict:
    room = await _load_room(db, space_uid)
    account = await _require_active_member(db, room, viewer_uid)
    _, manager_role = await _manager_context(db, room, account.uid)
    activity = await db.get(SpaceActivity, activity_uid)
    if not activity or activity.room_uid != room.uid:
        raise HTTPException(status_code=404, detail={"error_type": "activity_not_found"})
    if activity.created_by_account_uid != account.uid and manager_role not in {"owner", "moderator"}:
        raise HTTPException(status_code=403, detail={"error_type": "activity_manage_required"})

    changes = payload.model_dump(exclude_unset=True)
    if changes.get("starts_at") is not None:
        changes["starts_at"] = _utc_naive(changes["starts_at"])
    if "timezone" in changes:
        changes["timezone_name"] = changes.pop("timezone")
    for field, value in changes.items():
        setattr(activity, field, value)
    activity.updated_at = datetime.utcnow()

    if changes.get("status") == "cancelled":
        round_result = await db.execute(
            select(ConversationRound).where(
                ConversationRound.activity_uid == activity.uid,
                ConversationRound.status == "open",
            )
        )
        now = datetime.utcnow()
        for round_item in round_result.scalars().all():
            round_item.status = "closed"
            round_item.closed_at = now
            round_item.updated_at = now

    await db.commit()
    await db.refresh(activity)
    return await _single_activity_projection(db, activity, account.uid)


async def set_activity_rsvp(
    db: AsyncSession,
    activity_uid: UUID,
    viewer_uid: UUID | str,
    payload: ActivityRSVPRequest,
) -> dict:
    activity = await db.get(SpaceActivity, activity_uid)
    if not activity:
        raise HTTPException(status_code=404, detail={"error_type": "activity_not_found"})
    room = await _load_room(db, activity.room_uid)
    account = await _require_active_member(db, room, viewer_uid)
    if activity.status == "cancelled":
        raise HTTPException(status_code=409, detail={"error_type": "activity_cancelled"})

    item = await db.get(ActivityRSVP, (activity.uid, account.uid))
    if not item:
        item = ActivityRSVP(activity_uid=activity.uid, account_uid=account.uid, status=payload.status)
        db.add(item)
    else:
        item.status = payload.status
        item.updated_at = datetime.utcnow()
    await db.commit()
    return await _single_activity_projection(db, activity, account.uid)


async def clear_activity_rsvp(
    db: AsyncSession,
    activity_uid: UUID,
    viewer_uid: UUID | str,
) -> dict:
    activity = await db.get(SpaceActivity, activity_uid)
    if not activity:
        raise HTTPException(status_code=404, detail={"error_type": "activity_not_found"})
    room = await _load_room(db, activity.room_uid)
    account = await _require_active_member(db, room, viewer_uid)
    await db.execute(
        delete(ActivityRSVP).where(
            ActivityRSVP.activity_uid == activity.uid,
            ActivityRSVP.account_uid == account.uid,
        )
    )
    await db.commit()
    return await _single_activity_projection(db, activity, account.uid)
