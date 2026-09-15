from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Account, Persona
from components.message.model import Message
from components.moderation.model import ModerationAction, ModerationAppeal, ModerationReport
from components.moderation.schemas import (
    ModerationActionCreateRequest,
    ModerationAppealCreateRequest,
    ModerationAppealResolveRequest,
    ModerationReportCreateRequest,
)
from components.realtime import RealtimeUnavailable, realtime_service
from components.room.model import RoomBan
from components.space.membership_service import (
    _load_membership,
    _load_room,
    _manager_context,
    _require_active_member,
)
from components.space.service import _get_account


async def _persona_map(db: AsyncSession, account_uids: set[UUID]) -> dict[UUID, Persona]:
    if not account_uids:
        return {}
    result = await db.execute(
        select(Persona).where(
            Persona.account_uid.in_(list(account_uids)),
            Persona.is_primary.is_(True),
        )
    )
    return {persona.account_uid: persona for persona in result.scalars().all()}


def _persona_projection(account_uid: UUID | None, personas: dict[UUID, Persona]) -> dict | None:
    if not account_uid:
        return None
    persona = personas.get(account_uid)
    return {
        "account_uid": str(account_uid),
        "handle": persona.handle if persona else None,
        "display_name": persona.display_name if persona else None,
        "avatar": persona.avatar if persona else None,
    }


def _effective_action_status(action: ModerationAction) -> str:
    if action.status == "active" and action.expires_at and action.expires_at <= datetime.utcnow():
        return "expired"
    return action.status


async def _require_manager(db: AsyncSession, space_uid: UUID, viewer_uid: UUID | str):
    room = await _load_room(db, space_uid)
    account, role = await _manager_context(db, room, viewer_uid)
    if role not in {"owner", "moderator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "space_moderation_required"},
        )
    return room, account, role


async def _target_context(
    db: AsyncSession,
    room_uid: UUID,
    target_uid: UUID,
) -> tuple[Account, object]:
    target = await db.get(Account, target_uid)
    membership = await _load_membership(db, room_uid, target_uid)
    if not target or target.status != "active" or not membership or membership.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "moderation_target_not_found"},
        )
    return target, membership


