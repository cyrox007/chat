from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.auth.permissions import require_platform_moderator
from components.identity.model import Account
from components.moderation.consistency import (
    ensure_report_actionable,
    supersede_previous_restrictions,
)
from components.moderation.schemas import (
    ModerationActionCreateRequest,
    ModerationAppealCreateRequest,
    ModerationAppealResolveRequest,
    ModerationReportCreateRequest,
    ModerationReportStatusRequest,
    ReportStatus,
    TrustSafetyCategory,
    TrustSafetyDecisionRequest,
    TrustSafetyPriority,
    TrustSafetyReportCreateRequest,
    TrustSafetyStatus,
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
from components.moderation.trust_safety import (
    claim_trust_safety_report,
    create_trust_safety_report,
    decide_trust_safety_report,
    list_my_trust_safety_reports,
    list_trust_safety_audit,
    list_trust_safety_queue,
    release_trust_safety_report,
    trust_safety_evidence,
)
from database import Database


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/moderation/v1", tags=["moderation-v1"])
    trust_safety = APIRouter(prefix="/trust-safety/v1", tags=["trust-safety-v1"])

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
        await ensure_report_actionable(
            db,
            space_uid=space_uid,
            viewer_uid=current_user["user_uid"],
            report_uid=payload.report_uid,
            target_account_uid=payload.target_account_uid,
        )
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

    # Platform Trust & Safety is intentionally separate from Space-local moderation.
    @trust_safety.post("/reports", status_code=status.HTTP_201_CREATED)
    async def create_platform_report(
        payload: TrustSafetyReportCreateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await create_trust_safety_report(db, current_user["user_uid"], payload)
        return {"status": "ok", "report": item}

    @trust_safety.get("/me/reports")
    async def my_platform_reports(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_my_trust_safety_reports(
            db,
            current_user["user_uid"],
            limit=limit,
            offset=offset,
        )
        return {
            "status": "ok",
            "reports": items,
            "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total},
        }

    @trust_safety.get("/queue")
    async def platform_queue(
        queue_status: Optional[TrustSafetyStatus] = Query(default=None, alias="status"),
        priority: Optional[TrustSafetyPriority] = Query(default=None),
        category: Optional[TrustSafetyCategory] = Query(default=None),
        assigned: Literal["any", "mine", "unassigned"] = Query(default="any"),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        moderator: Account = Depends(require_platform_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total = await list_trust_safety_queue(
            db,
            queue_status=queue_status,
            priority=priority,
            category=category,
            assigned_to_account_uid=moderator.uid if assigned == "mine" else None,
            only_unassigned=assigned == "unassigned",
            limit=limit,
            offset=offset,
        )
        return {
            "status": "ok",
            "reports": items,
            "pagination": {"limit": limit, "offset": offset, "count": len(items), "total": total},
        }

    @trust_safety.post("/reports/{report_uid}/claim")
    async def claim_platform_report(
        report_uid: UUID,
        moderator: Account = Depends(require_platform_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await claim_trust_safety_report(db, report_uid, moderator.uid)
        return {"status": "ok", "report": item}

    @trust_safety.post("/reports/{report_uid}/release")
    async def release_platform_report(
        report_uid: UUID,
        moderator: Account = Depends(require_platform_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await release_trust_safety_report(db, report_uid, moderator.uid)
        return {"status": "ok", "report": item}

    @trust_safety.get("/reports/{report_uid}/evidence")
    async def platform_report_evidence(
        report_uid: UUID,
        moderator: Account = Depends(require_platform_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        evidence = await trust_safety_evidence(db, report_uid, moderator.uid)
        return {"status": "ok", "evidence": evidence}

    @trust_safety.patch("/reports/{report_uid}")
    async def decide_platform_report(
        report_uid: UUID,
        payload: TrustSafetyDecisionRequest,
        moderator: Account = Depends(require_platform_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await decide_trust_safety_report(db, report_uid, moderator.uid, payload)
        return {"status": "ok", "report": item}

    @trust_safety.get("/reports/{report_uid}/audit")
    async def platform_report_audit(
        report_uid: UUID,
        limit: int = Query(default=100, ge=1, le=250),
        _: Account = Depends(require_platform_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        events = await list_trust_safety_audit(db, report_uid, limit=limit)
        return {"status": "ok", "events": events}

    app.include_router(router)
    app.include_router(trust_safety)
