from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Account, Persona
from components.message.model import Message, PrivateMessage
from components.moderation.model import TrustSafetyAuditEvent, TrustSafetyReport
from components.moderation.schemas import TrustSafetyDecisionRequest, TrustSafetyReportCreateRequest
from components.notification.model import UserNotification
from components.room.model import Room
from components.space.membership_service import _require_active_member
from components.space.service import _get_account


OPEN_TRUST_SAFETY_STATUSES = ("triage", "in_review", "escalated")
TRUST_SAFETY_REPORT_WINDOW_MINUTES = 10
TRUST_SAFETY_REPORT_LIMIT = 10


_HIGH_PRIORITY_CATEGORIES = {"violence", "self_harm", "minor_safety"}
_LOW_PRIORITY_CATEGORIES = {"spam", "other"}


def trust_safety_priority(category: str) -> str:
    """Server-owned queue priority; reporters cannot choose or raise it."""
    if category in _HIGH_PRIORITY_CATEGORIES:
        return "high"
    if category in _LOW_PRIORITY_CATEGORIES:
        return "low"
    return "normal"


async def _audit(
    db: AsyncSession,
    report_uid: UUID,
    actor_account_uid: UUID | None,
    event_type: str,
    *,
    previous_status: str | None = None,
    next_status: str | None = None,
    note: str | None = None,
) -> None:
    db.add(
        TrustSafetyAuditEvent(
            report_uid=report_uid,
            actor_account_uid=actor_account_uid,
            event_type=event_type,
            previous_status=previous_status,
            next_status=next_status,
            note=(note or "")[:2000] or None,
        )
    )


async def _primary_persona(db: AsyncSession, account_uid: UUID | None) -> dict | None:
    if account_uid is None:
        return None
    result = await db.execute(
        select(Persona)
        .where(Persona.account_uid == account_uid, Persona.is_primary.is_(True))
        .limit(1)
    )
    persona = result.scalar_one_or_none()
    return {
        "account_uid": str(account_uid),
        "persona_uid": str(persona.uid) if persona else None,
        "handle": persona.handle if persona else None,
        "display_name": persona.display_name if persona else None,
        "avatar": persona.avatar if persona else None,
    }


async def _report_projection(
    db: AsyncSession,
    report: TrustSafetyReport,
    *,
    include_description: bool = True,
    include_assignment: bool = True,
) -> dict:
    target = await _primary_persona(db, report.target_account_uid)
    item = {
        "uid": str(report.uid),
        "source_type": report.source_type,
        "source_uid": str(report.source_uid),
        "source_space_uid": str(report.source_room_uid) if report.source_room_uid else None,
        "category": report.category,
        "priority": report.priority,
        "status": report.status,
        "target": target,
        "resolution_code": report.resolution_code,
        "public_explanation": report.public_explanation,
        "created_at": report.created_at.isoformat(),
        "updated_at": report.updated_at.isoformat(),
        "resolved_at": report.resolved_at.isoformat() if report.resolved_at else None,
    }
    if include_description:
        item["description"] = report.description
    if include_assignment:
        item["assigned_to_account_uid"] = (
            str(report.assigned_to_account_uid) if report.assigned_to_account_uid else None
        )
        item["assigned_at"] = report.assigned_at.isoformat() if report.assigned_at else None
    return item


async def _account_for_legacy_user(db: AsyncSession, legacy_user_uid: UUID) -> Account:
    result = await db.execute(
        select(Account)
        .where(
            Account.legacy_user_uid == legacy_user_uid,
            Account.deleted_at.is_(None),
        )
        .limit(1)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "identity_bridge_missing"},
        )
    return account


