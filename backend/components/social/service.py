from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Account, AccountRelationship, Persona


RELATION_FOLLOW = "follow"
RELATION_FRIEND_REQUEST = "friend_request"
RELATION_FRIEND = "friend"
RELATION_BLOCK = "block"


def _normalize_uid(value: UUID | str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "invalid_account_uid"},
        ) from exc


async def _active_account(db: AsyncSession, account_uid: UUID | str) -> Account:
    uid = _normalize_uid(account_uid)
    account = await db.get(Account, uid)
    if not account or account.deleted_at is not None or account.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "account_not_found"},
        )
    return account


async def _pair(
    db: AsyncSession,
    viewer_uid: UUID | str,
    target_uid: UUID | str,
) -> tuple[Account, Account]:
    viewer = await _active_account(db, viewer_uid)
    target = await _active_account(db, target_uid)
    if viewer.uid == target.uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "relationship_with_self_not_allowed"},
        )
    return viewer, target


async def _relationship_exists(
    db: AsyncSession,
    from_uid: UUID,
    to_uid: UUID,
    relation_type: str,
) -> bool:
    result = await db.execute(
        select(AccountRelationship.id)
        .where(
            AccountRelationship.from_account_uid == from_uid,
            AccountRelationship.to_account_uid == to_uid,
            AccountRelationship.relation_type == relation_type,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _blocked_between(db: AsyncSession, left_uid: UUID, right_uid: UUID) -> bool:
    result = await db.execute(
        select(AccountRelationship.id)
        .where(
            AccountRelationship.relation_type == RELATION_BLOCK,
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


async def _ensure_not_blocked(db: AsyncSession, left_uid: UUID, right_uid: UUID) -> None:
    if await _blocked_between(db, left_uid, right_uid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "social_relationship_blocked"},
        )


async def _add_relationship(
    db: AsyncSession,
    from_uid: UUID,
    to_uid: UUID,
    relation_type: str,
) -> None:
    if await _relationship_exists(db, from_uid, to_uid, relation_type):
        return
    db.add(
        AccountRelationship(
            from_account_uid=from_uid,
            to_account_uid=to_uid,
            relation_type=relation_type,
        )
    )


async def relationship_projection(
    db: AsyncSession,
    viewer_uid: UUID | str,
    target_uid: UUID | str,
) -> dict:
    viewer, target = await _pair(db, viewer_uid, target_uid)

    result = await db.execute(
        select(
            AccountRelationship.from_account_uid,
            AccountRelationship.to_account_uid,
            AccountRelationship.relation_type,
        ).where(
            AccountRelationship.from_account_uid.in_([viewer.uid, target.uid]),
            AccountRelationship.to_account_uid.in_([viewer.uid, target.uid]),
        )
    )
    relations = {
        (from_uid, to_uid, relation_type)
        for from_uid, to_uid, relation_type in result.all()
    }

    following = (viewer.uid, target.uid, RELATION_FOLLOW) in relations
    followed_by = (target.uid, viewer.uid, RELATION_FOLLOW) in relations
    blocked_by_me = (viewer.uid, target.uid, RELATION_BLOCK) in relations
    blocked_me = (target.uid, viewer.uid, RELATION_BLOCK) in relations
    outgoing_request = (viewer.uid, target.uid, RELATION_FRIEND_REQUEST) in relations
    incoming_request = (target.uid, viewer.uid, RELATION_FRIEND_REQUEST) in relations
    friends = (
        (viewer.uid, target.uid, RELATION_FRIEND) in relations
        and (target.uid, viewer.uid, RELATION_FRIEND) in relations
    )

    return {
        "account_uid": str(target.uid),
        "following": following,
        "followed_by": followed_by,
        "friends": friends,
        "friend_request": (
            "outgoing" if outgoing_request else "incoming" if incoming_request else None
        ),
        "blocked_by_me": blocked_by_me,
        "blocked_me": blocked_me,
    }


async def follow_account(
    db: AsyncSession,
    viewer_uid: UUID | str,
    target_uid: UUID | str,
) -> dict:
    viewer, target = await _pair(db, viewer_uid, target_uid)
    await _ensure_not_blocked(db, viewer.uid, target.uid)
    await _add_relationship(db, viewer.uid, target.uid, RELATION_FOLLOW)
    await db.commit()
    return await relationship_projection(db, viewer.uid, target.uid)


async def unfollow_account(
    db: AsyncSession,
    viewer_uid: UUID | str,
    target_uid: UUID | str,
) -> dict:
    viewer, target = await _pair(db, viewer_uid, target_uid)
    await db.execute(
        delete(AccountRelationship).where(
            AccountRelationship.from_account_uid == viewer.uid,
            AccountRelationship.to_account_uid == target.uid,
            AccountRelationship.relation_type == RELATION_FOLLOW,
        )
    )
    await db.commit()
    return await relationship_projection(db, viewer.uid, target.uid)


async def apply_friend_action(
    db: AsyncSession,
    viewer_uid: UUID | str,
    target_uid: UUID | str,
    action: str,
) -> dict:
    viewer, target = await _pair(db, viewer_uid, target_uid)

    if action in {"request", "accept"}:
        await _ensure_not_blocked(db, viewer.uid, target.uid)

    if action == "request":
        state = await relationship_projection(db, viewer.uid, target.uid)
        if state["friends"]:
            return state
        if state["friend_request"] == "incoming":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_type": "incoming_friend_request_exists"},
            )
        await _add_relationship(db, viewer.uid, target.uid, RELATION_FRIEND_REQUEST)

    elif action == "accept":
        incoming = await _relationship_exists(
            db, target.uid, viewer.uid, RELATION_FRIEND_REQUEST
        )
        if not incoming:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_type": "friend_request_not_found"},
            )
        await db.execute(
            delete(AccountRelationship).where(
                AccountRelationship.relation_type == RELATION_FRIEND_REQUEST,
                or_(
                    and_(
                        AccountRelationship.from_account_uid == viewer.uid,
                        AccountRelationship.to_account_uid == target.uid,
                    ),
                    and_(
                        AccountRelationship.from_account_uid == target.uid,
                        AccountRelationship.to_account_uid == viewer.uid,
                    ),
                ),
            )
        )
        await _add_relationship(db, viewer.uid, target.uid, RELATION_FRIEND)
        await _add_relationship(db, target.uid, viewer.uid, RELATION_FRIEND)

    elif action == "reject":
        incoming = await _relationship_exists(
            db, target.uid, viewer.uid, RELATION_FRIEND_REQUEST
        )
        if not incoming:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_type": "friend_request_not_found"},
            )
        await db.execute(
            delete(AccountRelationship).where(
                AccountRelationship.from_account_uid == target.uid,
                AccountRelationship.to_account_uid == viewer.uid,
                AccountRelationship.relation_type == RELATION_FRIEND_REQUEST,
            )
        )

    elif action == "remove":
        await db.execute(
            delete(AccountRelationship).where(
                AccountRelationship.relation_type.in_([RELATION_FRIEND, RELATION_FRIEND_REQUEST]),
                or_(
                    and_(
                        AccountRelationship.from_account_uid == viewer.uid,
                        AccountRelationship.to_account_uid == target.uid,
                    ),
                    and_(
                        AccountRelationship.from_account_uid == target.uid,
                        AccountRelationship.to_account_uid == viewer.uid,
                    ),
                ),
            )
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "invalid_friend_action"},
        )

    await db.commit()
    return await relationship_projection(db, viewer.uid, target.uid)


