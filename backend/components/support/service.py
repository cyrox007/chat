from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Persona
from components.room.model import Room
from components.social.privacy import can_view_profile
from components.space.membership_service import _load_room, _manager_context, _require_active_member
from components.space.service import _get_account, get_space
from components.support.model import (
    CosmeticEntitlement,
    CreatorSupportProfile,
    GiftDefinition,
    SpaceSupportSettings,
    SupportLedgerEntry,
)
from components.support.schemas import GiftSendRequest, SupportSettingsUpdateRequest


MAX_GIFTS_PER_DAY = 20


def _gift_projection(item: GiftDefinition) -> dict:
    return {
        "code": item.code,
        "name": item.name,
        "description": item.description,
        "icon": item.icon,
        "target_scope": item.target_scope,
    }


def _settings_projection(enabled: bool, note: str | None) -> dict:
    return {"enabled": bool(enabled), "note": note}


async def _primary_persona(db: AsyncSession, account_uid: UUID) -> Persona | None:
    result = await db.execute(
        select(Persona)
        .where(Persona.account_uid == account_uid, Persona.is_primary.is_(True))
        .order_by(Persona.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _gift_definition(
    db: AsyncSession,
    code: str,
    target_kind: str,
) -> GiftDefinition:
    gift = await db.get(GiftDefinition, code)
    if not gift or not gift.active or gift.target_scope not in {target_kind, "both"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "gift_not_available"},
        )
    return gift


async def _enforce_sender_limit(db: AsyncSession, sender_account_uid: UUID) -> None:
    since = datetime.utcnow() - timedelta(days=1)
    result = await db.execute(
        select(func.count(SupportLedgerEntry.uid)).where(
            SupportLedgerEntry.sender_account_uid == sender_account_uid,
            SupportLedgerEntry.created_at >= since,
        )
    )
    if int(result.scalar_one() or 0) >= MAX_GIFTS_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error_type": "gift_daily_limit_reached"},
        )


async def list_gift_catalog(db: AsyncSession, target_kind: str) -> list[dict]:
    if target_kind not in {"persona", "space"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "invalid_gift_target"},
        )
    result = await db.execute(
        select(GiftDefinition)
        .where(
            GiftDefinition.active.is_(True),
            GiftDefinition.target_scope.in_([target_kind, "both"]),
        )
        .order_by(GiftDefinition.code.asc())
    )
    return [_gift_projection(item) for item in result.scalars().all()]


async def get_own_support_profile(db: AsyncSession, viewer_uid: UUID | str) -> dict:
    account = await _get_account(db, viewer_uid)
    item = await db.get(CreatorSupportProfile, account.uid)
    if not item:
        return _settings_projection(False, None)
    return _settings_projection(item.enabled, item.note)


async def update_own_support_profile(
    db: AsyncSession,
    viewer_uid: UUID | str,
    payload: SupportSettingsUpdateRequest,
) -> dict:
    account = await _get_account(db, viewer_uid)
    item = await db.get(CreatorSupportProfile, account.uid)
    if not item:
        item = CreatorSupportProfile(account_uid=account.uid, enabled=False)
        db.add(item)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    return _settings_projection(item.enabled, item.note)


async def get_space_support_settings(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
) -> dict:
    await get_space(db, space_uid, viewer_uid)
    item = await db.get(SpaceSupportSettings, space_uid)
    if not item:
        return _settings_projection(False, None)
    return _settings_projection(item.enabled, item.note)


async def update_space_support_settings(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    payload: SupportSettingsUpdateRequest,
) -> dict:
    room = await _load_room(db, space_uid)
    _, manager_role = await _manager_context(db, room, viewer_uid)
    if manager_role not in {"owner", "moderator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "space_manage_support_required"},
        )
    item = await db.get(SpaceSupportSettings, room.uid)
    if not item:
        item = SpaceSupportSettings(room_uid=room.uid, enabled=False)
        db.add(item)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    return _settings_projection(item.enabled, item.note)


async def _sender_label(db: AsyncSession, account_uid: UUID) -> str | None:
    persona = await _primary_persona(db, account_uid)
    return persona.display_name if persona else None


async def _public_shelf(
    db: AsyncSession,
    *,
    persona_uid: UUID | None = None,
    room_uid: UUID | None = None,
) -> list[dict]:
    filters = []
    if persona_uid:
        filters.append(CosmeticEntitlement.persona_uid == persona_uid)
    elif room_uid:
        filters.append(CosmeticEntitlement.room_uid == room_uid)
    else:
        return []

    result = await db.execute(
        select(GiftDefinition, func.count(CosmeticEntitlement.uid))
        .join(CosmeticEntitlement, CosmeticEntitlement.gift_code == GiftDefinition.code)
        .where(*filters, GiftDefinition.active.is_(True))
        .group_by(
            GiftDefinition.code,
            GiftDefinition.name,
            GiftDefinition.description,
            GiftDefinition.icon,
            GiftDefinition.target_scope,
            GiftDefinition.active,
            GiftDefinition.created_at,
        )
        .order_by(func.count(CosmeticEntitlement.uid).desc(), GiftDefinition.code.asc())
    )
    return [
        {"gift": _gift_projection(gift), "count": int(count)}
        for gift, count in result.all()
    ]


