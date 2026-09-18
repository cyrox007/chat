from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.permissions import require_platform_moderator, require_platform_permission
from components.identity.model import Account
from components.moderation.ai_copilot import (
    create_moderation_ai_assessment,
    list_moderation_ai_assessments,
    moderation_ai_public_config,
    set_moderation_ai_outcome,
)
from components.moderation.schemas import ModerationAIOutcomeRequest
from database import Database


AI_ASSESS_PERMISSION = "moderation.platform.ai.assess"


async def require_ai_assessor(request: Request) -> Account:
    await require_platform_moderator(request)
    return await require_platform_permission(request, AI_ASSESS_PERMISSION)


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/trust-safety/v1", tags=["trust-safety-v1"])

    @router.get("/ai-assessment/config")
    async def ai_assessment_config(
        _: Account = Depends(require_ai_assessor),
    ):
        return {"status": "ok", "ai": moderation_ai_public_config()}

    @router.post(
        "/reports/{report_uid}/ai-assessments",
        status_code=status.HTTP_201_CREATED,
    )
    async def request_ai_assessment(
        report_uid: UUID,
        moderator: Account = Depends(require_ai_assessor),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await create_moderation_ai_assessment(
            db,
            report_uid,
            moderator.uid,
        )
        return {"status": "ok", "assessment": item}

    @router.get("/reports/{report_uid}/ai-assessments")
    async def ai_assessments(
        report_uid: UUID,
        limit: int = Query(default=10, ge=1, le=50),
        moderator: Account = Depends(require_ai_assessor),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await list_moderation_ai_assessments(
            db,
            report_uid,
            moderator.uid,
            limit=limit,
        )
        return {"status": "ok", "assessments": items}

    @router.patch(
        "/reports/{report_uid}/ai-assessments/{recommendation_uid}"
    )
    async def ai_assessment_outcome(
        report_uid: UUID,
        recommendation_uid: UUID,
        payload: ModerationAIOutcomeRequest,
        moderator: Account = Depends(require_ai_assessor),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await set_moderation_ai_outcome(
            db,
            report_uid,
            recommendation_uid,
            moderator.uid,
            payload,
        )
        return {"status": "ok", "assessment": item}

    app.include_router(router)
