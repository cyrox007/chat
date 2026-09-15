from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.engagement.round_schemas import (
    ConversationRoundCreateRequest,
    ConversationRoundResponseRequest,
    ConversationRoundUpdateRequest,
)
from components.engagement.round_service import (
    close_round,
    create_round,
    list_round_responses,
    list_rounds,
    put_round_response,
)
from database import Database


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/activities/v1", tags=["conversation-rounds-v1"])

    @router.get("/{activity_uid}/rounds")
    async def rounds(
        activity_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await list_rounds(db, activity_uid, current_user["user_uid"])
        return {"status": "ok", "rounds": items}

    @router.post("/{activity_uid}/rounds", status_code=status.HTTP_201_CREATED)
    async def create_conversation_round(
        activity_uid: UUID,
        payload: ConversationRoundCreateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await create_round(db, activity_uid, current_user["user_uid"], payload)
        return {"status": "ok", "round": item}

    @router.patch("/{activity_uid}/rounds/{round_uid}")
    async def update_conversation_round(
        activity_uid: UUID,
        round_uid: UUID,
        payload: ConversationRoundUpdateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        # v1 only supports the terminal `closed` transition. There is no client
        # path for reopening a round or mutating its original prompt/options.
        item = await close_round(
            db,
            activity_uid,
            round_uid,
            current_user["user_uid"],
        )
        return {"status": "ok", "round": item}

    @router.get("/rounds/{round_uid}/responses")
    async def round_responses(
        round_uid: UUID,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_round_responses(
            db,
            round_uid,
            current_user["user_uid"],
            limit,
            offset,
        )
        return {
            "status": "ok",
            "responses": items,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(items),
                "total": total,
            },
        }

    @router.put("/rounds/{round_uid}/response")
    async def respond_to_round(
        round_uid: UUID,
        payload: ConversationRoundResponseRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await put_round_response(
            db,
            round_uid,
            current_user["user_uid"],
            payload,
        )
        return {"status": "ok", "response": item}

    app.include_router(router)
