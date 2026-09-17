from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import Account, AccountRole, PlatformPermission, RolePermission
from components.moderation.model import (
    PlatformRestriction,
    PlatformRestrictionAppeal,
    PlatformRestrictionAuditEvent,
    TrustSafetyAuditEvent,
)
from components.moderation.policy import (
    ACCOUNT_ACCESS_PERMISSION,
    PERMANENT_RESTRICTION_PERMISSION,
    PLATFORM_MODERATION_PERMISSION,
    account_has_platform_permission,
    effective_authority_level,
    effective_restriction_status,
    resolve_account,
)
from components.moderation.schemas import (
    PlatformRestrictionAppealCreateRequest,
    PlatformRestrictionAppealResolveRequest,
)
from components.notification.model import UserNotification


APPEAL_OPEN_STATUS = "pending"
APPEAL_FINAL_STATUSES = frozenset({"upheld", "overturned"})


def appeal_projection(
    appeal: PlatformRestrictionAppeal,
    restriction: PlatformRestriction,
    *,
    include_reviewer: bool = False,
) -> dict:
    item = {
        "uid": str(appeal.uid),
        "restriction_uid": str(appeal.restriction_uid),
        "status": appeal.status,
        "body": appeal.body,
        "resolution": appeal.resolution,
        "created_at": appeal.created_at.isoformat(),
        "resolved_at": appeal.resolved_at.isoformat() if appeal.resolved_at else None,
        "restriction": {
            "uid": str(restriction.uid),
            "capability": restriction.capability,
            "scope_type": restriction.scope_type,
            "scope_uid": str(restriction.scope_uid) if restriction.scope_uid else None,
            "public_explanation": restriction.public_explanation,
            "status": effective_restriction_status(restriction),
            "expires_at": restriction.expires_at.isoformat() if restriction.expires_at else None,
        },
    }
    if include_reviewer:
        item["appellant_account_uid"] = (
            str(appeal.appellant_account_uid) if appeal.appellant_account_uid else None
        )
        item["reviewer_account_uid"] = (
            str(appeal.reviewer_account_uid) if appeal.reviewer_account_uid else None
        )
        item["restriction"]["actor_account_uid"] = (
            str(restriction.actor_account_uid) if restriction.actor_account_uid else None
        )
        item["restriction"]["actor_authority_level"] = restriction.actor_authority_level
        item["restriction"]["target_authority_level"] = restriction.target_authority_level
    return item


async def _audit_restriction(
    db: AsyncSession,
    restriction_uid: UUID,
    actor_account_uid: UUID | None,
    event_type: str,
    note: str | None = None,
) -> None:
    db.add(
        PlatformRestrictionAuditEvent(
            restriction_uid=restriction_uid,
            actor_account_uid=actor_account_uid,
            event_type=event_type,
            note=(note or "")[:2000] or None,
        )
    )


async def _load_restriction(db: AsyncSession, restriction_uid: UUID) -> PlatformRestriction:
    restriction = await db.get(PlatformRestriction, restriction_uid)
    if not restriction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "platform_restriction_not_found"},
        )
    return restriction


async def create_platform_restriction_appeal(
    db: AsyncSession,
    appellant_subject_uid: UUID | str,
    restriction_uid: UUID,
    payload: PlatformRestrictionAppealCreateRequest,
) -> dict:
    appellant = await resolve_account(db, appellant_subject_uid)
    restriction = await _load_restriction(db, restriction_uid)
    if restriction.target_account_uid != appellant.uid:
        # Do not reveal moderation records belonging to another Account.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "platform_restriction_not_found"},
        )
    if restriction.status == "revoked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "platform_restriction_already_revoked"},
        )

    existing = await db.execute(
        select(PlatformRestrictionAppeal.uid)
        .where(
            PlatformRestrictionAppeal.restriction_uid == restriction.uid,
            PlatformRestrictionAppeal.appellant_account_uid == appellant.uid,
        )
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "platform_restriction_appeal_exists"},
        )

    appeal = PlatformRestrictionAppeal(
        restriction_uid=restriction.uid,
        appellant_account_uid=appellant.uid,
        body=payload.body,
        status=APPEAL_OPEN_STATUS,
    )
    db.add(appeal)
    await db.flush()
    await _audit_restriction(
        db,
        restriction.uid,
        appellant.uid,
        "appeal_created",
        note=f"appeal_uid={appeal.uid}",
    )
    if restriction.report_uid:
        db.add(
            TrustSafetyAuditEvent(
                report_uid=restriction.report_uid,
                actor_account_uid=appellant.uid,
                event_type="restriction_appeal_created",
                previous_status=None,
                next_status=None,
                note=f"restriction_uid={restriction.uid}; appeal_uid={appeal.uid}",
            )
        )
    await db.commit()
    await db.refresh(appeal)
    return appeal_projection(appeal, restriction)


