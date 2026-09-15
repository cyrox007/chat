from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query
from sqlalchemy.ext.asyncio import AsyncSession

from components.achievement.service import list_achievements
from components.auth.middleware import auth_middle
from database import Database


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/achievements/v1", tags=["achievements-v1"])

    @router.get("/me")
    async def my_achievements(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_achievements(
            db,
            target_account_uid=current_user["user_uid"],
            viewer_uid=current_user["user_uid"],
            include_private_context=True,
            limit=limit,
            offset=offset,
        )
        return {
            "status": "ok",
            "achievements": items,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(items),
                "total": total,
            },
        }

    @router.get("/accounts/{account_uid}")
    async def public_achievements(
        account_uid: UUID,
        limit: int = Query(default=12, ge=1, le=50),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_achievements(
            db,
            target_account_uid=account_uid,
            viewer_uid=current_user["user_uid"],
            include_private_context=False,
            limit=limit,
            offset=offset,
        )
        return {
            "status": "ok",
            "achievements": items,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(items),
                "total": total,
            },
        }

    app.include_router(router)
