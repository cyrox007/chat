from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.permissions import require_platform_moderator, require_platform_permission
from components.identity.model import Account
from components.moderation.media_service import (
    MEDIA_MANAGE_PERMISSION,
    list_report_media_records,
    quarantine_report_attachment,
    remove_report_attachment,
    restore_report_attachment,
)
from database import Database


class MediaActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=1000)


async def require_media_moderator(request: Request) -> Account:
    await require_platform_moderator(request)
    return await require_platform_permission(request, MEDIA_MANAGE_PERMISSION)


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/trust-safety/v1", tags=["trust-safety-v1"])

    @router.get("/reports/{report_uid}/media-records")
    async def media_records(
        report_uid: UUID,
        moderator: Account = Depends(require_media_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await list_report_media_records(
            db,
            report_uid=report_uid,
            moderator_account_uid=moderator.uid,
        )
        return {"status": "ok", "media_records": items}

    @router.post("/reports/{report_uid}/media/{attachment_index}/quarantine")
    async def quarantine_media(
        report_uid: UUID,
        attachment_index: int,
        payload: MediaActionRequest,
        moderator: Account = Depends(require_media_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await quarantine_report_attachment(
            db,
            report_uid=report_uid,
            attachment_index=attachment_index,
            moderator_account_uid=moderator.uid,
            reason=payload.reason,
        )
        return {"status": "ok", "media_record": item}

    @router.post("/reports/{report_uid}/media-records/{record_uid}/restore")
    async def restore_media(
        report_uid: UUID,
        record_uid: UUID,
        moderator: Account = Depends(require_media_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await restore_report_attachment(
            db,
            report_uid=report_uid,
            record_uid=record_uid,
            moderator_account_uid=moderator.uid,
        )
        return {"status": "ok", "media_record": item}

    @router.post("/reports/{report_uid}/media-records/{record_uid}/remove")
    async def remove_media(
        report_uid: UUID,
        record_uid: UUID,
        payload: MediaActionRequest,
        moderator: Account = Depends(require_media_moderator),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await remove_report_attachment(
            db,
            report_uid=report_uid,
            record_uid=record_uid,
            moderator_account_uid=moderator.uid,
            reason=payload.reason,
        )
        return {"status": "ok", "media_record": item}

    app.include_router(router)
