from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import joinedload

from components.decorators.db import get_session
from components.message.model import PrivateMessage
from utils.logger import setup_logger

logger = setup_logger(__name__)


@get_session
async def get_dialogs(request: Request, db_session=None):
    """Return one latest message per real conversation partner.

    The legacy implementation grouped by greatest(sender_uid, receiver_uid), which
    can collapse unrelated dialogs when the current UUID sorts above both partners.
    Partner identity is contextual, so derive it relative to the authenticated user.
    """
    try:
        current_uid = UUID(request.state.user["user_uid"])

        result = await db_session.execute(
            select(PrivateMessage)
            .options(
                joinedload(PrivateMessage.sender),
                joinedload(PrivateMessage.receiver),
            )
            .where(
                or_(
                    PrivateMessage.sender_uid == current_uid,
                    PrivateMessage.receiver_uid == current_uid,
                )
            )
            .order_by(desc(PrivateMessage.created_at))
            .limit(500)
        )
        recent_messages = result.scalars().all()

        unread_result = await db_session.execute(
            select(PrivateMessage.sender_uid, func.count(PrivateMessage.uid))
            .where(
                PrivateMessage.receiver_uid == current_uid,
                PrivateMessage.is_read.is_(False),
            )
            .group_by(PrivateMessage.sender_uid)
        )
        unread_by_sender = {str(sender_uid): count for sender_uid, count in unread_result.all()}

        dialogs = []
        seen_partners = set()
        for message in recent_messages:
            partner_uid = (
                message.receiver_uid
                if str(message.sender_uid) == str(current_uid)
                else message.sender_uid
            )
            partner_key = str(partner_uid)
            if partner_key in seen_partners:
                continue
            seen_partners.add(partner_key)

            partner = (
                message.receiver
                if str(message.sender_uid) == str(current_uid)
                else message.sender
            )
            dialogs.append(
                {
                    "partner_id": partner_key,
                    "last_message": message.text,
                    "last_message_time": message.created_at.isoformat(),
                    "unread_count": unread_by_sender.get(partner_key, 0),
                    "partner": {
                        "username": getattr(partner, "username", "Unknown"),
                        "avatar": getattr(partner, "avatar", None),
                    },
                }
            )

        return {"status": "ok", "dialogs": dialogs}
    except Exception:
        logger.exception("Error fetching dialogs")
        raise HTTPException(status_code=500, detail="Internal server error")


@get_session
async def get_conversation(user_id: UUID, request: Request, db_session=None):
    try:
        current_user = request.state.user
        messages = await PrivateMessage.get_conversation(
            db_session,
            UUID(current_user["user_uid"]),
            user_id,
        )
        return {"status": "ok", "messages": messages}
    except Exception:
        logger.exception("Error fetching conversation")
        raise HTTPException(status_code=500, detail="Internal server error")
