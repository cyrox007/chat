from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.engagement.batch import SpaceAppearanceBatchRequest, get_space_appearance_batch
from components.engagement.queries import get_my_persona_appearance
from components.engagement.schemas import (
    ActivityCreateRequest,
    ActivityRSVPRequest,
    ActivityUpdateRequest,
    PersonaAppearanceUpdateRequest,
    SpaceAppearanceUpdateRequest,
)
from components.engagement.service import (
    clear_activity_rsvp,
    create_activity,
    get_persona_appearance,
    get_space_appearance,
    list_activities,
    set_activity_rsvp,
    update_activity,
    update_my_persona_appearance,
    update_space_appearance,
)
from database import Database


def install(app: FastAPI) -> None:
    appearance = APIRouter(prefix="/appearance/v1", tags=["appearance-v1"])
    activities = APIRouter(prefix="/activities/v1", tags=["activities-v1"])

    @appearance.get("/me/persona")
    async def my_persona_appearance(
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await get_my_persona_appearance(db, current_user["user_uid"])
        if item is None:
            raise HTTPException(status_code=409, detail={"error_type": "primary_persona_missing"})
        return {"status": "ok", "appearance": item}

    @appearance.get("/personas/{persona_uid}")
    async def persona_appearance(
        persona_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await get_persona_appearance(db, persona_uid, current_user["user_uid"])
        return {"status": "ok", "appearance": item}

    @appearance.patch("/me/persona")
    async def patch_my_persona_appearance(
        payload: PersonaAppearanceUpdateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await update_my_persona_appearance(db, current_user["user_uid"], payload)
        return {"status": "ok", "appearance": item}

    @appearance.post("/spaces/batch")
    async def batch_space_appearance(
        payload: SpaceAppearanceBatchRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await get_space_appearance_batch(
            db,
            current_user["user_uid"],
            payload.space_uids,
        )
        return {"status": "ok", "appearances": items}

    @appearance.get("/spaces/{space_uid}")
    async def space_appearance(
        space_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await get_space_appearance(db, space_uid, current_user["user_uid"])
        return {"status": "ok", "appearance": item}

    @appearance.patch("/spaces/{space_uid}")
    async def patch_space_appearance(
        space_uid: UUID,
        payload: SpaceAppearanceUpdateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await update_space_appearance(db, space_uid, current_user["user_uid"], payload)
        return {"status": "ok", "appearance": item}

    @activities.get("/spaces/{space_uid}")
    async def activity_list(
        space_uid: UUID,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_activities(
            db,
            space_uid,
            current_user["user_uid"],
            limit,
            offset,
        )
        return {
            "status": "ok",
            "activities": items,
            "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total},
        }

    @activities.post("/spaces/{space_uid}", status_code=status.HTTP_201_CREATED)
    async def create_space_activity(
        space_uid: UUID,
        payload: ActivityCreateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await create_activity(db, space_uid, current_user["user_uid"], payload)
        return {"status": "ok", "activity": item}

    @activities.patch("/spaces/{space_uid}/{activity_uid}")
    async def patch_space_activity(
        space_uid: UUID,
        activity_uid: UUID,
        payload: ActivityUpdateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await update_activity(
            db,
            space_uid,
            activity_uid,
            current_user["user_uid"],
            payload,
        )
        return {"status": "ok", "activity": item}

    @activities.put("/{activity_uid}/rsvp")
    async def activity_rsvp(
        activity_uid: UUID,
        payload: ActivityRSVPRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await set_activity_rsvp(db, activity_uid, current_user["user_uid"], payload)
        return {"status": "ok", "activity": item}

    @activities.delete("/{activity_uid}/rsvp")
    async def delete_activity_rsvp(
        activity_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await clear_activity_rsvp(db, activity_uid, current_user["user_uid"])
        return {"status": "ok", "activity": item}

    app.include_router(appearance)
    app.include_router(activities)
