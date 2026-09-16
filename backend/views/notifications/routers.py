from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.engagement.occurrence_service import (
    list_activity_occurrences,
    sync_activity_occurrences,
)
from components.notification.message_delivery import (
    get_message_notification_preferences,
    update_message_notification_preferences,
)
from components.notification.schemas import (
    ActivityReminderUpdateRequest,
    MessageNotificationPreferenceUpdateRequest,
)
from components.notification.service import (
    delete_activity_reminder,
    list_notifications,
    list_space_reminders,
    mark_all_notifications_read,
    mark_notification_read,
    set_activity_reminder,
    sync_activity_reminders,
    unread_notification_count,
)
from database import Database


def install(app: FastAPI) -> None:
    occurrences = APIRouter(prefix="/activity-occurrences/v1", tags=["activity-occurrences-v1"])
    notifications = APIRouter(prefix="/notifications/v1", tags=["notifications-v1"])

    @occurrences.get("/activities/{activity_uid}")
    async def activity_occurrence_list(
        activity_uid: UUID,
        limit: int = Query(default=20, ge=1, le=100),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await list_activity_occurrences(
            db,
            activity_uid,
            current_user["user_uid"],
            limit=limit,
        )
        return {"status": "ok", "occurrences": items}

    @occurrences.post("/activities/{activity_uid}/sync")
    async def activity_occurrence_sync(
        activity_uid: UUID,
        limit: int = Query(default=20, ge=1, le=100),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await sync_activity_occurrences(
            db,
            activity_uid,
            current_user["user_uid"],
            limit=limit,
        )
        return {"status": "ok", "occurrences": items}

    @notifications.post("/sync")
    async def sync_notifications(
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        await sync_activity_reminders(db, current_user["user_uid"])
        unread = await unread_notification_count(db, current_user["user_uid"])
        return {"status": "ok", "unread": unread}

    @notifications.get("/unread-count")
    async def notification_unread_count(
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        unread = await unread_notification_count(db, current_user["user_uid"])
        return {"status": "ok", "unread": unread}

    @notifications.get("/message-preferences")
    async def message_notification_preferences(
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        preferences = await get_message_notification_preferences(
            db,
            current_user["user_uid"],
        )
        return {"status": "ok", "preferences": preferences}

    @notifications.patch("/message-preferences")
    async def patch_message_notification_preferences(
        payload: MessageNotificationPreferenceUpdateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        preferences = await update_message_notification_preferences(
            db,
            current_user["user_uid"],
            payload,
        )
        return {"status": "ok", "preferences": preferences}

    @notifications.get("")
    async def notification_list(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items, total, unread = await list_notifications(
            db,
            current_user["user_uid"],
            limit=limit,
            offset=offset,
        )
        return {
            "status": "ok",
            "notifications": items,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(items),
                "total": total,
            },
            "unread": unread,
        }

    @notifications.get("/spaces/{space_uid}/reminders")
    async def space_reminder_list(
        space_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        items = await list_space_reminders(db, space_uid, current_user["user_uid"])
        return {"status": "ok", "reminders": items}

    @notifications.put("/activities/{activity_uid}/reminder")
    async def put_activity_reminder(
        activity_uid: UUID,
        payload: ActivityReminderUpdateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await set_activity_reminder(
            db,
            activity_uid,
            current_user["user_uid"],
            payload,
        )
        return {"status": "ok", "reminder": item}

    @notifications.delete("/activities/{activity_uid}/reminder", status_code=status.HTTP_204_NO_CONTENT)
    async def remove_activity_reminder(
        activity_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        await delete_activity_reminder(db, activity_uid, current_user["user_uid"])

    @notifications.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
    async def read_all_notifications(
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        await mark_all_notifications_read(db, current_user["user_uid"])

    @notifications.patch("/{notification_uid}/read")
    async def read_notification(
        notification_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        item = await mark_notification_read(
            db,
            notification_uid,
            current_user["user_uid"],
        )
        return {"status": "ok", "notification": item}

    app.include_router(occurrences)
    app.include_router(notifications)