async def list_my_platform_restriction_appeals(
    db: AsyncSession,
    appellant_subject_uid: UUID | str,
    *,
    limit: int = 100,
) -> list[dict]:
    appellant = await resolve_account(db, appellant_subject_uid)
    result = await db.execute(
        select(PlatformRestrictionAppeal, PlatformRestriction)
        .join(
            PlatformRestriction,
            PlatformRestriction.uid == PlatformRestrictionAppeal.restriction_uid,
        )
        .where(PlatformRestrictionAppeal.appellant_account_uid == appellant.uid)
        .order_by(PlatformRestrictionAppeal.created_at.desc())
        .limit(limit)
    )
    return [appeal_projection(appeal, restriction) for appeal, restriction in result.all()]


async def list_platform_restriction_appeals(
    db: AsyncSession,
    *,
    appeal_status: str | None = APPEAL_OPEN_STATUS,
    reviewer_account_uid: UUID | None = None,
    only_unassigned: bool = False,
    limit: int = 100,
) -> list[dict]:
    filters = []
    if appeal_status:
        filters.append(PlatformRestrictionAppeal.status == appeal_status)
    if reviewer_account_uid:
        filters.append(PlatformRestrictionAppeal.reviewer_account_uid == reviewer_account_uid)
    elif only_unassigned:
        filters.append(PlatformRestrictionAppeal.reviewer_account_uid.is_(None))

    result = await db.execute(
        select(PlatformRestrictionAppeal, PlatformRestriction)
        .join(
            PlatformRestriction,
            PlatformRestriction.uid == PlatformRestrictionAppeal.restriction_uid,
        )
        .where(*filters)
        .order_by(PlatformRestrictionAppeal.created_at.asc())
        .limit(limit)
    )
    return [
        appeal_projection(appeal, restriction, include_reviewer=True)
        for appeal, restriction in result.all()
    ]


async def _reviewer_is_eligible(
    db: AsyncSession,
    reviewer: Account,
    restriction: PlatformRestriction,
) -> None:
    if not await account_has_platform_permission(db, reviewer.uid, PLATFORM_MODERATION_PERMISSION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "platform_moderation_permission_required"},
        )
    reviewer_level = await effective_authority_level(db, reviewer.uid)
    if reviewer_level < restriction.actor_authority_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_type": "appeal_reviewer_authority_insufficient",
                "required_authority_level": restriction.actor_authority_level,
                "reviewer_authority_level": reviewer_level,
            },
        )
    if restriction.expires_at is None and not await account_has_platform_permission(
        db,
        reviewer.uid,
        PERMANENT_RESTRICTION_PERMISSION,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "appeal_permanent_permission_required"},
        )
    if restriction.capability == "account.access" and not await account_has_platform_permission(
        db,
        reviewer.uid,
        ACCOUNT_ACCESS_PERMISSION,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "appeal_account_access_permission_required"},
        )


async def _independent_reviewer_available(
    db: AsyncSession,
    restriction: PlatformRestriction,
    *,
    exclude_account_uid: UUID,
) -> bool:
    result = await db.execute(
        select(AccountRole.account_uid)
        .join(RolePermission, RolePermission.role_id == AccountRole.role_id)
        .join(PlatformPermission, PlatformPermission.id == RolePermission.permission_id)
        .join(Account, Account.uid == AccountRole.account_uid)
        .where(
            PlatformPermission.name == PLATFORM_MODERATION_PERMISSION,
            Account.status == "active",
            Account.deleted_at.is_(None),
            AccountRole.account_uid != exclude_account_uid,
        )
        .distinct()
    )
    for candidate_uid in result.scalars().all():
        if candidate_uid == restriction.target_account_uid:
            continue
        candidate = await db.get(Account, candidate_uid)
        if not candidate:
            continue
        try:
            await _reviewer_is_eligible(db, candidate, restriction)
        except HTTPException:
            continue
        return True
    return False


async def _assert_independent_reviewer(
    db: AsyncSession,
    reviewer: Account,
    appeal: PlatformRestrictionAppeal,
    restriction: PlatformRestriction,
) -> None:
    if appeal.appellant_account_uid == reviewer.uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "appeal_self_review_forbidden"},
        )
    if restriction.actor_account_uid != reviewer.uid:
        return
    if await _independent_reviewer_available(
        db,
        restriction,
        exclude_account_uid=reviewer.uid,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "independent_appeal_reviewer_required"},
        )


