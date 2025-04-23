from uuid import UUID
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from components.user.model import User
from components.message.model import PrivateMessage
from components.decorators.db import get_session
from utils.logger import setup_logger
from socket_manager import private_manager

logger = setup_logger(__name__)

# Инициализация менеджера подключений
# private_manager = ConnectionManager()

async def initialize_messenger_connection(websocket: WebSocket, user_uid: UUID, db_session: AsyncSession):
    """
    Инициализирует соединение для мессенджера.
    """
    await private_manager.connect_to_messenger(websocket, user_uid)
    await User.update_last_online(db_session, user_uid)
    logger.info(f"User {user_uid} connected to messenger from a new device")

async def handle_private_messages(websocket: WebSocket, user_uid: UUID, db_session: AsyncSession):
    """
    Обрабатывает входящие приватные сообщения.
    """
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "send_message":
                await handle_send_private_message(data, user_uid, db_session)
            elif action == "mark_message_as_read":
                await handle_mark_as_read(data, user_uid, db_session)
            elif action == "get_conversation":
                await handle_get_conversation(data, user_uid, db_session, websocket)
            else:
                logger.warning(f"Unknown action: {action}")

            # Обновляем статус онлайн
            await private_manager.update_user_activity(db_session, user_uid)

    except WebSocketDisconnect:
        logger.info(f"User {user_uid} disconnected from messenger")
        private_manager.disconnect(websocket, None)

async def handle_send_private_message(data: dict, sender_uid: UUID, db_session: AsyncSession):
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
        formatted_message = await PrivateMessage.create_private_message(db_session, message_data)
        formatted_message['frontId'] = data.get('frontId')
        
        # Отправляем сообщение всем устройствам отправителя
        await private_manager.send_to_user(str(sender_uid), formatted_message)

        # Отправляем сообщение всем устройствам получателя
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
        # Уведомляем отправителя на всех его устройствах
        for websocket in private_manager.user_connections.get(str(sender_uid), []):
            await private_manager.send_to_user(str(sender_uid), error_message)

async def handle_mark_as_read(data: dict, user_uid: UUID, db_session: AsyncSession):
    """
    Помечает сообщение как прочитанное.
    """
    try:
        message_uid = data.get("message_uid")
        if not message_uid:
            raise ValueError("Отсутствует message_uid")

        # Помечаем сообщение как прочитанное в базе данных
        message = await PrivateMessage.mark_as_read(db_session, message_uid)
        if not message:
            raise ValueError(f"Сообщение с UID {message_uid} не найдено")

        # Формируем ответ для отправки
        response = {
            "type": "message_read",
            "message_uid": str(message_uid),
            "read_at": datetime.utcnow().isoformat()
        }

        # Уведомляем отправителя на всех его устройствах
        if str(message.sender_uid) != str(user_uid):
            for websocket in private_manager.user_connections.get(message.sender_uid, []):
                await private_manager.send_to_user(str(message.sender_uid), response)

    except Exception as e:
        logger.error(f"Ошибка при обработке отметки сообщения как прочитанного: {e}")

async def handle_get_conversation(data: dict, user_uid: UUID, db_session: AsyncSession, websocket: WebSocket):
    """
    Возвращает переписку с другим пользователем.
    Отправляет историю переписки только на то устройство, которое запросило её.
    """
    try:
        other_user_uid = data.get("other_user_uid")
        if not other_user_uid:
            raise ValueError("Отсутствует other_user_uid в запросе")

        # Получаем историю переписки из базы данных
        messages = await PrivateMessage.get_conversation(
            db_session, 
            user1_uid=user_uid,
            user2_uid=UUID(other_user_uid)
        )
        
        # Формируем ответ
        response = {
            "type": "conversation",
            "other_user_uid": other_user_uid,
            "messages": messages,
            "request_id": data.get("request_id")
        }

        # Отправляем историю переписки только на конкретное устройство (websocket)
        await private_manager.send_to_specific_user(websocket, response)
        logger.debug(f"Отправляем историю переписки пользователю {user_uid} на запрашивающее устройство")

    except Exception as e:
        logger.error(f"Ошибка при получении истории переписки: {e}")
        error_message = {
            "type": "error",
            "message": "Не удалось получить историю переписки",
            "details": str(e),
            "request_id": data.get("request_id")
        }
        # Уведомляем об ошибке только запрашивающее устройство
        await private_manager.send_to_specific_user(websocket, error_message)

@get_session
async def handle_messenger_connection(websocket: WebSocket, user, db_session: AsyncSession = None):
    """
    Основной обработчик подключения к мессенджеру.
    """
    try:
        user_uid = UUID(user["user_uid"])
        
        # Инициализация соединения
        await initialize_messenger_connection(websocket, user_uid, db_session)
        
        # Обработка входящих сообщений
        await handle_private_messages(websocket, user_uid, db_session)

    except Exception as e:
        logger.error(f"Messenger connection error: {e}")
        await websocket.close(code=1011, reason="Internal server error")