async def _resolve_report_source(
    db: AsyncSession,
    reporter: Account,
    payload: TrustSafetyReportCreateRequest,
) -> tuple[Account, UUID | None]:
    if payload.source_type == "persona":
        persona = await db.get(Persona, payload.source_uid)
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "trust_safety_source_not_found"},
            )
        target = await db.get(Account, persona.account_uid)
        if not target or target.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "trust_safety_target_not_found"},
            )
        return target, None

    if payload.source_type == "messenger_message":
        result = await db.execute(
            select(PrivateMessage).where(PrivateMessage.uid == payload.source_uid).limit(1)
        )
        message = result.scalar_one_or_none()
        if not message or reporter.legacy_user_uid != message.receiver_uid:
            # Do not reveal whether an arbitrary private message exists.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "trust_safety_source_not_found"},
            )
        target = await _account_for_legacy_user(db, message.sender_uid)
        return target, None

    if payload.source_type == "space_message":
        message = await db.get(Message, payload.source_uid)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "trust_safety_source_not_found"},
            )
        room_result = await db.execute(select(Room).where(Room.uid == message.room_uid).limit(1))
        room = room_result.scalar_one_or_none()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "trust_safety_source_not_found"},
            )
        try:
            await _require_active_member(db, room, reporter.uid)
        except HTTPException as exc:
            # Membership is part of source authorization; keep existence private.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "trust_safety_source_not_found"},
            ) from exc
        target = await _account_for_legacy_user(db, message.author_uid)
        return target, room.uid

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"error_type": "unsupported_trust_safety_source"},
    )


async def create_trust_safety_report(
    db: AsyncSession,
    viewer_uid: UUID | str,
    payload: TrustSafetyReportCreateRequest,
) -> dict:
    reporter = await _get_account(db, viewer_uid)
    target, source_room_uid = await _resolve_report_source(db, reporter, payload)
    if target.uid == reporter.uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "cannot_report_self"},
        )

    existing_result = await db.execute(
        select(TrustSafetyReport)
        .where(
            TrustSafetyReport.reporter_account_uid == reporter.uid,
            TrustSafetyReport.source_type == payload.source_type,
            TrustSafetyReport.source_uid == payload.source_uid,
            TrustSafetyReport.category == payload.category,
            TrustSafetyReport.status.in_(OPEN_TRUST_SAFETY_STATUSES),
        )
        .order_by(TrustSafetyReport.created_at.desc())
        .limit(1)
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        await _audit(db, existing.uid, reporter.uid, "duplicate_submission")
        await db.commit()
        result = await _report_projection(db, existing, include_assignment=False)
        result["deduplicated"] = True
        return result

    cutoff = datetime.utcnow() - timedelta(minutes=TRUST_SAFETY_REPORT_WINDOW_MINUTES)
    recent_count = int(
        (
            await db.execute(
                select(func.count(TrustSafetyReport.uid)).where(
                    TrustSafetyReport.reporter_account_uid == reporter.uid,
                    TrustSafetyReport.created_at >= cutoff,
                )
            )
        ).scalar_one()
        or 0
    )
    if recent_count >= TRUST_SAFETY_REPORT_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error_type": "trust_safety_report_rate_limited"},
        )

    report = TrustSafetyReport(
        reporter_account_uid=reporter.uid,
        target_account_uid=target.uid,
        source_type=payload.source_type,
        source_uid=payload.source_uid,
        source_room_uid=source_room_uid,
        category=payload.category,
        priority=trust_safety_priority(payload.category),
        description=payload.description,
        status="triage",
    )
    db.add(report)
    await db.flush()
    await _audit(
        db,
        report.uid,
        reporter.uid,
        "report_created",
        next_status="triage",
    )
    await db.commit()
    await db.refresh(report)
    result = await _report_projection(db, report, include_assignment=False)
    result["deduplicated"] = False
    return result


