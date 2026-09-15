from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from components.identity.model import AccountRelationship, Persona, PrivacySettings
from components.space.model import SpaceMembership


async def can_view_profile(
    db: AsyncSession,
    viewer_uid: UUID | str,
    target_uid: UUID | str,
) -> bool:
    viewer = UUID(str(viewer_uid))
    target = UUID(str(target_uid))
    if viewer == target:
        return True

    blocked_result = await db.execute(
        select(AccountRelationship.id)
        .where(
            AccountRelationship.relation_type == "block",
            or_(
                and_(
                    AccountRelationship.from_account_uid == viewer,
                    AccountRelationship.to_account_uid == target,
                ),
                and_(
                    AccountRelationship.from_account_uid == target,
                    AccountRelationship.to_account_uid == viewer,
                ),
            ),
        )
        .limit(1)
    )
    if blocked_result.scalar_one_or_none() is not None:
        return False

    visibility_result = await db.execute(
        select(PrivacySettings.profile_visibility)
        .join(Persona, Persona.uid == PrivacySettings.persona_uid)
        .where(
            Persona.account_uid == target,
            Persona.is_primary.is_(True),
        )
        .limit(1)
    )
    visibility = visibility_result.scalar_one_or_none() or "public"
    if visibility == "public":
        return True
    if visibility == "private":
        return False
    if visibility != "shared_spaces":
        return False

    viewer_membership = aliased(SpaceMembership)
    target_membership = aliased(SpaceMembership)
    shared_result = await db.execute(
        select(viewer_membership.room_uid)
        .join(
            target_membership,
            target_membership.room_uid == viewer_membership.room_uid,
        )
        .where(
            viewer_membership.account_uid == viewer,
            viewer_membership.status == "active",
            target_membership.account_uid == target,
            target_membership.status == "active",
        )
        .limit(1)
    )
    return shared_result.scalar_one_or_none() is not None
