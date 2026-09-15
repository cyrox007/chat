from collections import defaultdict
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from components.identity.model import Account, AccountRelationship, Persona, PrivacySettings
from components.social.service import (
    RELATION_FOLLOW,
    RELATION_FRIEND,
    RELATION_FRIEND_REQUEST,
    _active_account,
)
from components.space.model import SpaceMembership


async def discover_people(
    db: AsyncSession,
    viewer_uid: UUID | str,
    query: str | None = None,
    social_intent: str | None = None,
    limit: int = 30,
    offset: int = 0,
) -> tuple[list[dict], int]:
    viewer = await _active_account(db, viewer_uid)

    viewer_membership = aliased(SpaceMembership)
    candidate_membership = aliased(SpaceMembership)
    shared_space_exists = (
        select(viewer_membership.uid)
        .join(
            candidate_membership,
            candidate_membership.room_uid == viewer_membership.room_uid,
        )
        .where(
            viewer_membership.account_uid == viewer.uid,
            viewer_membership.status == "active",
            candidate_membership.account_uid == Persona.account_uid,
            candidate_membership.status == "active",
        )
        .limit(1)
        .exists()
    )

    blocked_between = (
        select(AccountRelationship.id)
        .where(
            AccountRelationship.relation_type == "block",
            or_(
                and_(
                    AccountRelationship.from_account_uid == viewer.uid,
                    AccountRelationship.to_account_uid == Persona.account_uid,
                ),
                and_(
                    AccountRelationship.from_account_uid == Persona.account_uid,
                    AccountRelationship.to_account_uid == viewer.uid,
                ),
            ),
        )
        .limit(1)
        .exists()
    )

    visibility = func.coalesce(PrivacySettings.profile_visibility, "public")
    base_filters = [
        Persona.is_primary.is_(True),
        Persona.account_uid != viewer.uid,
        Account.status == "active",
        Account.deleted_at.is_(None),
        ~blocked_between,
        or_(
            visibility == "public",
            and_(visibility == "shared_spaces", shared_space_exists),
        ),
    ]

    normalized_query = (query or "").strip()
    if normalized_query:
        pattern = f"%{normalized_query}%"
        base_filters.append(
            or_(
                Persona.handle.ilike(pattern),
                Persona.display_name.ilike(pattern),
                Persona.bio.ilike(pattern),
            )
        )
    if social_intent:
        base_filters.append(Persona.social_intent == social_intent)

    stmt = (
        select(Persona, PrivacySettings)
        .join(Account, Account.uid == Persona.account_uid)
        .outerjoin(PrivacySettings, PrivacySettings.persona_uid == Persona.uid)
        .where(*base_filters)
        .order_by(Persona.updated_at.desc(), Persona.created_at.desc())
    )

    total_result = await db.execute(
        select(func.count(Persona.uid))
        .join(Account, Account.uid == Persona.account_uid)
        .outerjoin(PrivacySettings, PrivacySettings.persona_uid == Persona.uid)
        .where(*base_filters)
    )
    total = int(total_result.scalar_one() or 0)

    result = await db.execute(stmt.limit(limit).offset(offset))
    rows = result.all()
    account_uids = [persona.account_uid for persona, _ in rows]

    relations_by_target: dict[UUID, set[tuple[UUID, UUID, str]]] = defaultdict(set)
    if account_uids:
        relationship_result = await db.execute(
            select(
                AccountRelationship.from_account_uid,
                AccountRelationship.to_account_uid,
                AccountRelationship.relation_type,
            ).where(
                AccountRelationship.relation_type.in_([
                    RELATION_FOLLOW,
                    RELATION_FRIEND_REQUEST,
                    RELATION_FRIEND,
                ]),
                or_(
                    and_(
                        AccountRelationship.from_account_uid == viewer.uid,
                        AccountRelationship.to_account_uid.in_(account_uids),
                    ),
                    and_(
                        AccountRelationship.from_account_uid.in_(account_uids),
                        AccountRelationship.to_account_uid == viewer.uid,
                    ),
                ),
            )
        )
        for from_uid, to_uid, relation_type in relationship_result.all():
            target_uid = to_uid if from_uid == viewer.uid else from_uid
            relations_by_target[target_uid].add((from_uid, to_uid, relation_type))

    people = []
    for persona, privacy in rows:
        target_uid = persona.account_uid
        relations = relations_by_target.get(target_uid, set())
        following = (viewer.uid, target_uid, RELATION_FOLLOW) in relations
        followed_by = (target_uid, viewer.uid, RELATION_FOLLOW) in relations
        friends = (
            (viewer.uid, target_uid, RELATION_FRIEND) in relations
            and (target_uid, viewer.uid, RELATION_FRIEND) in relations
        )
        outgoing_request = (viewer.uid, target_uid, RELATION_FRIEND_REQUEST) in relations
        incoming_request = (target_uid, viewer.uid, RELATION_FRIEND_REQUEST) in relations
        show_location = bool(privacy and privacy.show_location)

        people.append(
            {
                "account_uid": str(target_uid),
                "persona_uid": str(persona.uid),
                "handle": persona.handle,
                "display_name": persona.display_name,
                "avatar": persona.avatar,
                "bio": persona.bio,
                "city": persona.city if show_location else None,
                "country": persona.country if show_location else None,
                "social_intent": persona.social_intent,
                "relationship": {
                    "following": following,
                    "followed_by": followed_by,
                    "friends": friends,
                    "friend_request": (
                        "outgoing" if outgoing_request else "incoming" if incoming_request else None
                    ),
                },
            }
        )

    return people, total
