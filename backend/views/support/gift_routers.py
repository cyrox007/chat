from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.support.schemas import GiftSendRequest
from components.support import service
from database import Database


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/support/v1", tags=["support-v1"])

    @router.get("/catalog")
    async def catalog(
        target: str = Query(default="persona", pattern="^(persona|space)$"),
        _: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        return {"status": "ok", "gifts": await service.list_gift_catalog(db, target)}

    @router.get("/accounts/{account_uid}/shelf")
    async def account_shelf(
        account_uid: UUID,
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        return {
            "status": "ok",
            **(await service.account_support_shelf(db, account_uid, user["user_uid"])),
        }

    @router.get("/personas/{persona_uid}/shelf")
    async def persona_shelf(
        persona_uid: UUID,
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        return {"status": "ok", **(await service.persona_support_shelf(db, persona_uid, user["user_uid"]))}

    @router.post("/personas/{persona_uid}/gifts", status_code=status.HTTP_201_CREATED)
    async def gift_persona(
        persona_uid: UUID,
        payload: GiftSendRequest,
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        entry = await service.send_persona_gift(db, persona_uid, user["user_uid"], payload)
        return {"status": "ok", "entry": entry}

    @router.get("/spaces/{space_uid}/shelf")
    async def space_shelf(
        space_uid: UUID,
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        return {"status": "ok", **(await service.space_support_shelf(db, space_uid, user["user_uid"]))}

    @router.post("/spaces/{space_uid}/gifts", status_code=status.HTTP_201_CREATED)
    async def gift_space(
        space_uid: UUID,
        payload: GiftSendRequest,
        user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        entry = await service.send_space_gift(db, space_uid, user["user_uid"], payload)
        return {"status": "ok", "entry": entry}

    app.include_router(router)
