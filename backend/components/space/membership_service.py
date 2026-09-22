from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Account, Persona
from components.realtime import RealtimeUnavailable, realtime_service
from components.room.model import Room, RoomBan, RoomMember
from components.space.capacity import assert_space_has_capacity, lock_space_admission_policy
from components.space.model import SpaceMembership, SpaceSettings
from components.space.service import (
    DEFAULT_MEMBER_LIMIT,
    _get_account,
    _sync_legacy_membership,
)


async def _load_room(db: AsyncSession, space_uid: UUID) -> Room:
    result = await db.execute(
        select(Room)
        .where(
            Room.uid == space_uid,
            Room.is_active.is_(True),
        )
        .limit(1)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "space_not_found"},
        )
    return room


async def _load_membership(
    db: AsyncSession,
    space_uid: UUID,
    account_uid: UUID,
) -> SpaceMembership | None:
    result = await db.execute(
        select(SpaceMembership)
        .where(
            SpaceMembership.room_uid == space_uid,
            SpaceMembership.account_uid == account_uid,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _manager_context(
    db: AsyncSession,
    room: Room,
    viewer_uid: UUID | str,
) -> tuple[Account, str | None]:
    account = await _get_account(db, viewer_uid)
    membership = await _load_membership(db, room.uid, account.uid)

    if room.owner_uid == account.legacy_user_uid:
        return account, "owner"
    if membership and membership.status == "active" and membership.role in {"owner", "moderator"}:
        return account, membership.role
    return account, None


async def _require_active_member(
    db: AsyncSession,
    room: Room,
    viewer_uid: UUID | str,
) -> Account:
    account = await _get_account(db, viewer_uid)
    if room.owner_uid == account.legacy_user_uid:
        return account

    membership = await _load_membership(db, room.uid, account.uid)
    if membership and membership.status == "active":
        return account

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error_type": "space_membership_required"},
    )


async def list_members_page(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    membership_status: str = "active",
    role: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    room = await _load_room(db, space_uid)
    viewer_account, manager_role = await _manager_context(db, room, viewer_uid)

    if membership_status == "active":
        await _require_active_member(db, room, viewer_account.uid)
    elif membership_status == "pending":
        if manager_role not in {"owner", "moderator"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_type": "space_manage_members_required"},
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "invalid_membership_status"},
        )

    filters = [
        SpaceMembership.room_uid == room.uid,
        SpaceMembership.status == membership_status,
    ]
    if role:
        filters.append(SpaceMembership.role == role)

    total_result = await db.execute(
        select(func.count(SpaceMembership.uid)).where(*filters)
    )
    total = int(total_result.scalar_one() or 0)

    role_order = case(
        (SpaceMembership.role == "owner", 0),
        (SpaceMembership.role == "moderator", 1),
        else_=2,
    )
    result = await db.execute(
        select(SpaceMembership, Persona)
        .outerjoin(
            Persona,
            (Persona.account_uid == SpaceMembership.account_uid)
            & Persona.is_primary.is_(True),
        )
        .where(*filters)
        .order_by(role_order, SpaceMembership.joined_at.asc())
        .limit(limit)
        .offset(offset)
    )

    items: list[dict] = []
    for membership, persona in result.all():
        items.append(
            {
                "account_uid": str(membership.account_uid),
                "role": membership.role,
                "status": membership.status,
                "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
                "persona": {
                    "uid": str(membership.account_uid),
                    "persona_uid": str(persona.uid) if persona else None,
                    "handle": persona.handle if persona else None,
                    "display_name": persona.display_name if persona else None,
                    "avatar": persona.avatar if persona else None,
                    "social_intent": persona.social_intent if persona else None,
                },
            }
        )
    return items, total


async def _remove_legacy_membership(
    db: AsyncSession,
    room_uid: UUID,
    legacy_user_uid: UUID | None,
) -> None:
    if not legacy_user_uid:
        return
    await db.execute(
        delete(RoomMember).where(
            RoomMember.room_uid == room_uid,
            RoomMember.user_uid == legacy_user_uid,
        )
    )


async def manage_membership(
    db: AsyncSession,
    space_uid: UUID,
    target_account_uid: UUID,
    viewer_uid: UUID | str,
    action: str,
) -> dict:
    room = await _load_room(db, space_uid)
    viewer_account, manager_role = await _manager_context(db, room, viewer_uid)
    if manager_role not in {"owner", "moderator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "space_manage_members_required"},
        )

    target_account = await db.get(Account, target_account_uid)
    target_membership = await _load_membership(db, room.uid, target_account_uid)
    if not target_account or not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "member_not_found"},
        )

    if target_account.uid == viewer_account.uid or target_membership.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "cannot_manage_space_owner"},
        )

    if manager_role == "moderator" and target_membership.role == "moderator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "moderator_cannot_manage_moderator"},
        )

    if action == "approve":
        policy = await lock_space_admission_policy(
            db,
            room.uid,
            default_join_policy="open",
            default_member_limit=DEFAULT_MEMBER_LIMIT,
        )
        locked_membership_result = await db.execute(
            select(SpaceMembership)
            .where(SpaceMembership.uid == target_membership.uid)
            .with_for_update()
        )
        target_membership = locked_membership_result.scalar_one_or_none()
        if not target_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "member_not_found"},
            )
        if target_account.uid == viewer_account.uid or target_membership.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_type": "cannot_manage_space_owner"},
            )
        if manager_role == "moderator" and target_membership.role == "moderator":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_type": "moderator_cannot_manage_moderator"},
            )
        if target_membership.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_type": "membership_not_pending"},
            )

        await assert_space_has_capacity(
            db,
            room.uid,
            member_limit=policy.member_limit,
        )

        if target_account.legacy_user_uid and await RoomBan.is_user_banned(
            db, room.uid, target_account.legacy_user_uid
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_type": "member_has_active_restriction"},
            )

        target_membership.status = "active"
        target_membership.role = "member"
        target_membership.updated_at = datetime.utcnow()
        await _sync_legacy_membership(db, room.uid, target_account, role="member")
        await db.commit()

    elif action == "reject":
        if target_membership.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_type": "membership_not_pending"},
            )
        target_membership.status = "rejected"
        target_membership.role = "member"
        target_membership.updated_at = datetime.utcnow()
        await db.commit()

    elif action == "remove":
        if target_membership.status != "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_type": "membership_not_active"},
            )
        target_membership.status = "removed"
        target_membership.role = "member"
        target_membership.updated_at = datetime.utcnow()
        await _remove_legacy_membership(db, room.uid, target_account.legacy_user_uid)
        await db.commit()

        try:
            await realtime_service.publish(
                {
                    "kind": "room_control",
                    "action": "disconnect_user",
                    "room_uid": str(room.uid),
                    "user_uid": str(target_account.uid),
                    "reason": "Membership in this space was removed",
                }
            )
        except RealtimeUnavailable:
            # Membership is authoritative in PostgreSQL; a later ticket request is
            # rejected even if the best-effort realtime disconnect is unavailable.
            pass
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "invalid_membership_action"},
        )

    return {
        "account_uid": str(target_membership.account_uid),
        "role": target_membership.role,
        "status": target_membership.status,
    }
