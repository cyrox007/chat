from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.auth.permissions import require_platform_moderator
from components.identity.model import Account
from components.moderation.policy import (
    issue_platform_restriction,
    list_account_restrictions,
    resolve_account,
    revoke_platform_restriction,
)
from components.moderation.schemas import (
    PlatformCapability,
    PlatformRestrictionCreateRequest,
    PlatformRestrictionRevokeRequest,
)
from database import Database


# Only capabilities with a real server-side enforcement point may be issued.
# Expand this set in the same commit that adds the corresponding domain guard.
ENFORCEMENT_READY_CAPABILITIES: frozenset[str] = frozenset(
    {"messenger.send", "space.chat.send", "media.upload"}
)


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/trust-safety/v1", tags=["trust-safety-v1"])

    @router.post("/restrictions", status_code=status.HTTP_201_CREATED)
    async def create_restriction(
        payload: PlatformRestrictionCreateRequest,
        moderator: Account = Depends(require_platform_moderator),
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
        moderator: Account = Depends(require_platform_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await revoke_platform_restriction(db, moderator.uid, restriction_uid, payload)
        return {"status": "ok", "restriction": item}

    @router.get("/restriction-capabilities")
    async def restriction_capabilities(
        _: Account = Depends(require_platform_moderator),
    ):
        # The complete schema remains broader than the currently enforced set;
        # exposing only ready capabilities prevents UI from offering fake sanctions.
        return {
            "status": "ok",
            "capabilities": sorted(ENFORCEMENT_READY_CAPABILITIES),
        }

    app.include_router(router)