async def block_account(
    db: AsyncSession,
    viewer_uid: UUID | str,
    target_uid: UUID | str,
) -> dict:
    viewer, target = await _pair(db, viewer_uid, target_uid)

    await db.execute(
        delete(AccountRelationship).where(
            AccountRelationship.relation_type.in_([
                RELATION_FOLLOW,
                RELATION_FRIEND_REQUEST,
                RELATION_FRIEND,
            ]),
            or_(
                and_(
                    AccountRelationship.from_account_uid == viewer.uid,
                    AccountRelationship.to_account_uid == target.uid,
                ),
                and_(
                    AccountRelationship.from_account_uid == target.uid,
                    AccountRelationship.to_account_uid == viewer.uid,
                ),
            ),
        )
    )
    await _add_relationship(db, viewer.uid, target.uid, RELATION_BLOCK)
    await db.commit()
    return await relationship_projection(db, viewer.uid, target.uid)


async def unblock_account(
    db: AsyncSession,
    viewer_uid: UUID | str,
    target_uid: UUID | str,
) -> dict:
    viewer, target = await _pair(db, viewer_uid, target_uid)
    await db.execute(
        delete(AccountRelationship).where(
            AccountRelationship.from_account_uid == viewer.uid,
            AccountRelationship.to_account_uid == target.uid,
            AccountRelationship.relation_type == RELATION_BLOCK,
        )
    )
    await db.commit()
    return await relationship_projection(db, viewer.uid, target.uid)


