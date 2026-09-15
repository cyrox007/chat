from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Persona
from components.space.content_schemas import (
    SpaceEventCreateRequest,
    SpaceEventUpdateRequest,
    SpaceRuleCreateRequest,
    SpaceRuleUpdateRequest,
)
from components.space.membership_service import (
    _load_room,
    _manager_context,
    _require_active_member,
)
from components.space.model import SpaceEvent, SpaceHistoryEntry, SpaceRule
from components.space.service import get_space


async def _require_manager(db: AsyncSession, space_uid: UUID, viewer_uid: UUID | str):
    room = await _load_room(db, space_uid)
    account, role = await _manager_context(db, room, viewer_uid)
    if role not in {"owner", "moderator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "space_content_manage_required"},
        )
    return room, account, role


async def _record_history(
    db: AsyncSession,
    room_uid: UUID,
    actor_uid: UUID | None,
    event_type: str,
    summary: str,
) -> None:
    db.add(
        SpaceHistoryEntry(
            room_uid=room_uid,
            actor_account_uid=actor_uid,
            event_type=event_type,
            summary=summary[:255],
        )
    )


def _rule_projection(rule: SpaceRule) -> dict:
    return {
        "uid": str(rule.uid),
        "space_uid": str(rule.room_uid),
        "title": rule.title,
        "body": rule.body,
        "position": rule.position,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


def _event_projection(event: SpaceEvent) -> dict:
    return {
        "uid": str(event.uid),
        "space_uid": str(event.room_uid),
        "title": event.title,
        "description": event.description,
        "starts_at": event.starts_at.isoformat() if event.starts_at else None,
        "ends_at": event.ends_at.isoformat() if event.ends_at else None,
        "status": event.status,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "updated_at": event.updated_at.isoformat() if event.updated_at else None,
    }


async def list_rules(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
) -> list[dict]:
    await get_space(db, space_uid, viewer_uid)
    result = await db.execute(
        select(SpaceRule)
        .where(SpaceRule.room_uid == space_uid)
        .order_by(SpaceRule.position.asc(), SpaceRule.created_at.asc())
    )
    return [_rule_projection(rule) for rule in result.scalars().all()]


async def create_rule(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    payload: SpaceRuleCreateRequest,
) -> dict:
    room, account, _ = await _require_manager(db, space_uid, viewer_uid)
    rule = SpaceRule(
        room_uid=room.uid,
        created_by_account_uid=account.uid,
        title=payload.title,
        body=payload.body,
        position=payload.position,
    )
    db.add(rule)
    await db.flush()
    await _record_history(db, room.uid, account.uid, "rule_created", f"Добавлено правило «{rule.title}»")
    await db.commit()
    await db.refresh(rule)
    return _rule_projection(rule)


async def update_rule(
    db: AsyncSession,
    space_uid: UUID,
    rule_uid: UUID,
    viewer_uid: UUID | str,
    payload: SpaceRuleUpdateRequest,
) -> dict:
    room, account, _ = await _require_manager(db, space_uid, viewer_uid)
    rule = await db.get(SpaceRule, rule_uid)
    if not rule or rule.room_uid != room.uid:
        raise HTTPException(status_code=404, detail={"error_type": "space_rule_not_found"})

    changes = payload.model_dump(exclude_unset=True)
    for field in ("title", "body", "position"):
        if field in changes:
            setattr(rule, field, changes[field])
    rule.updated_at = datetime.utcnow()
    await _record_history(db, room.uid, account.uid, "rule_updated", f"Обновлено правило «{rule.title}»")
    await db.commit()
    await db.refresh(rule)
    return _rule_projection(rule)


async def delete_rule(
    db: AsyncSession,
    space_uid: UUID,
    rule_uid: UUID,
    viewer_uid: UUID | str,
) -> None:
    room, account, _ = await _require_manager(db, space_uid, viewer_uid)
    rule = await db.get(SpaceRule, rule_uid)
    if not rule or rule.room_uid != room.uid:
        raise HTTPException(status_code=404, detail={"error_type": "space_rule_not_found"})
    title = rule.title
    await db.delete(rule)
    await _record_history(db, room.uid, account.uid, "rule_deleted", f"Удалено правило «{title}»")
    await db.commit()


async def list_events(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    await get_space(db, space_uid, viewer_uid)
    total_result = await db.execute(select(func.count(SpaceEvent.uid)).where(SpaceEvent.room_uid == space_uid))
    total = int(total_result.scalar_one() or 0)
    result = await db.execute(
        select(SpaceEvent)
        .where(SpaceEvent.room_uid == space_uid)
        .order_by(SpaceEvent.starts_at.asc(), SpaceEvent.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return [_event_projection(event) for event in result.scalars().all()], total


async def create_event(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    payload: SpaceEventCreateRequest,
) -> dict:
    room, account, _ = await _require_manager(db, space_uid, viewer_uid)
    event = SpaceEvent(
        room_uid=room.uid,
        created_by_account_uid=account.uid,
        title=payload.title,
        description=payload.description,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status="scheduled",
    )
    db.add(event)
    await db.flush()
    await _record_history(db, room.uid, account.uid, "event_created", f"Создано событие «{event.title}»")
    await db.commit()
    await db.refresh(event)
    return _event_projection(event)


async def update_event(
    db: AsyncSession,
    space_uid: UUID,
    event_uid: UUID,
    viewer_uid: UUID | str,
    payload: SpaceEventUpdateRequest,
) -> dict:
    room, account, _ = await _require_manager(db, space_uid, viewer_uid)
    event = await db.get(SpaceEvent, event_uid)
    if not event or event.room_uid != room.uid:
        raise HTTPException(status_code=404, detail={"error_type": "space_event_not_found"})

    changes = payload.model_dump(exclude_unset=True)
    next_starts_at = changes.get("starts_at", event.starts_at)
    next_ends_at = changes.get("ends_at", event.ends_at)
    if next_ends_at is not None and next_ends_at <= next_starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "invalid_event_time_range"},
        )

    previous_status = event.status
    for field in ("title", "description", "starts_at", "ends_at", "status"):
        if field in changes:
            setattr(event, field, changes[field])
    event.updated_at = datetime.utcnow()
    event_type = "event_cancelled" if previous_status != "cancelled" and event.status == "cancelled" else "event_updated"
    summary = f"Отменено событие «{event.title}»" if event_type == "event_cancelled" else f"Обновлено событие «{event.title}»"
    await _record_history(db, room.uid, account.uid, event_type, summary)
    await db.commit()
    await db.refresh(event)
    return _event_projection(event)


async def delete_event(
    db: AsyncSession,
    space_uid: UUID,
    event_uid: UUID,
    viewer_uid: UUID | str,
) -> None:
    room, account, _ = await _require_manager(db, space_uid, viewer_uid)
    event = await db.get(SpaceEvent, event_uid)
    if not event or event.room_uid != room.uid:
        raise HTTPException(status_code=404, detail={"error_type": "space_event_not_found"})
    title = event.title
    await db.delete(event)
    await _record_history(db, room.uid, account.uid, "event_deleted", f"Удалено событие «{title}»")
    await db.commit()


async def list_history(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    room = await _load_room(db, space_uid)
    await _require_active_member(db, room, viewer_uid)

    total_result = await db.execute(
        select(func.count(SpaceHistoryEntry.uid)).where(SpaceHistoryEntry.room_uid == room.uid)
    )
    total = int(total_result.scalar_one() or 0)
    result = await db.execute(
        select(SpaceHistoryEntry, Persona)
        .outerjoin(
            Persona,
            (Persona.account_uid == SpaceHistoryEntry.actor_account_uid) & Persona.is_primary.is_(True),
        )
        .where(SpaceHistoryEntry.room_uid == room.uid)
        .order_by(SpaceHistoryEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = []
    for entry, persona in result.all():
        items.append(
            {
                "uid": str(entry.uid),
                "event_type": entry.event_type,
                "summary": entry.summary,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "actor": {
                    "account_uid": str(entry.actor_account_uid),
                    "handle": persona.handle if persona else None,
                    "display_name": persona.display_name if persona else None,
                    "avatar": persona.avatar if persona else None,
                }
                if entry.actor_account_uid
                else None,
            }
        )
    return items, total
