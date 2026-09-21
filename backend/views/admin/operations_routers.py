from fastapi import APIRouter, Depends, FastAPI, Query
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.permissions import require_admin
from components.notification.operations_metrics import external_delivery_metrics
from database import Database


def install(app: FastAPI) -> None:
    router = APIRouter(
        prefix="/admin/operations",
        tags=["admin-operations"],
        dependencies=[Depends(require_admin)],
    )

    @router.get("/external-delivery")
    async def delivery_metrics(
        window_hours: int = Query(default=24, ge=1, le=720),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        metrics = await external_delivery_metrics(db, window_hours=window_hours)
        return {"status": "ok", "metrics": metrics}

    app.include_router(router)
