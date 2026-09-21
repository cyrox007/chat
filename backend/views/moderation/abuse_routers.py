from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.permissions import require_platform_moderator
from components.identity.model import Account
from components.moderation.abuse_signals import list_abuse_signals, review_abuse_signal
from database import Database


class AbuseSignalReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern=r"^(reviewed|dismissed)$")
    note: str | None = Field(default=None, max_length=1000)
    calibration_label: str | None = Field(
        default=None,
        pattern=r"^(true_positive|false_positive|unclear)$",
    )

    @model_validator(mode="after")
    def validate_calibration_pair(self):
        if self.calibration_label == "false_positive" and self.decision != "dismissed":
            raise ValueError("false_positive requires dismissed decision")
        if self.calibration_label in {"true_positive", "unclear"} and self.decision != "reviewed":
            raise ValueError(f"{self.calibration_label} requires reviewed decision")
        return self


async def require_signal_reviewer(request: Request) -> Account:
    return await require_platform_moderator(request)


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/trust-safety/v1", tags=["trust-safety-v1"])

    @router.get("/abuse-signals")
    async def abuse_signal_queue(
        status_value: str = Query(default="open", alias="status", pattern=r"^(open|reviewed|dismissed)?$"),
        limit: int = Query(default=100, ge=1, le=200),
        _: Account = Depends(require_signal_reviewer),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await list_abuse_signals(db, status_value=status_value, limit=limit)
        return {"status": "ok", "signals": items}

    @router.patch("/abuse-signals/{signal_uid}")
    async def review_signal(
        signal_uid: UUID,
        payload: AbuseSignalReviewRequest,
        moderator: Account = Depends(require_signal_reviewer),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await review_abuse_signal(
            db,
            signal_uid=signal_uid,
            reviewer_account_uid=moderator.uid,
            decision=payload.decision,
            note=payload.note,
            calibration_label=payload.calibration_label,
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_type": "trust_safety_abuse_signal_not_found"},
            )
        return {"status": "ok", "signal": item}

    app.include_router(router)
