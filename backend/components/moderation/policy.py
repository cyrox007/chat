from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.identity.model import (
    Account,
    AccountRole,
    PlatformPermission,
    PlatformRole,
    RolePermission,
)
from components.moderation.model import (
    PlatformRestriction,
    PlatformRestrictionAuditEvent,
    TrustSafetyAuditEvent,
    TrustSafetyReport,
)
from components.moderation.schemas import (
    PlatformRestrictionCreateRequest,
    PlatformRestrictionRevokeRequest,
)
from components.notification.model import UserNotification
from components.room.model import Room


PLATFORM_MODERATION_PERMISSION = "moderation.platform.manage"
PERMANENT_RESTRICTION_PERMISSION = "moderation.platform.permanent"
ACCOUNT_ACCESS_PERMISSION = "moderation.platform.account_access"

# These are contract-level capabilities. Runtime enforcement is wired into domain
# services in the next implementation slice; a DB row alone must never be treated
# as a working sanction until the corresponding server-side guard is present.
PLATFORM_CAPABILITIES = frozenset(
    {
        "messenger.send",
        "space.chat.send",
        "media.upload",
        "space.create",
        "space.join",
        "invitation.send",
        "profile.edit",
        "discovery.publish",
        "account.access",
    }
)


def effective_restriction_status(restriction: PlatformRestriction, now: datetime | None = None) -> str:
    now = now or datetime.utcnow()
    if restriction.status == "active" and restriction.expires_at and restriction.expires_at <= now:
        return "expired"
    return restriction.status


async def resolve_account(db: AsyncSession, subject_uid: UUID | str) -> Account:
    uid = UUID(str(subject_uid))
    result = await db.execute(
        select(Account)
        .where(
            or_(Account.uid == uid, Account.legacy_user_uid == uid),
            Account.deleted_at.is_(None),
        )
        .limit(1)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "moderation_account_not_found"},
        )
    return account


async def effective_authority_level(db: AsyncSession, account_uid: UUID) -> int:
    result = await db.execute(
        select(func.max(PlatformRole.authority_level))
        .join(AccountRole, AccountRole.role_id == PlatformRole.id)
        .where(AccountRole.account_uid == account_uid)
    )
    return int(result.scalar_one_or_none() or 0)


async def account_has_platform_permission(
    db: AsyncSession,
    account_uid: UUID,
    permission_name: str,
) -> bool:
    result = await db.execute(
        select(PlatformPermission.id)
        .join(RolePermission, RolePermission.permission_id == PlatformPermission.id)
        .join(AccountRole, AccountRole.role_id == RolePermission.role_id)
        .where(
            AccountRole.account_uid == account_uid,
            PlatformPermission.name == permission_name,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def assert_higher_authority(
    db: AsyncSession,
    actor_account_uid: UUID,
    target_account_uid: UUID,
) -> tuple[int, int]:
    if actor_account_uid == target_account_uid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "moderation_self_action_forbidden"},
        )
    actor_level = await effective_authority_level(db, actor_account_uid)
    target_level = await effective_authority_level(db, target_account_uid)
    if actor_level <= target_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_type": "moderation_authority_insufficient",
                "actor_authority_level": actor_level,
                "target_authority_level": target_level,
            },
        )
    return actor_level, target_level


def restriction_projection(restriction: PlatformRestriction) -> dict:
    return {
        "uid": str(restriction.uid),
        "report_uid": str(restriction.report_uid) if restriction.report_uid else None,
        "actor_account_uid": (
            str(restriction.actor_account_uid) if restriction.actor_account_uid else None
        ),
        "target_account_uid": str(restriction.target_account_uid),
        "capability": restriction.capability,
        "scope_type": restriction.scope_type,
        "scope_uid": str(restriction.scope_uid) if restriction.scope_uid else None,
        "reason_code": restriction.reason_code,
        "public_explanation": restriction.public_explanation,
        "origin": restriction.origin,
        "status": effective_restriction_status(restriction),
        "starts_at": restriction.starts_at.isoformat(),
        "expires_at": restriction.expires_at.isoformat() if restriction.expires_at else None,
        "revoked_at": restriction.revoked_at.isoformat() if restriction.revoked_at else None,
        "created_at": restriction.created_at.isoformat(),
    }


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


