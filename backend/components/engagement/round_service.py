from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from components.achievement.service import grant_achievement
from components.engagement.model import SpaceActivity
from components.engagement.round_model import ConversationRound, ConversationRoundResponse
from components.engagement.round_schemas import (
    ConversationRoundCreateRequest,
    ConversationRoundResponseRequest,
)
from components.identity.model import AccountRelationship, Persona
from components.space.membership_service import _load_room, _manager_context, _require_active_member


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return f"{value.isoformat()}Z"
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


async def _activity_context(
    db: AsyncSession,
    activity_uid: UUID,
    viewer_uid: UUID | str,
):
    activity = await db.get(SpaceActivity, activity_uid)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "activity_not_found"},
        )
    room = await _load_room(db, activity.room_uid)
    account = await _require_active_member(db, room, viewer_uid)
    _, manager_role = await _manager_context(db, room, account.uid)
    return activity, room, account, manager_role


def _can_manage(activity: SpaceActivity, account_uid: UUID, manager_role: str | None) -> bool:
    return bool(
        activity.created_by_account_uid == account_uid
        or manager_role in {"owner", "moderator"}
    )


def _round_projection(
    item: ConversationRound,
    *,
    response_count: int = 0,
    choice_counts: dict[str, int] | None = None,
    viewer_response: ConversationRoundResponse | None = None,
    can_manage: bool = False,
) -> dict:
    choice_counts = choice_counts or {}
    return {
        "uid": str(item.uid),
        "activity_uid": str(item.activity_uid),
        "round_type": item.round_type,
        "prompt": item.prompt,
        "option_a": item.option_a,
        "option_b": item.option_b,
        "status": item.status,
        "response_count": int(response_count),
        "choice_counts": {
            "a": int(choice_counts.get("a", 0)),
            "b": int(choice_counts.get("b", 0)),
        }
        if item.round_type == "choice"
        else None,
        "viewer_response": {
            "choice": viewer_response.choice,
            "body": viewer_response.body,
            "created_at": _utc_iso(viewer_response.created_at),
            "updated_at": _utc_iso(viewer_response.updated_at),
        }
        if viewer_response
        else None,
        "can_manage": can_manage,
        "created_at": _utc_iso(item.created_at),
        "updated_at": _utc_iso(item.updated_at),
        "closed_at": _utc_iso(item.closed_at),
    }


async def list_rounds(
    db: AsyncSession,
    activity_uid: UUID,
    viewer_uid: UUID | str,
) -> list[dict]:
    activity, _, account, manager_role = await _activity_context(db, activity_uid, viewer_uid)
    result = await db.execute(
        select(ConversationRound)
        .where(ConversationRound.activity_uid == activity.uid)
        .order_by(ConversationRound.created_at.desc())
    )
    rounds = result.scalars().all()
    if not rounds:
        return []

    round_uids = [item.uid for item in rounds]
    count_result = await db.execute(
        select(ConversationRoundResponse.round_uid, func.count(ConversationRoundResponse.account_uid))
        .where(ConversationRoundResponse.round_uid.in_(round_uids))
        .group_by(ConversationRoundResponse.round_uid)
    )
    counts = {round_uid: int(count) for round_uid, count in count_result.all()}

    choice_result = await db.execute(
        select(
            ConversationRoundResponse.round_uid,
            ConversationRoundResponse.choice,
            func.count(ConversationRoundResponse.account_uid),
        )
        .where(
            ConversationRoundResponse.round_uid.in_(round_uids),
            ConversationRoundResponse.choice.is_not(None),
        )
        .group_by(ConversationRoundResponse.round_uid, ConversationRoundResponse.choice)
    )
    choice_counts: dict[UUID, dict[str, int]] = {}
    for round_uid, choice, count in choice_result.all():
        choice_counts.setdefault(round_uid, {})[choice] = int(count)

    viewer_result = await db.execute(
        select(ConversationRoundResponse).where(
            ConversationRoundResponse.round_uid.in_(round_uids),
            ConversationRoundResponse.account_uid == account.uid,
        )
    )
    viewer_by_round = {item.round_uid: item for item in viewer_result.scalars().all()}
    can_manage = _can_manage(activity, account.uid, manager_role)

    return [
        _round_projection(
            item,
            response_count=counts.get(item.uid, 0),
            choice_counts=choice_counts.get(item.uid),
            viewer_response=viewer_by_round.get(item.uid),
            can_manage=can_manage,
        )
        for item in rounds
    ]


async def create_round(
    db: AsyncSession,
    activity_uid: UUID,
    viewer_uid: UUID | str,
    payload: ConversationRoundCreateRequest,
) -> dict:
    activity, room, account, manager_role = await _activity_context(db, activity_uid, viewer_uid)
    if activity.status != "scheduled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "activity_not_open"},
        )
    if not _can_manage(activity, account.uid, manager_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "conversation_round_manage_required"},
        )

    existing_result = await db.execute(
        select(ConversationRound.uid).where(
            ConversationRound.activity_uid == activity.uid,
            ConversationRound.status == "open",
        ).limit(1)
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "conversation_round_already_open"},
        )

    item = ConversationRound(
        activity_uid=activity.uid,
        created_by_account_uid=account.uid,
        round_type=payload.round_type,
        prompt=payload.prompt,
        option_a=payload.option_a,
        option_b=payload.option_b,
        status="open",
    )
    db.add(item)
    try:
        await db.flush()
        await grant_achievement(
            db,
            account_uid=account.uid,
            code="conversation_starter",
            source_kind="conversation_round_created",
            source_uid=item.uid,
            context_room_uid=room.uid,
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "conversation_round_already_open"},
        ) from exc
    await db.refresh(item)
    return _round_projection(item, can_manage=True)


