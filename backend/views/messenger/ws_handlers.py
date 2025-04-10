from uuid import UUID
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from components.message.model import PrivateMessage
from components.decorators.db import get_session
from utils.logger import setup_logger
from socket_manager.manager import ConnectionManager

logger = setup_logger(__name__)

# Инициализация менеджера подключений
private_manager = ConnectionManager()

async def initialize_messenger_connection(websocket: WebSocket, db_session: Session, user_uid: UUID):
    """
    Инициализирует соединение для мессенджера.
    """
    await private_manager.connect_to_messenger(websocket, user_uid)
    logger.info(f"User {user_uid} connected to messenger")

async def handle_private_messages(websocket: WebSocket, user_uid: UUID, db_session: Session):
    """
    Обрабатывает входящие приватные сообщения.
    """
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "send_message":
                await handle_send_private_message(data, user_uid, db_session)
            elif action == "mark_as_read":
                await handle_mark_as_read(data, user_uid, db_session)
            elif action == "get_conversation":
                await handle_get_conversation(data, user_uid, db_session)
            else:
                logger.warning(f"Unknown action: {action}")

    except WebSocketDisconnect:
        logger.info(f"User {user_uid} disconnected from messenger")
        private_manager.disconnect(websocket, None)

async def handle_send_private_message(data: dict, sender_uid: UUID, db_session: Session):
    """
    Обрабатывает отправку нового приватного сообщения.
    """
    try:
        message_data = {
            "content": data.get("content"),
            "content_type": data.get("content_type", "text"),
            "sender_uid": str(sender_uid),
            "receiver_uid": data.get("receiver_uid"),
            "media_metadata": data.get("media_metadata"),
        }

        # Создаем сообщение в БД
        formatted_message = PrivateMessage.create_private_message(db_session, message_data)
        formatted_message['frontId'] = data.get('frontId')

        # Отправляем сообщение отправителю и получателю
        await private_manager.send_to_user(str(sender_uid), formatted_message)
        await private_manager.send_to_user(str(message_data["receiver_uid"]), formatted_message)

        logger.info(f"Private message sent from {sender_uid} to {message_data['receiver_uid']}")

    except Exception as e:
        logger.error(f"Error sending private message: {e}")
        error_message = {
            "type": "error",
            "message": "Failed to send message",
            "details": str(e),
            "frontId": data.get('frontId')
        }
        await private_manager.send_to_user(str(sender_uid), error_message)

async def handle_mark_as_read(data: dict, user_uid: UUID, db_session: Session):
    """
    Помечает сообщение как прочитанное.
    """
    try:
        message_uid = data.get("message_uid")
        if message_uid:
            message = PrivateMessage.mark_as_read(db_session, message_uid)
            if message:
                response = {
                    "type": "message_read",
                    "message_uid": str(message_uid),
                    "read_at": datetime.utcnow().isoformat()
                }
                # Уведомляем отправителя о прочтении
                if str(message.sender_uid) != str(user_uid):
                    await private_manager.send_to_user(str(message.sender_uid), response)

    except Exception as e:
        logger.error(f"Error marking message as read: {e}")

async def handle_get_conversation(data: dict, user_uid: UUID, db_session: Session):
    """
    Возвращает переписку с другим пользователем.
    """
    try:
        other_user_uid = data.get("other_user_uid")
        if other_user_uid:
            messages = PrivateMessage.get_conversation(
                db_session, 
                user1_uid=user_uid,
                user2_uid=UUID(other_user_uid)
            )
            
            response = {
                "type": "conversation",
                "other_user_uid": other_user_uid,
                "messages": messages,
                "request_id": data.get("request_id")
            }
            
            await private_manager.send_to_user(str(user_uid), response)

    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        error_message = {
            "type": "error",
            "message": "Failed to get conversation",
            "details": str(e),
            "request_id": data.get("request_id")
        }
        await private_manager.send_to_user(str(user_uid), error_message)

@get_session
async def handle_messenger_connection(websocket: WebSocket, user, db_session=None):
    """
    Основной обработчик подключения к мессенджеру.
    """
    try:
        user_uid = UUID(user["user_uid"])
        
        # Инициализация соединения
        await initialize_messenger_connection(websocket, db_session, user_uid)
        
        # Обработка входящих сообщений
        await handle_private_messages(websocket, user_uid, db_session)

    except Exception as e:
        logger.error(f"Messenger connection error: {e}")
        await websocket.close(code=1011, reason="Internal server error")