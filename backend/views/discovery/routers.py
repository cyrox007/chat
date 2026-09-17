from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, Query
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.discovery.moderation import discover_spaces_with_moderation
from components.discovery.service import DISCOVERY_ALGORITHM
from components.space.schemas import SpacePurpose
from database import Database


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/discovery/v1", tags=["discovery-v1"])

    @router.get("/spaces")
    async def spaces(
        q: Optional[str] = Query(default=None, max_length=80),
        purpose: Optional[SpacePurpose] = None,
        tag: Optional[str] = Query(default=None, max_length=40),
        limit: int = Query(default=30, ge=1, le=50),
        offset: int = Query(default=0, ge=0, le=150),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await discover_spaces_with_moderation(
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
            "algorithm": DISCOVERY_ALGORITHM,
            "spaces": items,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(items),
            },
        }

    app.include_router(router)
