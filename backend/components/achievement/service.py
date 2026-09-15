from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from components.achievement.model import AccountAchievement, AchievementDefinition
from components.identity.model import Account
from components.social.privacy import can_view_profile


SYSTEM_ACHIEVEMENT_CODES = {
    "first_host",
    "conversation_starter",
    "first_round_response",
}


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return f"{value.isoformat()}Z"
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


async def grant_achievement(
    db: AsyncSession,
    *,
    account_uid: UUID,
    code: str,
    source_kind: str,
    source_uid: UUID | None = None,
    context_room_uid: UUID | None = None,
) -> bool:
    """Grant an allowlisted system achievement without committing the transaction.

    There is intentionally no public HTTP endpoint for this operation. The
    database unique constraint plus ON CONFLICT makes concurrent grants idempotent.
    """
    if code not in SYSTEM_ACHIEVEMENT_CODES:
        raise ValueError(f"Unknown system achievement: {code}")

    definition_result = await db.execute(
        select(AchievementDefinition.code).where(
            AchievementDefinition.code == code,
            AchievementDefinition.is_active.is_(True),
        ).limit(1)
    )
    if definition_result.scalar_one_or_none() is None:
        return False

    statement = (
        insert(AccountAchievement)
        .values(
            account_uid=account_uid,
            achievement_code=code,
            context_room_uid=context_room_uid,
            source_kind=source_kind,
            source_uid=source_uid,
        )
        .on_conflict_do_nothing(
            constraint="uq_account_achievement_code",
        )
        .returning(AccountAchievement.uid)
    )
    result = await db.execute(statement)
    return result.scalar_one_or_none() is not None


async def _account_or_404(db: AsyncSession, account_uid: UUID | str) -> Account:
    try:
        normalized = UUID(str(account_uid))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "profile_not_available"},
        ) from exc

    account = await db.get(Account, normalized)
    if not account or account.status != "active" or account.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "profile_not_available"},
        )
    return account


async def list_achievements(
    db: AsyncSession,
    *,
    target_account_uid: UUID | str,
    viewer_uid: UUID | str,
    include_private_context: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    target = await _account_or_404(db, target_account_uid)
    if not await can_view_profile(db, viewer_uid, target.uid):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "profile_not_available"},
        )

    filters = (AccountAchievement.account_uid == target.uid,)
    total = int(
        (await db.execute(select(func.count(AccountAchievement.uid)).where(*filters))).scalar_one() or 0
    )
    result = await db.execute(
        select(AccountAchievement, AchievementDefinition)
        .join(
            AchievementDefinition,
            AchievementDefinition.code == AccountAchievement.achievement_code,
        )
        .where(*filters)
        .order_by(AccountAchievement.earned_at.desc(), AccountAchievement.uid.desc())
        .limit(limit)
        .offset(offset)
    )

    items: list[dict] = []
    for award, definition in result.all():
        item = {
            "code": definition.code,
            "title": definition.title,
            "description": definition.description,
            "icon_preset": definition.icon_preset,
            "category": definition.category,
            "earned_at": _utc_iso(award.earned_at),
        }
        if include_private_context:
            item.update(
                {
                    "source_kind": award.source_kind,
                    "source_uid": str(award.source_uid) if award.source_uid else None,
                    "context_space_uid": str(award.context_room_uid) if award.context_room_uid else None,
                }
            )
        items.append(item)
    return items, total
