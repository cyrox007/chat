from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
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
    list_space_members,
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
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await list_space_members(db, space_uid, current_user["user_uid"])
        return {"status": "ok", "members": items}

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

    app.include_router(router)
