from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.auth.permissions import require_platform_moderator, require_platform_permission
from components.identity.model import Account
from components.moderation.policy import (
    ACCOUNT_ACCESS_PERMISSION,
    APPEAL_REVIEW_PERMISSION,
    PERMANENT_RESTRICTION_PERMISSION,
    RESTRICTION_ISSUE_PERMISSION,
    RESTRICTION_REVOKE_PERMISSION,
    account_has_platform_permission,
    issue_platform_restriction,
    list_account_restrictions,
    resolve_account,
    revoke_platform_restriction,
)
from components.moderation.restriction_appeals import (
    claim_platform_restriction_appeal,
    create_platform_restriction_appeal,
    list_my_platform_restriction_appeals,
    list_platform_restriction_appeals,
    release_platform_restriction_appeal,
    resolve_platform_restriction_appeal,
)
from components.moderation.schemas import (
    PlatformRestrictionAppealCreateRequest,
    PlatformRestrictionAppealResolveRequest,
    PlatformRestrictionCreateRequest,
    PlatformRestrictionRevokeRequest,
)
from database import Database


# Only capabilities with a real server-side enforcement point may be issued.
# Expand this set in the same commit that adds the corresponding domain guard.
ENFORCEMENT_READY_CAPABILITIES: frozenset[str] = frozenset(
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


async def require_restriction_issuer(request: Request) -> Account:
    # Keep queue access separate from the power to impose a sanction.
    await require_platform_moderator(request)
    return await require_platform_permission(request, RESTRICTION_ISSUE_PERMISSION)


async def require_restriction_revoker(request: Request) -> Account:
    await require_platform_moderator(request)
    return await require_platform_permission(request, RESTRICTION_REVOKE_PERMISSION)


async def require_appeal_reviewer(request: Request) -> Account:
    await require_platform_moderator(request)
    return await require_platform_permission(request, APPEAL_REVIEW_PERMISSION)


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/trust-safety/v1", tags=["trust-safety-v1"])

    @router.post("/restrictions", status_code=status.HTTP_201_CREATED)
    async def create_restriction(
        payload: PlatformRestrictionCreateRequest,
        moderator: Account = Depends(require_restriction_issuer),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        if payload.capability not in ENFORCEMENT_READY_CAPABILITIES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_type": "moderation_capability_not_enforced_yet",
                    "capability": payload.capability,
                },
            )
        item = await issue_platform_restriction(db, moderator.uid, payload)
        return {"status": "ok", "restriction": item}

    @router.get("/me/restrictions")
    async def my_restrictions(
        include_inactive: bool = Query(default=True),
        limit: int = Query(default=100, ge=1, le=250),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        account = await resolve_account(db, current_user["user_uid"])
        items = await list_account_restrictions(
            db,
            account.uid,
            include_inactive=include_inactive,
            limit=limit,
        )
        return {"status": "ok", "restrictions": items}

    @router.get("/restrictions")
    async def target_restrictions(
        target_account_uid: UUID,
        include_inactive: bool = Query(default=True),
        limit: int = Query(default=100, ge=1, le=250),
        _: Account = Depends(require_platform_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        target = await resolve_account(db, target_account_uid)
        items = await list_account_restrictions(
            db,
            target.uid,
            include_inactive=include_inactive,
            limit=limit,
        )
        return {"status": "ok", "restrictions": items}

    @router.post("/restrictions/{restriction_uid}/revoke")
    async def revoke_restriction(
        restriction_uid: UUID,
        payload: PlatformRestrictionRevokeRequest,
        moderator: Account = Depends(require_restriction_revoker),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await revoke_platform_restriction(db, moderator.uid, restriction_uid, payload)
        return {"status": "ok", "restriction": item}

    @router.post(
        "/restrictions/{restriction_uid}/appeals",
        status_code=status.HTTP_201_CREATED,
    )
    async def appeal_restriction(
        restriction_uid: UUID,
        payload: PlatformRestrictionAppealCreateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await create_platform_restriction_appeal(
            db,
            current_user["user_uid"],
            restriction_uid,
            payload,
        )
        return {"status": "ok", "appeal": item}

    @router.get("/me/restriction-appeals")
    async def my_restriction_appeals(
        limit: int = Query(default=100, ge=1, le=250),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await list_my_platform_restriction_appeals(
            db,
            current_user["user_uid"],
            limit=limit,
        )
        return {"status": "ok", "appeals": items}

    @router.get("/restriction-appeals")
    async def restriction_appeal_queue(
        appeal_status: Optional[Literal["pending", "upheld", "overturned"]] = Query(
            default="pending",
            alias="status",
        ),
        assigned: Literal["any", "mine", "unassigned"] = Query(default="any"),
        limit: int = Query(default=100, ge=1, le=250),
        moderator: Account = Depends(require_appeal_reviewer),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await list_platform_restriction_appeals(
            db,
            appeal_status=appeal_status,
            reviewer_account_uid=moderator.uid if assigned == "mine" else None,
            only_unassigned=assigned == "unassigned",
            limit=limit,
        )
        return {"status": "ok", "appeals": items}

    @router.post("/restriction-appeals/{appeal_uid}/claim")
    async def claim_restriction_appeal(
        appeal_uid: UUID,
        moderator: Account = Depends(require_appeal_reviewer),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await claim_platform_restriction_appeal(db, appeal_uid, moderator.uid)
        return {"status": "ok", "appeal": item}

    @router.post("/restriction-appeals/{appeal_uid}/release")
    async def release_restriction_appeal(
        appeal_uid: UUID,
        moderator: Account = Depends(require_appeal_reviewer),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await release_platform_restriction_appeal(db, appeal_uid, moderator.uid)
        return {"status": "ok", "appeal": item}

    @router.patch("/restriction-appeals/{appeal_uid}")
    async def resolve_restriction_appeal(
        appeal_uid: UUID,
        payload: PlatformRestrictionAppealResolveRequest,
        moderator: Account = Depends(require_appeal_reviewer),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await resolve_platform_restriction_appeal(
            db,
            appeal_uid,
            moderator.uid,
            payload,
        )
        return {"status": "ok", "appeal": item}

    @router.get("/restriction-capabilities")
    async def restriction_capabilities(
        moderator: Account = Depends(require_platform_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        # UI affordances are derived from server-side RBAC. They are not a
        # security boundary; the action services repeat every permission and
        # hierarchy check before changing durable state.
        can_issue = await account_has_platform_permission(
            db, moderator.uid, RESTRICTION_ISSUE_PERMISSION
        )
        can_permanent = can_issue and await account_has_platform_permission(
            db, moderator.uid, PERMANENT_RESTRICTION_PERMISSION
        )
        can_account_access = can_issue and await account_has_platform_permission(
            db, moderator.uid, ACCOUNT_ACCESS_PERMISSION
        )
        can_revoke = await account_has_platform_permission(
            db, moderator.uid, RESTRICTION_REVOKE_PERMISSION
        )
        can_review_appeals = await account_has_platform_permission(
            db, moderator.uid, APPEAL_REVIEW_PERMISSION
        )

        capabilities: set[str] = set()
        if can_issue:
            capabilities.update(ENFORCEMENT_READY_CAPABILITIES - {"account.access"})
            if can_account_access:
                capabilities.add("account.access")

        return {
            "status": "ok",
            "capabilities": sorted(capabilities),
            "permissions": {
                "issue": can_issue,
                "permanent": can_permanent,
                "account_access": can_account_access,
                "revoke": can_revoke,
                "appeal_review": can_review_appeals,
            },
        }

    app.include_router(router)
