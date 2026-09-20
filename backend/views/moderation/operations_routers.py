from fastapi import APIRouter, Depends, FastAPI, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.permissions import require_platform_moderator
from components.identity.model import Account
from components.moderation.operations_metrics import trust_safety_metrics
from database import Database


async def require_metrics_viewer(request: Request) -> Account:
    return await require_platform_moderator(request)


def install(app: FastAPI) -> None:
    router = APIRouter(prefix="/trust-safety/v1", tags=["trust-safety-v1"])

    @router.get("/metrics")
    async def metrics(
        window_hours: int = Query(default=168, ge=1, le=720),
        _: Account = Depends(require_metrics_viewer),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        result = await trust_safety_metrics(db, window_hours=window_hours)
        return {"status": "ok", "metrics": result}

    app.include_router(router)
