from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Account, AccountRelationship, Persona
from components.moderation.abuse_signals import detect_invitation_burst
from components.room.model import RoomBan
from components.space.capacity import assert_space_has_capacity, lock_space_admission_policy
from components.space.membership_service import _load_membership, _load_room, _manager_context
from components.space.model import SpaceInvitation, SpaceMembership, SpaceSettings
from components.space.service import (
    DEFAULT_MEMBER_LIMIT,
    _get_account,
    _sync_legacy_membership,
    build_space_projections,
)


INVITATION_TTL_DAYS = 7


async def _blocked_between(db: AsyncSession, left_uid: UUID, right_uid: UUID) -> bool:
    result = await db.execute(
        select(AccountRelationship.id)
        .where(
            AccountRelationship.relation_type == "block",
            or_(
                and_(
                    AccountRelationship.from_account_uid == left_uid,
                    AccountRelationship.to_account_uid == right_uid,
                ),
                and_(
                    AccountRelationship.from_account_uid == right_uid,
                    AccountRelationship.to_account_uid == left_uid,
                ),
            ),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def create_invitation(
    db: AsyncSession,
    space_uid: UUID,
    invitee_uid: UUID,
    viewer_uid: UUID | str,
) -> dict:
    room = await _load_room(db, space_uid)
    inviter, manager_role = await _manager_context(db, room, viewer_uid)
    if manager_role not in {"owner", "moderator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "space_invite_permission_required"},
        )

    invitee = await _get_account(db, invitee_uid)
    if invitee.uid == inviter.uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "cannot_invite_self"},
        )
    if await _blocked_between(db, inviter.uid, invitee.uid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "social_relationship_blocked"},
        )
    if invitee.legacy_user_uid and await RoomBan.is_user_banned(
        db, room.uid, invitee.legacy_user_uid
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "invitee_has_active_restriction"},
        )

    membership = await _load_membership(db, room.uid, invitee.uid)
    if membership and membership.status == "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "invitee_already_member"},
        )

    result = await db.execute(
        select(SpaceInvitation)
        .where(
            SpaceInvitation.room_uid == room.uid,
            SpaceInvitation.invitee_account_uid == invitee.uid,
        )
        .limit(1)
    )
    invitation = result.scalar_one_or_none()
    now = datetime.utcnow()
    expires_at = now + timedelta(days=INVITATION_TTL_DAYS)
    if invitation:
        invitation.inviter_account_uid = inviter.uid
        invitation.status = "pending"
        invitation.updated_at = now
        invitation.expires_at = expires_at
        invitation.responded_at = None
    else:
        invitation = SpaceInvitation(
            room_uid=room.uid,
            inviter_account_uid=inviter.uid,
            invitee_account_uid=invitee.uid,
            status="pending",
            expires_at=expires_at,
        )
        db.add(invitation)

    await db.commit()
    await db.refresh(invitation)
    try:
        await detect_invitation_burst(
            db,
            inviter_account_uid=inviter.uid,
        )
    except Exception:
        # Behavioral signal collection is advisory and must never make a valid
        # invitation fail.
        pass
    return {
        "uid": str(invitation.uid),
        "space_uid": str(room.uid),
        "invitee_account_uid": str(invitee.uid),
        "status": invitation.status,
        "expires_at": invitation.expires_at.isoformat(),
    }


