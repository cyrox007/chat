from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.support.schemas import SupportSettingsUpdateRequest
from components.support import service
from database import Database


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/support/v1", tags=["support-v1"])

    @router.get("/me/profile")
    async def my_profile(
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        return {"status": "ok", "support": await service.get_own_support_profile(db, user["user_uid"])}

    @router.patch("/me/profile")
    async def patch_my_profile(
        payload: SupportSettingsUpdateRequest,
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await service.update_own_support_profile(db, user["user_uid"], payload)
        return {"status": "ok", "support": item}

    @router.get("/me/received")
    async def my_received(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await service.own_received_support(db, user["user_uid"], limit=limit, offset=offset)
        return {"status": "ok", "items": items, "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total}}

    @router.get("/spaces/{space_uid}/settings")
    async def space_settings(
        space_uid: UUID,
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await service.get_space_support_settings(db, space_uid, user["user_uid"])
        return {"status": "ok", "support": item}

    @router.patch("/spaces/{space_uid}/settings")
    async def patch_space_settings(
        space_uid: UUID,
        payload: SupportSettingsUpdateRequest,
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await service.update_space_support_settings(db, space_uid, user["user_uid"], payload)
        return {"status": "ok", "support": item}

    @router.get("/spaces/{space_uid}/received")
    async def space_received(
        space_uid: UUID,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await service.space_received_support(db, space_uid, user["user_uid"], limit=limit, offset=offset)
        return {"status": "ok", "items": items, "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total}}

    app.include_router(router)