async def issue_platform_restriction(
    db: AsyncSession,
    actor_account_uid: UUID,
    payload: PlatformRestrictionCreateRequest,
) -> dict:
    actor = await resolve_account(db, actor_account_uid)
    target = await resolve_account(db, payload.target_account_uid)

    if not await account_has_platform_permission(db, actor.uid, PLATFORM_MODERATION_PERMISSION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "platform_moderation_permission_required"},
        )

    actor_level, target_level = await assert_higher_authority(db, actor.uid, target.uid)

    if payload.duration_minutes is None and not await account_has_platform_permission(
        db,
        actor.uid,
        PERMANENT_RESTRICTION_PERMISSION,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "permanent_restriction_permission_required"},
        )

    if payload.capability == "account.access" and not await account_has_platform_permission(
        db,
        actor.uid,
        ACCOUNT_ACCESS_PERMISSION,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "account_access_permission_required"},
        )

    if payload.scope_type == "space":
        room_result = await db.execute(select(Room.uid).where(Room.uid == payload.scope_uid).limit(1))
        if room_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "restriction_scope_not_found"},
            )

    report = None
    if payload.report_uid:
        report = await db.get(TrustSafetyReport, payload.report_uid)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "trust_safety_report_not_found"},
            )
        if report.target_account_uid != target.uid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error_type": "restriction_report_target_mismatch"},
            )
        if report.assigned_to_account_uid != actor.uid or report.status not in {"in_review", "escalated"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_type": "trust_safety_claim_required"},
            )

    now = datetime.utcnow()
    expires_at = (
        now + timedelta(minutes=payload.duration_minutes)
        if payload.duration_minutes is not None
        else None
    )
    restriction = PlatformRestriction(
        report_uid=payload.report_uid,
        actor_account_uid=actor.uid,
        target_account_uid=target.uid,
        capability=payload.capability,
        scope_type=payload.scope_type,
        scope_uid=payload.scope_uid,
        reason_code=payload.reason_code,
        public_explanation=payload.public_explanation,
        origin="human",
        status="active",
        actor_authority_level=actor_level,
        target_authority_level=target_level,
        starts_at=now,
        expires_at=expires_at,
    )
    db.add(restriction)
    await db.flush()
    await _audit_restriction(
        db,
        restriction.uid,
        actor.uid,
        "restriction_issued",
        note=f"{payload.capability}: {payload.reason_code}",
    )

    if report:
        db.add(
            TrustSafetyAuditEvent(
                report_uid=report.uid,
                actor_account_uid=actor.uid,
                event_type="restriction_issued",
                previous_status=report.status,
                next_status=report.status,
                note=f"{payload.capability}: {payload.reason_code}",
            )
        )

    db.add(
        UserNotification(
            account_uid=target.uid,
            kind="platform_restriction",
            dedupe_key=f"platform-restriction:{restriction.uid}:issued",
            title="Ограничение возможностей",
            body=payload.public_explanation[:500],
            context_room_uid=payload.scope_uid if payload.scope_type == "space" else None,
        )
    )
    await db.commit()
    await db.refresh(restriction)
    return restriction_projection(restriction)


