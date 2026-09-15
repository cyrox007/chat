from uuid import UUID

from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from components.user.model import User
from database import Database


class StatusesRequest(BaseModel):
    user_ids: list[UUID] = Field(min_length=1, max_length=100)


async def get_user_statuses(
    payload: StatusesRequest,
    db: AsyncSession = Depends(Database.session_generator),
):
    result = await db.execute(
        select(User.uid, User.last_online).where(User.uid.in_(payload.user_ids))
    )
    statuses = {
        str(uid): {
            "last_online": last_online.isoformat() if last_online else None,
        }
        for uid, last_online in result.all()
    }
    return {"status": "ok", "statuses": statuses}