async def _people_for_relation_rows(
    db: AsyncSession,
    account_uids: list[UUID],
) -> list[dict]:
    if not account_uids:
        return []
    persona_result = await db.execute(
        select(Persona).where(
            Persona.account_uid.in_(account_uids),
            Persona.is_primary.is_(True),
        )
    )
    personas = {persona.account_uid: persona for persona in persona_result.scalars().all()}
    return [
        {
            "account_uid": str(account_uid),
            "persona": {
                "uid": str(account_uid),
                "persona_uid": str(personas[account_uid].uid) if account_uid in personas else None,
                "handle": personas[account_uid].handle if account_uid in personas else None,
                "display_name": personas[account_uid].display_name if account_uid in personas else None,
                "avatar": personas[account_uid].avatar if account_uid in personas else None,
                "social_intent": personas[account_uid].social_intent if account_uid in personas else None,
            },
        }
        for account_uid in account_uids
    ]


async def list_friends(
    db: AsyncSession,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    viewer = await _active_account(db, viewer_uid)
    base_filter = (
        AccountRelationship.from_account_uid == viewer.uid,
        AccountRelationship.relation_type == RELATION_FRIEND,
    )
    total_result = await db.execute(
        select(func.count(AccountRelationship.id)).where(*base_filter)
    )
    total = int(total_result.scalar_one() or 0)
    result = await db.execute(
        select(AccountRelationship.to_account_uid)
        .where(*base_filter)
        .order_by(AccountRelationship.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    uids = [uid for (uid,) in result.all()]
    return await _people_for_relation_rows(db, uids), total


async def list_friend_requests(
    db: AsyncSession,
    viewer_uid: UUID | str,
    direction: str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    viewer = await _active_account(db, viewer_uid)
    if direction == "incoming":
        filter_expression = AccountRelationship.to_account_uid == viewer.uid
        person_column = AccountRelationship.from_account_uid
    elif direction == "outgoing":
        filter_expression = AccountRelationship.from_account_uid == viewer.uid
        person_column = AccountRelationship.to_account_uid
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "invalid_request_direction"},
        )

    filters = (
        filter_expression,
        AccountRelationship.relation_type == RELATION_FRIEND_REQUEST,
    )
    total_result = await db.execute(
        select(func.count(AccountRelationship.id)).where(*filters)
    )
    total = int(total_result.scalar_one() or 0)
    result = await db.execute(
        select(person_column)
        .where(*filters)
        .order_by(AccountRelationship.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    uids = [uid for (uid,) in result.all()]
    return await _people_for_relation_rows(db, uids), total
