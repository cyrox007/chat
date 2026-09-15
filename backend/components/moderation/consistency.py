from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from components.moderation.model import ModerationAction


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
    )
    await db.commit()
    return int(result.rowcount or 0)