async def persona_support_shelf(
    db: AsyncSession,
    persona_uid: UUID,
    viewer_uid: UUID | str,
) -> dict:
    persona = await db.get(Persona, persona_uid)
    if not persona or not persona.is_primary:
        raise HTTPException(status_code=404, detail={"error_type": "persona_not_found"})
    if not await can_view_profile(db, viewer_uid, persona.account_uid):
        raise HTTPException(status_code=404, detail={"error_type": "persona_not_found"})
    profile = await db.get(CreatorSupportProfile, persona.account_uid)
    return {
        "settings": _settings_projection(profile.enabled, profile.note) if profile else _settings_projection(False, None),
        "items": await _public_shelf(db, persona_uid=persona.uid),
    }


async def space_support_shelf(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
) -> dict:
    await get_space(db, space_uid, viewer_uid)
    settings = await db.get(SpaceSupportSettings, space_uid)
    return {
        "settings": _settings_projection(settings.enabled, settings.note) if settings else _settings_projection(False, None),
        "items": await _public_shelf(db, room_uid=space_uid),
    }


async def send_persona_gift(
    db: AsyncSession,
    persona_uid: UUID,
    viewer_uid: UUID | str,
    payload: GiftSendRequest,
) -> dict:
    sender = await _get_account(db, viewer_uid)
    target = await db.get(Persona, persona_uid)
    if not target or not target.is_primary:
        raise HTTPException(status_code=404, detail={"error_type": "persona_not_found"})
    if sender.uid == target.account_uid:
        raise HTTPException(status_code=409, detail={"error_type": "self_gift_not_allowed"})
    if not await can_view_profile(db, sender.uid, target.account_uid):
        raise HTTPException(status_code=404, detail={"error_type": "persona_not_found"})

    support_profile = await db.get(CreatorSupportProfile, target.account_uid)
    if not support_profile or not support_profile.enabled:
        raise HTTPException(status_code=409, detail={"error_type": "support_not_enabled"})

    gift = await _gift_definition(db, payload.gift_code, "persona")
    await _enforce_sender_limit(db, sender.uid)

    entry = SupportLedgerEntry(
        sender_account_uid=sender.uid,
        target_kind="persona",
        target_persona_uid=target.uid,
        target_label=target.display_name,
        sender_label=await _sender_label(db, sender.uid),
        gift_code=gift.code,
        message=payload.message,
    )
    db.add(entry)
    await db.flush()
    db.add(
        CosmeticEntitlement(
            source_ledger_uid=entry.uid,
            persona_uid=target.uid,
            gift_code=gift.code,
        )
    )
    await db.commit()
    await db.refresh(entry)
    return {
        "uid": str(entry.uid),
        "gift": _gift_projection(gift),
        "target_kind": "persona",
        "target_label": entry.target_label,
        "message": entry.message,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


async def send_space_gift(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    payload: GiftSendRequest,
) -> dict:
    room = await _load_room(db, space_uid)
    sender = await _require_active_member(db, room, viewer_uid)
    if room.owner_uid == sender.legacy_user_uid:
        raise HTTPException(status_code=409, detail={"error_type": "self_space_gift_not_allowed"})

    settings = await db.get(SpaceSupportSettings, room.uid)
    if not settings or not settings.enabled:
        raise HTTPException(status_code=409, detail={"error_type": "support_not_enabled"})

    gift = await _gift_definition(db, payload.gift_code, "space")
    await _enforce_sender_limit(db, sender.uid)

    entry = SupportLedgerEntry(
        sender_account_uid=sender.uid,
        target_kind="space",
        target_room_uid=room.uid,
        target_label=room.name,
        sender_label=await _sender_label(db, sender.uid),
        gift_code=gift.code,
        message=payload.message,
    )
    db.add(entry)
    await db.flush()
    db.add(
        CosmeticEntitlement(
            source_ledger_uid=entry.uid,
            room_uid=room.uid,
            gift_code=gift.code,
        )
    )
    await db.commit()
    await db.refresh(entry)
    return {
        "uid": str(entry.uid),
        "gift": _gift_projection(gift),
        "target_kind": "space",
        "target_label": entry.target_label,
        "message": entry.message,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


async def _ledger_history(
    db: AsyncSession,
    *,
    persona_uid: UUID | None = None,
    room_uid: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    filters = []
    if persona_uid:
        filters.append(SupportLedgerEntry.target_persona_uid == persona_uid)
    elif room_uid:
        filters.append(SupportLedgerEntry.target_room_uid == room_uid)
    else:
        return [], 0

    total = int((await db.execute(select(func.count(SupportLedgerEntry.uid)).where(*filters))).scalar_one() or 0)
    result = await db.execute(
        select(SupportLedgerEntry, GiftDefinition)
        .join(GiftDefinition, GiftDefinition.code == SupportLedgerEntry.gift_code)
        .where(*filters)
        .order_by(SupportLedgerEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [
        {
            "uid": str(entry.uid),
            "gift": _gift_projection(gift),
            "sender_label": entry.sender_label,
            "message": entry.message,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
        for entry, gift in result.all()
    ]
    return items, total


async def own_received_support(
    db: AsyncSession,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    account = await _get_account(db, viewer_uid)
    persona = await _primary_persona(db, account.uid)
    if not persona:
        return [], 0
    return await _ledger_history(db, persona_uid=persona.uid, limit=limit, offset=offset)


async def space_received_support(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    room = await _load_room(db, space_uid)
    _, manager_role = await _manager_context(db, room, viewer_uid)
    if manager_role not in {"owner", "moderator"}:
        raise HTTPException(status_code=403, detail={"error_type": "space_manage_support_required"})
    return await _ledger_history(db, room_uid=room.uid, limit=limit, offset=offset)
