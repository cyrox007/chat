from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.engagement.model import SpaceActivity
from components.engagement.occurrence_model import ActivityOccurrence
from components.identity.model import AccountRelationship, Persona
from components.message.model import Message
from components.space.model import SpaceEvent, SpaceMembership, SpaceSettings, SpaceTag
from components.space.service import list_spaces


DISCOVERY_POOL_LIMIT = 200
DISCOVERY_ALGORITHM = "organic-v1"
UPCOMING_WINDOW_DAYS = 14
RECENT_MESSAGE_HOURS = 24

INTENT_PURPOSES = {
    "open": {"conversation", "community"},
    "meet": {"meet_people"},
    "games": {"games"},
}

REASON_LABELS = {
    "already_member": "Вы уже участник",
    "request_pending": "Ваша заявка уже рассматривается",
    "active_conversation": "Здесь недавно общались",
    "upcoming_activity": "Скоро общая активность",
    "shared_topics": "Похожие темы на ваши пространства",
    "familiar_format": "Знакомый вам формат",
    "intent_match": "Подходит вашему текущему настрою",
    "new_space": "Новое пространство",
}


def _reason(code: str) -> dict:
    return {"code": code, "label": REASON_LABELS[code]}


def _normalize_topic(value: str) -> str:
    return " ".join(str(value).split()).strip().casefold()


def _parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


async def _blocked_account_uids(db: AsyncSession, viewer_uid: UUID) -> set[UUID]:
    result = await db.execute(
        select(
            AccountRelationship.from_account_uid,
            AccountRelationship.to_account_uid,
        ).where(
            AccountRelationship.relation_type == "block",
            or_(
                AccountRelationship.from_account_uid == viewer_uid,
                AccountRelationship.to_account_uid == viewer_uid,
            ),
        )
    )
    blocked: set[UUID] = set()
    for from_uid, to_uid in result.all():
        blocked.add(to_uid if from_uid == viewer_uid else from_uid)
    blocked.discard(viewer_uid)
    return blocked


async def _viewer_context(
    db: AsyncSession,
    viewer_uid: UUID,
) -> tuple[set[str], set[str], str | None]:
    membership_result = await db.execute(
        select(SpaceMembership.room_uid).where(
            SpaceMembership.account_uid == viewer_uid,
            SpaceMembership.status == "active",
        )
    )
    room_uids = [room_uid for (room_uid,) in membership_result.all()]

    purposes: set[str] = set()
    tags: set[str] = set()
    if room_uids:
        purpose_result = await db.execute(
            select(SpaceSettings.purpose).where(SpaceSettings.room_uid.in_(room_uids))
        )
        purposes = {str(purpose) for (purpose,) in purpose_result.all() if purpose}

        tag_result = await db.execute(
            select(SpaceTag.label).where(SpaceTag.room_uid.in_(room_uids))
        )
        tags = {
            _normalize_topic(label)
            for (label,) in tag_result.all()
            if label and _normalize_topic(label)
        }

    persona_result = await db.execute(
        select(Persona.social_intent)
        .where(Persona.account_uid == viewer_uid, Persona.is_primary.is_(True))
        .limit(1)
    )
    social_intent = persona_result.scalar_one_or_none()
    return purposes, tags, str(social_intent) if social_intent else None


async def _recent_message_counts(
    db: AsyncSession,
    room_uids: list[UUID],
    now: datetime,
) -> dict[UUID, int]:
    if not room_uids:
        return {}
    since = now - timedelta(hours=RECENT_MESSAGE_HOURS)
    result = await db.execute(
        select(Message.room_uid, func.count(Message.uid))
        .where(
            Message.room_uid.in_(room_uids),
            Message.created_at >= since,
        )
        .group_by(Message.room_uid)
    )
    return {room_uid: int(count) for room_uid, count in result.all()}


async def _upcoming_by_room(
    db: AsyncSession,
    room_uids: list[UUID],
    now: datetime,
) -> dict[UUID, dict]:
    if not room_uids:
        return {}

    until = now + timedelta(days=UPCOMING_WINDOW_DAYS)
    candidates: dict[UUID, list[dict]] = defaultdict(list)

    event_result = await db.execute(
        select(SpaceEvent.room_uid, SpaceEvent.title, SpaceEvent.starts_at)
        .where(
            SpaceEvent.room_uid.in_(room_uids),
            SpaceEvent.status == "scheduled",
            SpaceEvent.starts_at >= now,
            SpaceEvent.starts_at <= until,
        )
        .order_by(SpaceEvent.room_uid.asc(), SpaceEvent.starts_at.asc())
    )
    for room_uid, title, starts_at in event_result.all():
        candidates[room_uid].append(
            {"kind": "event", "title": title, "starts_at": starts_at}
        )

    occurrence_result = await db.execute(
        select(
            SpaceActivity.room_uid,
            SpaceActivity.title,
            ActivityOccurrence.starts_at,
        )
        .join(ActivityOccurrence, ActivityOccurrence.activity_uid == SpaceActivity.uid)
        .where(
            SpaceActivity.room_uid.in_(room_uids),
            SpaceActivity.status == "scheduled",
            ActivityOccurrence.status == "scheduled",
            ActivityOccurrence.starts_at >= now,
            ActivityOccurrence.starts_at <= until,
        )
        .order_by(SpaceActivity.room_uid.asc(), ActivityOccurrence.starts_at.asc())
    )
    for room_uid, title, starts_at in occurrence_result.all():
        candidates[room_uid].append(
            {"kind": "activity", "title": title, "starts_at": starts_at}
        )

    result: dict[UUID, dict] = {}
    for room_uid, items in candidates.items():
        result[room_uid] = min(items, key=lambda item: item["starts_at"])
    return result