async def revoke_platform_restriction(
    db: AsyncSession,
    actor_account_uid: UUID,
    restriction_uid: UUID,
    payload: PlatformRestrictionRevokeRequest,
) -> dict:
    actor = await resolve_account(db, actor_account_uid)
    result = await db.execute(
        select(PlatformRestriction)
        .where(PlatformRestriction.uid == restriction_uid)
        .with_for_update()
    )
    restriction = result.scalar_one_or_none()
    if not restriction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_type": "platform_restriction_not_found"},
        )
    if effective_restriction_status(restriction) != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "platform_restriction_not_active"},
        )
    if not await account_has_platform_permission(db, actor.uid, PLATFORM_MODERATION_PERMISSION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_type": "platform_moderation_permission_required"},
        )
    await assert_higher_authority(db, actor.uid, restriction.target_account_uid)

    now = datetime.utcnow()
    restriction.status = "revoked"
    restriction.revoked_at = now
    restriction.revoked_by_account_uid = actor.uid
    restriction.updated_at = now
    await _audit_restriction(
        db,
        restriction.uid,
        actor.uid,
        "restriction_revoked",
        note=payload.reason,
    )
    db.add(
        UserNotification(
            account_uid=restriction.target_account_uid,
            kind="platform_restriction_revoked",
            dedupe_key=f"platform-restriction:{restriction.uid}:revoked",
            title="Ограничение снято",
            body=payload.reason[:500],
            context_room_uid=(
                restriction.scope_uid if restriction.scope_type == "space" else None
            ),
        )
    )
    await db.commit()
    await db.refresh(restriction)
    return restriction_projection(restriction)


async def list_account_restrictions(
    db: AsyncSession,
    account_uid: UUID,
    *,
    include_inactive: bool = True,
    limit: int = 100,
) -> list[dict]:
    filters = [PlatformRestriction.target_account_uid == account_uid]
    if not include_inactive:
        now = datetime.utcnow()
        filters.extend(
            [
                PlatformRestriction.status == "active",
                PlatformRestriction.starts_at <= now,
                or_(PlatformRestriction.expires_at.is_(None), PlatformRestriction.expires_at > now),
            ]
        )
    result = await db.execute(
        select(PlatformRestriction)
        .where(*filters)
        .order_by(PlatformRestriction.created_at.desc())
        .limit(limit)
    )
    return [restriction_projection(item) for item in result.scalars().all()]


async def active_restriction_for_subject(
    db: AsyncSession,
    subject_uid: UUID | str,
    capability: str,
    *,
    scope_type: str = "platform",
    scope_uid: UUID | None = None,
) -> PlatformRestriction | None:
    if capability not in PLATFORM_CAPABILITIES:
        raise ValueError(f"Unknown moderation capability: {capability}")
    account = await resolve_account(db, subject_uid)
    now = datetime.utcnow()

    scope_filter = PlatformRestriction.scope_type == "platform"
    if scope_type == "space" and scope_uid is not None:
        scope_filter = or_(
            PlatformRestriction.scope_type == "platform",
            and_(
                PlatformRestriction.scope_type == "space",
                PlatformRestriction.scope_uid == scope_uid,
            ),
        )

    result = await db.execute(
        select(PlatformRestriction)
        .where(
            PlatformRestriction.target_account_uid == account.uid,
            PlatformRestriction.status == "active",
            PlatformRestriction.starts_at <= now,
            or_(PlatformRestriction.expires_at.is_(None), PlatformRestriction.expires_at > now),
            PlatformRestriction.capability.in_([capability, "account.access"]),
            scope_filter,
        )
        .order_by(PlatformRestriction.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def assert_allowed(
    db: AsyncSession,
    subject_uid: UUID | str,
    capability: str,
    *,
    scope_type: str = "platform",
    scope_uid: UUID | None = None,
) -> None:
    restriction = await active_restriction_for_subject(
        db,
        subject_uid,
        capability,
        scope_type=scope_type,
        scope_uid=scope_uid,
    )
    if restriction is None:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error_type": "capability_restricted",
            "requested_capability": capability,
            "restriction_capability": restriction.capability,
            "restriction_uid": str(restriction.uid),
            "scope_type": restriction.scope_type,
            "scope_uid": str(restriction.scope_uid) if restriction.scope_uid else None,
            "expires_at": restriction.expires_at.isoformat() if restriction.expires_at else None,
            "explanation": restriction.public_explanation,
        },
    )