async def close_round(
    db: AsyncSession,
    activity_uid: UUID,
    round_uid: UUID,
    viewer_uid: UUID | str,
) -> dict:
    activity, _, account, manager_role = await _activity_context(db, activity_uid, viewer_uid)
    item = await db.get(ConversationRound, round_uid)
    if not item or item.activity_uid != activity.uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "conversation_round_not_found"},
        )
    if not _can_manage(activity, account.uid, manager_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "conversation_round_manage_required"},
        )
    if item.status == "closed":
        return _round_projection(item, can_manage=True)

    now = datetime.utcnow()
    item.status = "closed"
    item.closed_at = now
    item.updated_at = now
    await db.commit()
    await db.refresh(item)
    return _round_projection(item, can_manage=True)


async def _blocked_account_uids(
    db: AsyncSession,
    viewer_account_uid: UUID,
) -> set[UUID]:
    result = await db.execute(
        select(
            AccountRelationship.from_account_uid,
            AccountRelationship.to_account_uid,
        ).where(
            AccountRelationship.relation_type == "block",
            or_(
                AccountRelationship.from_account_uid == viewer_account_uid,
                AccountRelationship.to_account_uid == viewer_account_uid,
            ),
        )
    )
    blocked: set[UUID] = set()
    for from_uid, to_uid in result.all():
        blocked.add(to_uid if from_uid == viewer_account_uid else from_uid)
    return blocked


async def list_round_responses(
    db: AsyncSession,
    round_uid: UUID,
    viewer_uid: UUID | str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    round_item = await db.get(ConversationRound, round_uid)
    if not round_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "conversation_round_not_found"},
        )
    _, _, account, _ = await _activity_context(db, round_item.activity_uid, viewer_uid)
    blocked = await _blocked_account_uids(db, account.uid)

    filters = [ConversationRoundResponse.round_uid == round_item.uid]
    if blocked:
        filters.append(ConversationRoundResponse.account_uid.not_in(blocked))

    total = int(
        (await db.execute(select(func.count(ConversationRoundResponse.account_uid)).where(*filters))).scalar_one() or 0
    )
    result = await db.execute(
        select(ConversationRoundResponse, Persona)
        .outerjoin(
            Persona,
            and_(
                Persona.account_uid == ConversationRoundResponse.account_uid,
                Persona.is_primary.is_(True),
            ),
        )
        .where(*filters)
        .order_by(ConversationRoundResponse.created_at.asc())
        .limit(limit)
        .offset(offset)
    )

    items = []
    for response, persona in result.all():
        items.append(
            {
                "account_uid": str(response.account_uid),
                "choice": response.choice,
                "body": response.body,
                "persona": {
                    "persona_uid": str(persona.uid) if persona else None,
                    "handle": persona.handle if persona else None,
                    "display_name": persona.display_name if persona else None,
                    "avatar": persona.avatar if persona else None,
                },
                "created_at": _utc_iso(response.created_at),
                "updated_at": _utc_iso(response.updated_at),
            }
        )
    return items, total


def _validate_response_payload(
    round_item: ConversationRound,
    payload: ConversationRoundResponseRequest,
) -> None:
    if round_item.round_type == "choice":
        if payload.choice not in {"a", "b"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error_type": "conversation_round_choice_required"},
            )
        return

    if payload.choice is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "conversation_round_choice_not_allowed"},
        )
    if not payload.body or len(payload.body) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_type": "conversation_round_body_required"},
        )


async def put_round_response(
    db: AsyncSession,
    round_uid: UUID,
    viewer_uid: UUID | str,
    payload: ConversationRoundResponseRequest,
) -> dict:
    round_item = await db.get(ConversationRound, round_uid)
    if not round_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "conversation_round_not_found"},
        )
    activity, room, account, _ = await _activity_context(db, round_item.activity_uid, viewer_uid)
    if round_item.status != "open" or activity.status != "scheduled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "conversation_round_closed"},
        )
    _validate_response_payload(round_item, payload)

    response = await db.get(ConversationRoundResponse, (round_item.uid, account.uid))
    if not response:
        response = ConversationRoundResponse(
            round_uid=round_item.uid,
            account_uid=account.uid,
        )
        db.add(response)
    response.choice = payload.choice
    response.body = payload.body
    response.updated_at = datetime.utcnow()

    await db.flush()
    await grant_achievement(
        db,
        account_uid=account.uid,
        code="first_round_response",
        source_kind="conversation_round_response",
        source_uid=round_item.uid,
        context_room_uid=room.uid,
    )
    await db.commit()
    await db.refresh(response)
    return {
        "round_uid": str(response.round_uid),
        "account_uid": str(response.account_uid),
        "choice": response.choice,
        "body": response.body,
        "created_at": _utc_iso(response.created_at),
        "updated_at": _utc_iso(response.updated_at),
    }