async def create_report(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    payload: ModerationReportCreateRequest,
) -> dict:
    room = await _load_room(db, space_uid)
    reporter = await _require_active_member(db, room, viewer_uid)
    target_uid = payload.target_account_uid

    if payload.message_uid:
        message = await db.get(Message, payload.message_uid)
        if not message or message.room_uid != room.uid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "report_message_not_found"},
            )
        account_result = await db.execute(
            select(Account).where(Account.legacy_user_uid == message.author_uid).limit(1)
        )
        message_author = account_result.scalar_one_or_none()
        if not message_author:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_type": "message_identity_bridge_missing"},
            )
        if target_uid and target_uid != message_author.uid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error_type": "report_target_mismatch"},
            )
        target_uid = message_author.uid

    if not target_uid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "report_target_required"},
        )
    if target_uid == reporter.uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "cannot_report_self"},
        )

    await _target_context(db, room.uid, target_uid)
    report = ModerationReport(
        room_uid=room.uid,
        reporter_account_uid=reporter.uid,
        target_account_uid=target_uid,
        message_uid=payload.message_uid,
        category=payload.category,
        description=payload.description,
        status="open",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return {
        "uid": str(report.uid),
        "space_uid": str(report.room_uid),
        "status": report.status,
        "category": report.category,
        "created_at": report.created_at.isoformat(),
    }


async def list_my_reports(
    db: AsyncSession,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    viewer = await _get_account(db, viewer_uid)
    filters = (ModerationReport.reporter_account_uid == viewer.uid,)
    total = int((await db.execute(select(func.count(ModerationReport.uid)).where(*filters))).scalar_one() or 0)
    result = await db.execute(
        select(ModerationReport)
        .where(*filters)
        .order_by(ModerationReport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    reports = result.scalars().all()
    personas = await _persona_map(db, {item.target_account_uid for item in reports if item.target_account_uid})
    return [
        {
            "uid": str(item.uid),
            "space_uid": str(item.room_uid),
            "category": item.category,
            "description": item.description,
            "status": item.status,
            "message_uid": str(item.message_uid) if item.message_uid else None,
            "target": _persona_projection(item.target_account_uid, personas),
            "created_at": item.created_at.isoformat(),
            "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
        }
        for item in reports
    ], total


async def list_space_reports(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    report_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    room, _, _ = await _require_manager(db, space_uid, viewer_uid)
    filters = [ModerationReport.room_uid == room.uid]
    if report_status:
        filters.append(ModerationReport.status == report_status)
    total = int((await db.execute(select(func.count(ModerationReport.uid)).where(*filters))).scalar_one() or 0)
    result = await db.execute(
        select(ModerationReport)
        .where(*filters)
        .order_by(ModerationReport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    reports = result.scalars().all()
    account_uids = {
        uid
        for item in reports
        for uid in (item.reporter_account_uid, item.target_account_uid)
        if uid
    }
    personas = await _persona_map(db, account_uids)
    return [
        {
            "uid": str(item.uid),
            "space_uid": str(item.room_uid),
            "category": item.category,
            "description": item.description,
            "status": item.status,
            "message_uid": str(item.message_uid) if item.message_uid else None,
            "reporter": _persona_projection(item.reporter_account_uid, personas),
            "target": _persona_projection(item.target_account_uid, personas),
            "created_at": item.created_at.isoformat(),
            "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
        }
        for item in reports
    ], total


async def update_report_status(
    db: AsyncSession,
    space_uid: UUID,
    report_uid: UUID,
    viewer_uid: UUID | str,
    next_status: str,
) -> dict:
    room, _, _ = await _require_manager(db, space_uid, viewer_uid)
    report = await db.get(ModerationReport, report_uid)
    if not report or report.room_uid != room.uid:
        raise HTTPException(status_code=404, detail={"error_type": "moderation_report_not_found"})
    if report.status in {"resolved", "dismissed"}:
        raise HTTPException(status_code=409, detail={"error_type": "moderation_report_closed"})
    report.status = next_status
    report.updated_at = datetime.utcnow()
    if next_status == "dismissed":
        report.resolved_at = datetime.utcnow()
    await db.commit()
    return {"uid": str(report.uid), "status": report.status}


async def create_action(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    payload: ModerationActionCreateRequest,
) -> dict:
    room, moderator, manager_role = await _require_manager(db, space_uid, viewer_uid)
    target, target_membership = await _target_context(db, room.uid, payload.target_account_uid)
    if target.uid == moderator.uid or target_membership.role == "owner":
        raise HTTPException(status_code=409, detail={"error_type": "cannot_moderate_space_owner"})
    if manager_role == "moderator" and target_membership.role == "moderator":
        raise HTTPException(status_code=403, detail={"error_type": "moderator_cannot_manage_moderator"})

    report = None
    if payload.report_uid:
        report = await db.get(ModerationReport, payload.report_uid)
        if not report or report.room_uid != room.uid:
            raise HTTPException(status_code=404, detail={"error_type": "moderation_report_not_found"})
        if report.target_account_uid and report.target_account_uid != target.uid:
            raise HTTPException(status_code=422, detail={"error_type": "moderation_report_target_mismatch"})

    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=payload.duration_minutes) if payload.duration_minutes else None
    legacy_ban = None
    if payload.action_type == "restrict":
        if not target.legacy_user_uid or not moderator.legacy_user_uid:
            raise HTTPException(status_code=409, detail={"error_type": "identity_bridge_missing"})
        await db.execute(
            update(RoomBan)
            .where(
                RoomBan.room_uid == room.uid,
                RoomBan.user_uid == target.legacy_user_uid,
                RoomBan.is_active.is_(True),
            )
            .values(is_active=False)
        )
        legacy_ban = RoomBan(
            room_uid=room.uid,
            user_uid=target.legacy_user_uid,
            banned_by_uid=moderator.legacy_user_uid,
            reason=payload.reason,
            created_at=now,
            expires_at=expires_at,
            is_active=True,
        )
        db.add(legacy_ban)
        await db.flush()

    action = ModerationAction(
        room_uid=room.uid,
        report_uid=report.uid if report else None,
        moderator_account_uid=moderator.uid,
        target_account_uid=target.uid,
        action_type=payload.action_type,
        reason=payload.reason,
        status="active",
        starts_at=now,
        expires_at=expires_at,
        legacy_room_ban_id=legacy_ban.id if legacy_ban else None,
    )
    db.add(action)
    if report:
        report.status = "resolved"
        report.resolved_at = now
        report.updated_at = now
    await db.commit()
    await db.refresh(action)

    if payload.action_type == "restrict":
        try:
            await realtime_service.publish(
                {
                    "kind": "room_control",
                    "action": "disconnect_user",
                    "room_uid": str(room.uid),
                    "user_uid": str(target.uid),
                    "reason": "Access to this space was restricted",
                }
            )
        except RealtimeUnavailable:
            pass

    return {
        "uid": str(action.uid),
        "space_uid": str(action.room_uid),
        "target_account_uid": str(target.uid),
        "action_type": action.action_type,
        "reason": action.reason,
        "status": _effective_action_status(action),
        "starts_at": action.starts_at.isoformat(),
        "expires_at": action.expires_at.isoformat() if action.expires_at else None,
        "appealable": True,
    }


async def list_my_actions(
    db: AsyncSession,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    viewer = await _get_account(db, viewer_uid)
    filters = (ModerationAction.target_account_uid == viewer.uid,)
    total = int((await db.execute(select(func.count(ModerationAction.uid)).where(*filters))).scalar_one() or 0)
    result = await db.execute(
        select(ModerationAction)
        .where(*filters)
        .order_by(ModerationAction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    actions = result.scalars().all()
    return [
        {
            "uid": str(item.uid),
            "space_uid": str(item.room_uid),
            "action_type": item.action_type,
            "reason": item.reason,
            "status": _effective_action_status(item),
            "starts_at": item.starts_at.isoformat(),
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            "revoked_at": item.revoked_at.isoformat() if item.revoked_at else None,
        }
        for item in actions
    ], total


async def list_space_actions(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    room, _, _ = await _require_manager(db, space_uid, viewer_uid)
    filters = (ModerationAction.room_uid == room.uid,)
    total = int((await db.execute(select(func.count(ModerationAction.uid)).where(*filters))).scalar_one() or 0)
    result = await db.execute(
        select(ModerationAction)
        .where(*filters)
        .order_by(ModerationAction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    actions = result.scalars().all()
    account_uids = {
        uid
        for item in actions
        for uid in (item.moderator_account_uid, item.target_account_uid)
        if uid
    }
    personas = await _persona_map(db, account_uids)
    return [
        {
            "uid": str(item.uid),
            "space_uid": str(item.room_uid),
            "report_uid": str(item.report_uid) if item.report_uid else None,
            "moderator": _persona_projection(item.moderator_account_uid, personas),
            "target": _persona_projection(item.target_account_uid, personas),
            "action_type": item.action_type,
            "reason": item.reason,
            "status": _effective_action_status(item),
            "starts_at": item.starts_at.isoformat(),
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            "revoked_at": item.revoked_at.isoformat() if item.revoked_at else None,
        }
        for item in actions
    ], total


async def create_appeal(
    db: AsyncSession,
    action_uid: UUID,
    viewer_uid: UUID | str,
    payload: ModerationAppealCreateRequest,
) -> dict:
    viewer = await _get_account(db, viewer_uid)
    action = await db.get(ModerationAction, action_uid)
    if not action or action.target_account_uid != viewer.uid:
        raise HTTPException(status_code=404, detail={"error_type": "moderation_action_not_found"})
    if action.status == "revoked":
        raise HTTPException(status_code=409, detail={"error_type": "moderation_action_already_revoked"})

    existing_result = await db.execute(
        select(ModerationAppeal.uid).where(
            ModerationAppeal.action_uid == action.uid,
            ModerationAppeal.appellant_account_uid == viewer.uid,
        ).limit(1)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"error_type": "moderation_appeal_exists"})

    appeal = ModerationAppeal(
        action_uid=action.uid,
        appellant_account_uid=viewer.uid,
        body=payload.body,
        status="pending",
    )
    db.add(appeal)
    await db.commit()
    await db.refresh(appeal)
    return {
        "uid": str(appeal.uid),
        "action_uid": str(appeal.action_uid),
        "status": appeal.status,
        "body": appeal.body,
        "created_at": appeal.created_at.isoformat(),
    }


async def list_my_appeals(
    db: AsyncSession,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    viewer = await _get_account(db, viewer_uid)
    filters = (ModerationAppeal.appellant_account_uid == viewer.uid,)
    total = int((await db.execute(select(func.count(ModerationAppeal.uid)).where(*filters))).scalar_one() or 0)
    result = await db.execute(
        select(ModerationAppeal, ModerationAction)
        .join(ModerationAction, ModerationAction.uid == ModerationAppeal.action_uid)
        .where(*filters)
        .order_by(ModerationAppeal.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        {
            "uid": str(appeal.uid),
            "action_uid": str(action.uid),
            "space_uid": str(action.room_uid),
            "action_type": action.action_type,
            "reason": action.reason,
            "body": appeal.body,
            "status": appeal.status,
            "resolution": appeal.resolution,
            "created_at": appeal.created_at.isoformat(),
            "resolved_at": appeal.resolved_at.isoformat() if appeal.resolved_at else None,
        }
        for appeal, action in result.all()
    ], total


async def list_space_appeals(
    db: AsyncSession,
    space_uid: UUID,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    room, _, _ = await _require_manager(db, space_uid, viewer_uid)
    base = (
        ModerationAction.room_uid == room.uid,
        ModerationAppeal.status == "pending",
    )
    total = int(
        (await db.execute(
            select(func.count(ModerationAppeal.uid))
            .join(ModerationAction, ModerationAction.uid == ModerationAppeal.action_uid)
            .where(*base)
        )).scalar_one() or 0
    )
    result = await db.execute(
        select(ModerationAppeal, ModerationAction)
        .join(ModerationAction, ModerationAction.uid == ModerationAppeal.action_uid)
        .where(*base)
        .order_by(ModerationAppeal.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()
    personas = await _persona_map(db, {appeal.appellant_account_uid for appeal, _ in rows if appeal.appellant_account_uid})
    return [
        {
            "uid": str(appeal.uid),
            "action_uid": str(action.uid),
            "action_type": action.action_type,
            "reason": action.reason,
            "body": appeal.body,
            "status": appeal.status,
            "appellant": _persona_projection(appeal.appellant_account_uid, personas),
            "created_at": appeal.created_at.isoformat(),
        }
        for appeal, action in rows
    ], total


async def resolve_appeal(
    db: AsyncSession,
    space_uid: UUID,
    appeal_uid: UUID,
    viewer_uid: UUID | str,
    payload: ModerationAppealResolveRequest,
) -> dict:
    room, reviewer, _ = await _require_manager(db, space_uid, viewer_uid)
    appeal = await db.get(ModerationAppeal, appeal_uid)
    if not appeal:
        raise HTTPException(status_code=404, detail={"error_type": "moderation_appeal_not_found"})
    action = await db.get(ModerationAction, appeal.action_uid)
    if not action or action.room_uid != room.uid:
        raise HTTPException(status_code=404, detail={"error_type": "moderation_appeal_not_found"})
    if appeal.status != "pending":
        raise HTTPException(status_code=409, detail={"error_type": "moderation_appeal_closed"})
    if action.moderator_account_uid == reviewer.uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_appeal_reviewer_conflict"},
        )

    now = datetime.utcnow()
    appeal.reviewer_account_uid = reviewer.uid
    appeal.resolution = payload.resolution
    appeal.resolved_at = now
    appeal.updated_at = now

    if payload.decision == "overturn":
        appeal.status = "overturned"
        action.status = "revoked"
        action.revoked_at = now
        action.updated_at = now
        if action.legacy_room_ban_id:
            await db.execute(
                update(RoomBan)
                .where(RoomBan.id == action.legacy_room_ban_id)
                .values(is_active=False)
            )
    else:
        appeal.status = "upheld"

    await db.commit()
    return {
        "uid": str(appeal.uid),
        "status": appeal.status,
        "resolution": appeal.resolution,
        "resolved_at": appeal.resolved_at.isoformat(),
        "action_status": _effective_action_status(action),
    }
