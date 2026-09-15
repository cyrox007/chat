from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.moderation.consistency import supersede_previous_restrictions
from components.moderation.schemas import (
    ModerationActionCreateRequest,
    ModerationAppealCreateRequest,
    ModerationAppealResolveRequest,
    ModerationReportCreateRequest,
    ModerationReportStatusRequest,
    ReportStatus,
)
from components.moderation.service import (
    create_action,
    create_appeal,
    create_report,
    list_my_actions,
    list_my_appeals,
    list_my_reports,
    list_space_actions,
    list_space_appeals,
    list_space_reports,
    resolve_appeal,
    update_report_status,
)
from database import Database


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/moderation/v1", tags=["moderation-v1"])

    @router.get("/me/reports")
    async def my_reports(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_my_reports(db, current_user["user_uid"], limit, offset)
        return {"status": "ok", "reports": items, "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total}}

    @router.get("/me/actions")
    async def my_actions(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_my_actions(db, current_user["user_uid"], limit, offset)
        return {"status": "ok", "actions": items, "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total}}

    @router.get("/me/appeals")
    async def my_appeals(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_my_appeals(db, current_user["user_uid"], limit, offset)
        return {"status": "ok", "appeals": items, "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total}}

    @router.post("/actions/{action_uid}/appeals", status_code=status.HTTP_201_CREATED)
    async def appeal_action(
        action_uid: UUID,
        payload: ModerationAppealCreateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        appeal = await create_appeal(db, action_uid, current_user["user_uid"], payload)
        return {"status": "ok", "appeal": appeal}

    @router.post("/spaces/{space_uid}/reports", status_code=status.HTTP_201_CREATED)
    async def report(
        space_uid: UUID,
        payload: ModerationReportCreateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await create_report(db, space_uid, current_user["user_uid"], payload)
        return {"status": "ok", "report": item}

    @router.get("/spaces/{space_uid}/reports")
    async def reports(
        space_uid: UUID,
        report_status: Optional[ReportStatus] = Query(default=None, alias="status"),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_space_reports(
            db,
            space_uid,
            current_user["user_uid"],
            report_status,
            limit,
            offset,
        )
        return {"status": "ok", "reports": items, "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total}}

    @router.patch("/spaces/{space_uid}/reports/{report_uid}")
    async def report_status(
        space_uid: UUID,
        report_uid: UUID,
        payload: ModerationReportStatusRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await update_report_status(db, space_uid, report_uid, current_user["user_uid"], payload.status)
        return {"status": "ok", "report": item}

    @router.post("/spaces/{space_uid}/actions", status_code=status.HTTP_201_CREATED)
    async def action(
        space_uid: UUID,
        payload: ModerationActionCreateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await create_action(db, space_uid, current_user["user_uid"], payload)
        if payload.action_type == "restrict":
            await supersede_previous_restrictions(
                db,
                space_uid=space_uid,
                target_account_uid=payload.target_account_uid,
                keep_action_uid=UUID(item["uid"]),
            )
        return {"status": "ok", "action": item}

    @router.get("/spaces/{space_uid}/actions")
    async def actions(
        space_uid: UUID,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_space_actions(db, space_uid, current_user["user_uid"], limit, offset)
        return {"status": "ok", "actions": items, "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total}}

    @router.get("/spaces/{space_uid}/appeals")
    async def appeals(
        space_uid: UUID,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_space_appeals(db, space_uid, current_user["user_uid"], limit, offset)
        return {"status": "ok", "appeals": items, "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total}}

    @router.patch("/spaces/{space_uid}/appeals/{appeal_uid}")
    async def appeal_resolution(
        space_uid: UUID,
        appeal_uid: UUID,
        payload: ModerationAppealResolveRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await resolve_appeal(db, space_uid, appeal_uid, current_user["user_uid"], payload)
        return {"status": "ok", "appeal": item}

    app.include_router(router)
