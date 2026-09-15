from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.space.membership_schemas import (
    SpaceMembershipActionRequest,
    SpaceMembershipRoleFilter,
    SpaceMembershipStatusFilter,
)
from components.space.membership_service import list_members_page, manage_membership
from components.space.model import SpaceSettings
from components.space.schemas import (
    SpaceCreateRequest,
    SpaceMembershipRoleUpdateRequest,
    SpacePurpose,
    SpaceUpdateRequest,
)
from components.space.service import (
    archive_space,
    create_space,
    get_space,
    join_space,
    leave_space,
    list_spaces,
    update_member_role,
    update_space,
)
from database import Database


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/spaces/v1", tags=["spaces-v1"])

    @router.get("")
    async def index(
        q: Optional[str] = Query(default=None, max_length=80),
        purpose: Optional[SpacePurpose] = None,
        tag: Optional[str] = Query(default=None, max_length=40),
        limit: int = Query(default=30, ge=1, le=50),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        spaces = await list_spaces(
            db,
            viewer_uid=current_user["user_uid"],
            query=q,
            purpose=purpose,
            tag=tag,
            limit=limit,
            offset=offset,
        )
        return {
            "status": "ok",
            "spaces": spaces,
            "pagination": {"limit": limit, "offset": offset, "count": len(spaces)},
        }

    @router.post("", status_code=status.HTTP_201_CREATED)
    async def create(
        payload: SpaceCreateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        space = await create_space(db, current_user["user_uid"], payload)
        return {"status": "ok", "space": space}

    @router.get("/{space_uid}")
    async def detail(
        space_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        space = await get_space(db, space_uid, current_user["user_uid"])
        return {"status": "ok", "space": space}

    @router.patch("/{space_uid}")
    async def patch(
        space_uid: UUID,
        payload: SpaceUpdateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        changes = payload.model_dump(exclude_unset=True)
        settings = await db.get(SpaceSettings, space_uid)
        current_visibility = settings.visibility if settings else "public"
        current_join_policy = settings.join_policy if settings else "open"
        next_visibility = changes.get("visibility", current_visibility)
        next_join_policy = changes.get("join_policy", current_join_policy)
        if next_visibility == "private" and next_join_policy != "invite":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error_type": "private_space_must_be_invite_only"},
            )

        space = await update_space(db, space_uid, current_user["user_uid"], payload)
        return {"status": "ok", "space": space}

    @router.delete("/{space_uid}")
    async def archive(
        space_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        await archive_space(db, space_uid, current_user["user_uid"])
        return {"status": "ok"}

    @router.post("/{space_uid}/join")
    async def join(
        space_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        space = await join_space(db, space_uid, current_user["user_uid"])
        return {"status": "ok", "space": space}

    @router.delete("/{space_uid}/membership")
    async def leave(
        space_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        await leave_space(db, space_uid, current_user["user_uid"])
        return {"status": "ok"}

    @router.get("/{space_uid}/members")
    async def members(
        space_uid: UUID,
        membership_status: SpaceMembershipStatusFilter = Query(default="active", alias="status"),
        role: Optional[SpaceMembershipRoleFilter] = None,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_members_page(
            db,
            space_uid=space_uid,
            viewer_uid=current_user["user_uid"],
            membership_status=membership_status,
            role=role,
            limit=limit,
            offset=offset,
        )
        return {
            "status": "ok",
            "members": items,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(items),
                "total": total,
            },
        }

    @router.patch("/{space_uid}/members/{account_uid}")
    async def patch_member_role(
        space_uid: UUID,
        account_uid: UUID,
        payload: SpaceMembershipRoleUpdateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        membership = await update_member_role(
            db,
            space_uid=space_uid,
            target_account_uid=account_uid,
            viewer_uid=current_user["user_uid"],
            role=payload.role,
        )
        return {"status": "ok", "membership": membership}

    @router.patch("/{space_uid}/members/{account_uid}/membership")
    async def patch_membership(
        space_uid: UUID,
        account_uid: UUID,
        payload: SpaceMembershipActionRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        membership = await manage_membership(
            db,
            space_uid=space_uid,
            target_account_uid=account_uid,
            viewer_uid=current_user["user_uid"],
            action=payload.action,
        )
        return {"status": "ok", "membership": membership}

    app.include_router(router)