async def list_my_trust_safety_reports(
    db: AsyncSession,
    viewer_uid: UUID | str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    viewer = await _get_account(db, viewer_uid)
    filters = (TrustSafetyReport.reporter_account_uid == viewer.uid,)
    total = int(
        (await db.execute(select(func.count(TrustSafetyReport.uid)).where(*filters))).scalar_one()
        or 0
    )
    result = await db.execute(
        select(TrustSafetyReport)
        .where(*filters)
        .order_by(TrustSafetyReport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = []
    for report in result.scalars().all():
        item = await _report_projection(db, report, include_assignment=False)
        # Queue priority and moderator assignment are internal operational state.
        item.pop("priority", None)
        items.append(item)
    return items, total


async def list_trust_safety_queue(
    db: AsyncSession,
    *,
    queue_status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    assigned_to_account_uid: UUID | None = None,
    only_unassigned: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    filters = []
    if queue_status:
        filters.append(TrustSafetyReport.status == queue_status)
    else:
        filters.append(TrustSafetyReport.status.in_(OPEN_TRUST_SAFETY_STATUSES))
    if priority:
        filters.append(TrustSafetyReport.priority == priority)
    if category:
        filters.append(TrustSafetyReport.category == category)
    if assigned_to_account_uid:
        filters.append(TrustSafetyReport.assigned_to_account_uid == assigned_to_account_uid)
    elif only_unassigned:
        filters.append(TrustSafetyReport.assigned_to_account_uid.is_(None))

    total = int(
        (await db.execute(select(func.count(TrustSafetyReport.uid)).where(*filters))).scalar_one()
        or 0
    )
    result = await db.execute(
        select(TrustSafetyReport)
        .where(*filters)
        .order_by(
            # deterministic priority order without a database enum
            TrustSafetyReport.priority.asc(),
            TrustSafetyReport.created_at.asc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return [await _report_projection(db, report) for report in result.scalars().all()], total


async def _locked_report(db: AsyncSession, report_uid: UUID) -> TrustSafetyReport:
    result = await db.execute(
        select(TrustSafetyReport)
        .where(TrustSafetyReport.uid == report_uid)
        .with_for_update()
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "trust_safety_report_not_found"},
        )
    return report


async def claim_trust_safety_report(
    db: AsyncSession,
    report_uid: UUID,
    moderator_account_uid: UUID,
) -> dict:
    report = await _locked_report(db, report_uid)
    if report.status not in OPEN_TRUST_SAFETY_STATUSES:
        raise HTTPException(status_code=409, detail={"error_type": "trust_safety_report_closed"})
    if report.assigned_to_account_uid and report.assigned_to_account_uid != moderator_account_uid:
        raise HTTPException(status_code=409, detail={"error_type": "trust_safety_report_already_claimed"})
    if report.assigned_to_account_uid == moderator_account_uid:
        await db.rollback()
        return await _report_projection(db, report)

    previous = report.status
    report.assigned_to_account_uid = moderator_account_uid
    report.assigned_at = datetime.utcnow()
    if report.status == "triage":
        report.status = "in_review"
    report.updated_at = datetime.utcnow()
    await _audit(
        db,
        report.uid,
        moderator_account_uid,
        "report_claimed",
        previous_status=previous,
        next_status=report.status,
    )
    await db.commit()
    await db.refresh(report)
    return await _report_projection(db, report)


async def release_trust_safety_report(
    db: AsyncSession,
    report_uid: UUID,
    moderator_account_uid: UUID,
) -> dict:
    report = await _locked_report(db, report_uid)
    if report.assigned_to_account_uid != moderator_account_uid:
        raise HTTPException(status_code=409, detail={"error_type": "trust_safety_report_not_owned"})
    if report.status != "in_review":
        raise HTTPException(status_code=409, detail={"error_type": "trust_safety_report_not_releasable"})

    previous = report.status
    report.assigned_to_account_uid = None
    report.assigned_at = None
    report.status = "triage"
    report.updated_at = datetime.utcnow()
    await _audit(
        db,
        report.uid,
        moderator_account_uid,
        "report_released",
        previous_status=previous,
        next_status="triage",
    )
    await db.commit()
    await db.refresh(report)
    return await _report_projection(db, report)


async def _require_claim_owner(
    db: AsyncSession,
    report_uid: UUID,
    moderator_account_uid: UUID,
) -> TrustSafetyReport:
    report = await db.get(TrustSafetyReport, report_uid)
    if not report:
        raise HTTPException(status_code=404, detail={"error_type": "trust_safety_report_not_found"})
    if report.assigned_to_account_uid != moderator_account_uid or report.status not in {"in_review", "escalated"}:
        raise HTTPException(status_code=403, detail={"error_type": "trust_safety_claim_required"})
    return report


async def trust_safety_evidence(
    db: AsyncSession,
    report_uid: UUID,
    moderator_account_uid: UUID,
) -> dict:
    report = await _require_claim_owner(db, report_uid, moderator_account_uid)
    evidence: dict

    if report.source_type == "persona":
        persona = await db.get(Persona, report.source_uid)
        if not persona:
            evidence = {"source_type": "persona", "available": False}
        else:
            evidence = {
                "source_type": "persona",
                "available": True,
                "persona": {
                    "uid": str(persona.uid),
                    "handle": persona.handle,
                    "display_name": persona.display_name,
                    "avatar": persona.avatar,
                    "bio": persona.bio,
                    "social_intent": persona.social_intent,
                },
            }
    elif report.source_type == "messenger_message":
        result = await db.execute(
            select(PrivateMessage).where(PrivateMessage.uid == report.source_uid).limit(1)
        )
        message = result.scalar_one_or_none()
        evidence = {
            "source_type": "messenger_message",
            "available": bool(message),
            "message": (
                {
                    "uid": str(message.uid),
                    "content_type": message.content_type,
                    "content": message.text,
                    "media_metadata": message.media_metadata,
                    "created_at": message.created_at.isoformat(),
                }
                if message
                else None
            ),
            "context_policy": "reported_message_only",
        }
    elif report.source_type == "space_message":
        message = await db.get(Message, report.source_uid)
        evidence = {
            "source_type": "space_message",
            "available": bool(message),
            "message": (
                {
                    "uid": str(message.uid),
                    "content_type": message.content_type,
                    "content": message.text,
                    "media_metadata": message.media_metadata,
                    "created_at": message.created_at.isoformat(),
                    "space_uid": str(message.room_uid),
                }
                if message
                else None
            ),
            "context_policy": "reported_message_only",
        }
    else:
        evidence = {"source_type": report.source_type, "available": False}

    await _audit(db, report.uid, moderator_account_uid, "evidence_viewed")
    await db.commit()
    return evidence


async def decide_trust_safety_report(
    db: AsyncSession,
    report_uid: UUID,
    moderator_account_uid: UUID,
    payload: TrustSafetyDecisionRequest,
) -> dict:
    report = await _locked_report(db, report_uid)
    if report.assigned_to_account_uid != moderator_account_uid:
        raise HTTPException(status_code=403, detail={"error_type": "trust_safety_claim_required"})
    if report.status not in {"in_review", "escalated"}:
        raise HTTPException(status_code=409, detail={"error_type": "trust_safety_report_not_decidable"})

    previous = report.status
    now = datetime.utcnow()
    report.status = payload.status
    report.resolution_code = payload.resolution_code
    report.public_explanation = payload.public_explanation
    report.updated_at = now
    if payload.status in {"resolved", "dismissed"}:
        report.resolved_at = now
        report.assigned_to_account_uid = None
        report.assigned_at = None
    else:
        report.resolved_at = None

    await _audit(
        db,
        report.uid,
        moderator_account_uid,
        "report_decided",
        previous_status=previous,
        next_status=payload.status,
        note=f"{payload.resolution_code}: {payload.public_explanation}",
    )

    if report.reporter_account_uid:
        title = (
            "Жалоба передана на дополнительную проверку"
            if payload.status == "escalated"
            else "Жалоба рассмотрена"
        )
        db.add(
            UserNotification(
                account_uid=report.reporter_account_uid,
                kind="trust_safety_report_update",
                dedupe_key=f"trust-safety:{report.uid}:{payload.status}:{payload.resolution_code}",
                title=title,
                body=payload.public_explanation[:500],
                context_room_uid=report.source_room_uid,
            )
        )

    await db.commit()
    await db.refresh(report)
    return await _report_projection(db, report)


async def list_trust_safety_audit(
    db: AsyncSession,
    report_uid: UUID,
    *,
    limit: int = 100,
) -> list[dict]:
    report = await db.get(TrustSafetyReport, report_uid)
    if not report:
        raise HTTPException(status_code=404, detail={"error_type": "trust_safety_report_not_found"})
    result = await db.execute(
        select(TrustSafetyAuditEvent)
        .where(TrustSafetyAuditEvent.report_uid == report_uid)
        .order_by(TrustSafetyAuditEvent.created_at.asc())
        .limit(limit)
    )
    return [
        {
            "uid": str(event.uid),
            "actor_account_uid": str(event.actor_account_uid) if event.actor_account_uid else None,
            "event_type": event.event_type,
            "previous_status": event.previous_status,
            "next_status": event.next_status,
            "note": event.note,
            "created_at": event.created_at.isoformat(),
        }
        for event in result.scalars().all()
    ]