def _score_space(
    space: dict,
    *,
    recent_messages: int,
    upcoming: dict | None,
    viewer_purposes: set[str],
    viewer_tags: set[str],
    social_intent: str | None,
    now: datetime,
) -> tuple[float, list[dict]]:
    score = 0.0
    reasons: list[dict] = []

    membership = space.get("viewer_membership") or {}
    membership_status = membership.get("status")
    if membership_status == "active":
        score += 12
        reasons.append(_reason("already_member"))
    elif membership_status == "pending":
        score += 4
        reasons.append(_reason("request_pending"))

    if recent_messages > 0:
        score += 7 + min(11, math.log2(recent_messages + 1) * 2.5)
        reasons.append(_reason("active_conversation"))

    if upcoming:
        hours = max(0.0, (upcoming["starts_at"] - now).total_seconds() / 3600)
        score += 15 if hours <= 24 else 10 if hours <= 24 * 7 else 6
        reasons.append(_reason("upcoming_activity"))

    space_tags = {
        _normalize_topic(tag)
        for tag in (space.get("tags") or [])
        if _normalize_topic(tag)
    }
    shared_tag_count = len(space_tags & viewer_tags)
    if shared_tag_count:
        score += min(12, shared_tag_count * 4)
        reasons.append(_reason("shared_topics"))

    purpose = str(space.get("purpose") or "community")
    if purpose in viewer_purposes and membership_status != "active":
        score += 4
        reasons.append(_reason("familiar_format"))

    if purpose in INTENT_PURPOSES.get(social_intent or "", set()):
        score += 6
        reasons.append(_reason("intent_match"))

    created_at = _parse_created_at(space.get("created_at"))
    if created_at and created_at >= now - timedelta(days=14):
        score += 3
        reasons.append(_reason("new_space"))

    member_count = max(0, int(space.get("member_count") or 0))
    score += min(6.0, math.log2(member_count + 1))

    # Score stays server-only. Client receives a compact explanation instead.
    return score, reasons[:3]


def _diversify(items: list[dict]) -> list[dict]:
    remaining = list(items)
    result: list[dict] = []

    while remaining:
        chosen_index = 0
        if len(result) >= 2:
            last_purpose = result[-1]["space"].get("purpose")
            previous_purpose = result[-2]["space"].get("purpose")
            if last_purpose == previous_purpose:
                best_score = remaining[0]["_score"]
                for index, candidate in enumerate(remaining[1:8], start=1):
                    if candidate["space"].get("purpose") == last_purpose:
                        continue
                    if best_score - candidate["_score"] <= 8:
                        chosen_index = index
                        break
        result.append(remaining.pop(chosen_index))

    return result


async def discover_spaces(
    db: AsyncSession,
    viewer_uid: UUID | str,
    *,
    query: str | None = None,
    purpose: str | None = None,
    tag: str | None = None,
    limit: int = 30,
    offset: int = 0,
) -> list[dict]:
    viewer = UUID(str(viewer_uid))

    # Eligibility is resolved first by the canonical Space service. Ranking never
    # makes an otherwise private/inactive Space visible.
    candidate_spaces = await list_spaces(
        db,
        viewer_uid=viewer,
        query=query,
        purpose=purpose,
        tag=tag,
        limit=DISCOVERY_POOL_LIMIT,
        offset=0,
    )

    blocked_accounts = await _blocked_account_uids(db, viewer)
    eligible: list[dict] = []
    for space in candidate_spaces:
        membership = space.get("viewer_membership") or {}
        owner_uid = space.get("owner_uid")
        try:
            owner_account_uid = UUID(str(owner_uid)) if owner_uid else None
        except (TypeError, ValueError):
            owner_account_uid = None

        # Block suppresses owner-led public discovery for non-members. Existing
        # membership remains a Space/community relation and is not silently removed.
        if (
            owner_account_uid in blocked_accounts
            and membership.get("status") not in {"active", "pending"}
        ):
            continue
        eligible.append(space)

    room_uids = [UUID(str(space["uid"])) for space in eligible]
    now = datetime.utcnow()
    recent_by_room = await _recent_message_counts(db, room_uids, now)
    upcoming_by_room = await _upcoming_by_room(db, room_uids, now)
    viewer_purposes, viewer_tags, social_intent = await _viewer_context(db, viewer)

    ranked: list[dict] = []
    for space in eligible:
        room_uid = UUID(str(space["uid"]))
        upcoming = upcoming_by_room.get(room_uid)
        score, reasons = _score_space(
            space,
            recent_messages=recent_by_room.get(room_uid, 0),
            upcoming=upcoming,
            viewer_purposes=viewer_purposes,
            viewer_tags=viewer_tags,
            social_intent=social_intent,
            now=now,
        )

        discovery = {
            "algorithm": DISCOVERY_ALGORITHM,
            "reasons": reasons,
            "upcoming": {
                "kind": upcoming["kind"],
                "title": upcoming["title"],
                "starts_at": upcoming["starts_at"].isoformat(),
            }
            if upcoming
            else None,
        }
        ranked.append({"space": {**space, "discovery": discovery}, "_score": score})

    ranked.sort(
        key=lambda item: (
            -item["_score"],
            str(item["space"].get("name") or "").casefold(),
            str(item["space"].get("uid") or ""),
        )
    )
    diversified = _diversify(ranked)
    page = diversified[offset : offset + limit]
    return [item["space"] for item in page]
