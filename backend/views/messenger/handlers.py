from fastapi import HTTPException, Request
from uuid import UUID
from components.message.model import PrivateMessage
from components.decorators.db import get_session
from utils.logger import setup_logger

logger = setup_logger(__name__)

@get_session
async def get_dialogs(request: Request, db_session = None):
    try:
        user = request.state.user
        user_uid = UUID(user["user_uid"])
        dialogs = await PrivateMessage.get_dialogs(db_session, user_uid)
        return {"status": "ok", "dialogs": dialogs}
    except Exception as e:
        logger.error(f"Error fetching dialogs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@get_session
async def get_conversation(user_id: UUID, request: Request, db_session=None):
    try:
        current_user = request.state.user
        messages = await PrivateMessage.get_conversation(
            db_session,
            UUID(current_user["user_uid"]),
            user_id
        )
        return {"status": "ok", "messages": messages}
    except Exception as e:
        logger.error(f"Error fetching conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")