async def list_invitations(
    db: AsyncSession,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    viewer = await _get_account(db, viewer_uid)
    now = datetime.utcnow()

    stale_result = await db.execute(
        select(SpaceInvitation).where(
            SpaceInvitation.invitee_account_uid == viewer.uid,
            SpaceInvitation.status == "pending",
            SpaceInvitation.expires_at <= now,
        )
    )
    stale = stale_result.scalars().all()
    for invitation in stale:
        invitation.status = "expired"
        invitation.updated_at = now
        invitation.responded_at = now
    if stale:
        await db.commit()

    base_filters = (
        SpaceInvitation.invitee_account_uid == viewer.uid,
        SpaceInvitation.status == "pending",
        SpaceInvitation.expires_at > now,
    )
    total_result = await db.execute(
        select(func.count(SpaceInvitation.uid)).where(*base_filters)
    )
    total = int(total_result.scalar_one() or 0)

    result = await db.execute(
        select(SpaceInvitation)
        .where(*base_filters)
        .order_by(SpaceInvitation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    invitations = result.scalars().all()
    if not invitations:
        return [], total

    room_uids = [invitation.room_uid for invitation in invitations]
    inviter_uids = [invitation.inviter_account_uid for invitation in invitations]
    from components.room.model import Room

    rooms_result = await db.execute(select(Room).where(Room.uid.in_(room_uids)))
    rooms = {room.uid: room for room in rooms_result.scalars().all()}
    persona_result = await db.execute(
        select(Persona).where(
            Persona.account_uid.in_(inviter_uids),
            Persona.is_primary.is_(True),
        )
    )
    personas = {persona.account_uid: persona for persona in persona_result.scalars().all()}

    items = []
    for invitation in invitations:
        room = rooms.get(invitation.room_uid)
        inviter_persona = personas.get(invitation.inviter_account_uid)
        items.append(
            {
                "uid": str(invitation.uid),
                "status": invitation.status,
                "created_at": invitation.created_at.isoformat() if invitation.created_at else None,
                "expires_at": invitation.expires_at.isoformat(),
                "space": {
                    "uid": str(invitation.room_uid),
                    "name": room.name if room else "Пространство",
                    "description": room.description if room else None,
                },
                "inviter": {
                    "account_uid": str(invitation.inviter_account_uid),
                    "handle": inviter_persona.handle if inviter_persona else None,
                    "display_name": inviter_persona.display_name if inviter_persona else None,
                    "avatar": inviter_persona.avatar if inviter_persona else None,
                },
            }
        )
    return items, total


async def respond_to_invitation(
    db: AsyncSession,
    invitation_uid: UUID,
    viewer_uid: UUID | str,
    action: str,
) -> dict:
    viewer = await _get_account(db, viewer_uid)
    result = await db.execute(
        select(SpaceInvitation)
        .where(
            SpaceInvitation.uid == invitation_uid,
            SpaceInvitation.invitee_account_uid == viewer.uid,
        )
        .with_for_update()
        .limit(1)
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "space_invitation_not_found"},
        )

    now = datetime.utcnow()
    if invitation.status != "pending" or invitation.expires_at <= now:
        if invitation.status == "pending":
            invitation.status = "expired"
            invitation.updated_at = now
            invitation.responded_at = now
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "space_invitation_not_active"},
        )

    if action == "decline":
        invitation.status = "declined"
        invitation.updated_at = now
        invitation.responded_at = now
        await db.commit()
        return {"uid": str(invitation.uid), "status": invitation.status}

    if action != "accept":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "invalid_invitation_action"},
        )

    room = await _load_room(db, invitation.room_uid)
    if await _blocked_between(db, invitation.inviter_account_uid, viewer.uid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "social_relationship_blocked"},
        )
    if viewer.legacy_user_uid and await RoomBan.is_user_banned(
        db, room.uid, viewer.legacy_user_uid
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "space_access_restricted"},
        )

    policy = await lock_space_admission_policy(
        db,
        room.uid,
        default_join_policy="open",
        default_member_limit=DEFAULT_MEMBER_LIMIT,
    )
    membership = await _load_membership(db, room.uid, viewer.uid)
    if not membership or membership.status != "active":
        await assert_space_has_capacity(
            db,
            room.uid,
            member_limit=policy.member_limit,
        )

    if membership:
        membership.status = "active"
        membership.role = "member"
        membership.updated_at = now
    else:
        membership = SpaceMembership(
            room_uid=room.uid,
            account_uid=viewer.uid,
            role="member",
            status="active",
        )
        db.add(membership)
    await _sync_legacy_membership(db, room.uid, viewer, role="member")

    invitation.status = "accepted"
    invitation.updated_at = now
    invitation.responded_at = now
    await db.commit()
    return {
        "uid": str(invitation.uid),
        "status": invitation.status,
        "space": (await build_space_projections(db, [room], viewer.uid))[0],
    }


async def revoke_invitation(
    db: AsyncSession,
    space_uid: UUID,
    invitee_uid: UUID,
    viewer_uid: UUID | str,
) -> None:
    room = await _load_room(db, space_uid)
    _, manager_role = await _manager_context(db, room, viewer_uid)
    if manager_role not in {"owner", "moderator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "space_invite_permission_required"},
        )

    result = await db.execute(
        select(SpaceInvitation)
        .where(
            SpaceInvitation.room_uid == room.uid,
            SpaceInvitation.invitee_account_uid == invitee_uid,
            SpaceInvitation.status == "pending",
        )
        .limit(1)
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        return
    now = datetime.utcnow()
    invitation.status = "revoked"
    invitation.updated_at = now
    invitation.responded_at = now
    await db.commit()
