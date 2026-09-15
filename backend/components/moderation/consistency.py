from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from components.moderation.model import ModerationAction, ModerationAppeal, ModerationReport
from components.space.membership_service import _load_room, _manager_context


async def ensure_report_actionable(
    db: AsyncSession,
    *,
    space_uid: UUID,
    viewer_uid: UUID | str,
    report_uid: UUID | None,
    target_account_uid: UUID,
) -> None:
    """Authorize the Space manager before inspecting a private report."""
    room = await _load_room(db, space_uid)
    _, manager_role = await _manager_context(db, room, viewer_uid)
    if manager_role not in {"owner", "moderator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "space_moderation_required"},
        )

    if report_uid is None:
        return

    report = await db.get(ModerationReport, report_uid)
    if not report or report.room_uid != space_uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "moderation_report_not_found"},
        )
    if report.target_account_uid and report.target_account_uid != target_account_uid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "moderation_report_target_mismatch"},
        )
    if report.status not in {"open", "reviewing"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_report_closed"},
        )

    existing = await db.execute(
        select(ModerationAction.uid)
        .where(ModerationAction.report_uid == report_uid)
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_report_already_actioned"},
        )


async def supersede_previous_restrictions(
    db: AsyncSession,
    *,
    space_uid: UUID,
    target_account_uid: UUID,
    keep_action_uid: UUID,
) -> int:
    """Keep a single canonical active Space restriction for a target.

    Legacy RoomBan creation already deactivates older bans. This companion update
    keeps the canonical moderation journal consistent with enforcement. Replaced
    restrictions use the existing ``revoked`` state so appeal/UI semantics stay
    unambiguous while ``revoked_at`` preserves when replacement happened.
    Pending appeals against a replaced restriction are closed because there is no
    longer an active decision for an independent reviewer to uphold or overturn.
    """
    now = datetime.utcnow()
    result = await db.execute(
        update(ModerationAction)
        .where(
            ModerationAction.room_uid == space_uid,
            ModerationAction.target_account_uid == target_account_uid,
            ModerationAction.action_type == "restrict",
            ModerationAction.status == "active",
            ModerationAction.uid != keep_action_uid,
        )
        .values(status="revoked", revoked_at=now, updated_at=now)
        .returning(ModerationAction.uid)
    )
    revoked_action_uids = list(result.scalars().all())

    if revoked_action_uids:
        await db.execute(
            update(ModerationAppeal)
            .where(
                ModerationAppeal.action_uid.in_(revoked_action_uids),
                ModerationAppeal.status == "pending",
            )
            .values(
                status="overturned",
                resolution="Исходное ограничение было заменено новым решением модерации.",
                resolved_at=now,
                updated_at=now,
            )
        )

    await db.commit()
    return len(revoked_action_uids)