async def claim_platform_restriction_appeal(
    db: AsyncSession,
    appeal_uid: UUID,
    reviewer_account_uid: UUID,
) -> dict:
    reviewer = await resolve_account(db, reviewer_account_uid)
    result = await db.execute(
        select(PlatformRestrictionAppeal)
        .where(PlatformRestrictionAppeal.uid == appeal_uid)
        .with_for_update()
    )
    appeal = result.scalar_one_or_none()
    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "platform_restriction_appeal_not_found"},
        )
    if appeal.status != APPEAL_OPEN_STATUS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "platform_restriction_appeal_closed"},
        )
    restriction = await _load_restriction(db, appeal.restriction_uid)
    await _reviewer_is_eligible(db, reviewer, restriction)
    await _assert_independent_reviewer(db, reviewer, appeal, restriction)

    if appeal.reviewer_account_uid and appeal.reviewer_account_uid != reviewer.uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "platform_restriction_appeal_already_claimed"},
        )
    if appeal.reviewer_account_uid == reviewer.uid:
        await db.rollback()
        return appeal_projection(appeal, restriction, include_reviewer=True)

    appeal.reviewer_account_uid = reviewer.uid
    appeal.updated_at = datetime.utcnow()
    await _audit_restriction(
        db,
        restriction.uid,
        reviewer.uid,
        "appeal_claimed",
        note=f"appeal_uid={appeal.uid}",
    )
    await db.commit()
    await db.refresh(appeal)
    return appeal_projection(appeal, restriction, include_reviewer=True)


async def release_platform_restriction_appeal(
    db: AsyncSession,
    appeal_uid: UUID,
    reviewer_account_uid: UUID,
) -> dict:
    reviewer = await resolve_account(db, reviewer_account_uid)
    result = await db.execute(
        select(PlatformRestrictionAppeal)
        .where(PlatformRestrictionAppeal.uid == appeal_uid)
        .with_for_update()
    )
    appeal = result.scalar_one_or_none()
    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "platform_restriction_appeal_not_found"},
        )
    if appeal.status != APPEAL_OPEN_STATUS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "platform_restriction_appeal_closed"},
        )
    if appeal.reviewer_account_uid != reviewer.uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "platform_restriction_appeal_not_owned"},
        )
    restriction = await _load_restriction(db, appeal.restriction_uid)
    appeal.reviewer_account_uid = None
    appeal.updated_at = datetime.utcnow()
    await _audit_restriction(
        db,
        restriction.uid,
        reviewer.uid,
        "appeal_released",
        note=f"appeal_uid={appeal.uid}",
    )
    await db.commit()
    await db.refresh(appeal)
    return appeal_projection(appeal, restriction, include_reviewer=True)


async def resolve_platform_restriction_appeal(
    db: AsyncSession,
    appeal_uid: UUID,
    reviewer_account_uid: UUID,
    payload: PlatformRestrictionAppealResolveRequest,
) -> dict:
    reviewer = await resolve_account(db, reviewer_account_uid)
    result = await db.execute(
        select(PlatformRestrictionAppeal)
        .where(PlatformRestrictionAppeal.uid == appeal_uid)
        .with_for_update()
    )
    appeal = result.scalar_one_or_none()
    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "platform_restriction_appeal_not_found"},
        )
    if appeal.status != APPEAL_OPEN_STATUS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "platform_restriction_appeal_closed"},
        )
    if appeal.reviewer_account_uid != reviewer.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "platform_restriction_appeal_claim_required"},
        )

    restriction_result = await db.execute(
        select(PlatformRestriction)
        .where(PlatformRestriction.uid == appeal.restriction_uid)
        .with_for_update()
    )
    restriction = restriction_result.scalar_one()
    await _reviewer_is_eligible(db, reviewer, restriction)
    await _assert_independent_reviewer(db, reviewer, appeal, restriction)

    now = datetime.utcnow()
    appeal.status = "overturned" if payload.decision == "overturn" else "upheld"
    appeal.resolution = payload.resolution
    appeal.resolved_at = now
    appeal.updated_at = now

    if payload.decision == "overturn" and effective_restriction_status(restriction, now) == "active":
        restriction.status = "revoked"
        restriction.revoked_at = now
        restriction.revoked_by_account_uid = reviewer.uid
        restriction.updated_at = now
        await _audit_restriction(
            db,
            restriction.uid,
            reviewer.uid,
            "restriction_revoked_on_appeal",
            note=payload.resolution,
        )
    else:
        await _audit_restriction(
            db,
            restriction.uid,
            reviewer.uid,
            f"appeal_{appeal.status}",
            note=payload.resolution,
        )

    if restriction.report_uid:
        db.add(
            TrustSafetyAuditEvent(
                report_uid=restriction.report_uid,
                actor_account_uid=reviewer.uid,
                event_type="restriction_appeal_resolved",
                previous_status=None,
                next_status=None,
                note=(
                    f"restriction_uid={restriction.uid}; appeal_uid={appeal.uid}; "
                    f"decision={payload.decision}"
                ),
            )
        )

    if appeal.appellant_account_uid:
        db.add(
            UserNotification(
                account_uid=appeal.appellant_account_uid,
                kind="platform_restriction_appeal",
                dedupe_key=f"platform-restriction-appeal:{appeal.uid}:{appeal.status}",
                title=(
                    "Ограничение отменено по апелляции"
                    if appeal.status == "overturned"
                    else "Апелляция рассмотрена"
                ),
                body=payload.resolution[:500],
                context_room_uid=(
                    restriction.scope_uid if restriction.scope_type == "space" else None
                ),
            )
        )

    await db.commit()
    await db.refresh(appeal)
    return appeal_projection(appeal, restriction, include_reviewer=True)
