import asyncio
from uuid import UUID
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from components.room.model import Room
from components.message.model import Message
from components.decorators.db import get_session
from utils.logger import setup_logger  # Импортируем централизованный логгер

# Создаем логгер для этого модуля
logger = setup_logger(__name__)

# Менеджер для хранения активных соединений
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket, room_uid: UUID, user_uid: UUID):
        if room_uid not in self.active_connections:
            self.active_connections[room_uid] = []
        self.active_connections[room_uid].append((websocket, user_uid))
        logger.info(f"Пользователь {user_uid} подключен к комнате {room_uid}")

        # Уведомляем всех участников о новом пользователе
        await self.broadcast_user_list(room_uid)

    def disconnect(self, websocket, room_uid: UUID):
        if room_uid in self.active_connections:
            self.active_connections[room_uid] = [
                conn for conn in self.active_connections[room_uid] if conn[0] != websocket
            ]
            if not self.active_connections[room_uid]:
                del self.active_connections[room_uid]
            logger.info(f"Пользователь отключен от комнаты {room_uid}")

        # Уведомляем всех участников об изменении списка пользователей
        asyncio.create_task(self.broadcast_user_list(room_uid))

    async def broadcast_user_list(self, room_uid: UUID):
        if room_uid in self.active_connections:
            user_list = [str(user_uid) for _, user_uid in self.active_connections[room_uid]]
            message = {"type": "user_list", "users": user_list}
            await self.broadcast(room_uid, message)

    async def broadcast(self, room_uid: UUID, message: dict):
        if room_uid in self.active_connections:
            for connection, _ in self.active_connections[room_uid]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Ошибка при отправке сообщения: {e}")

manager = ConnectionManager()

@get_session
async def handle_websocket_connection(websocket: WebSocket, room_uid: str, user, db_session=None):
    logger.info("Обработка WebSocket соединения...")
    
    try:
        room_uid = UUID(room_uid)
        user_uid = UUID(user["user_uid"])
        room = Room.get_room_by_uid(db_session, room_uid)
        if not room:
            logger.warning(f"Комната не найдена: {room_uid}")
            await websocket.close(code=1008, reason="Room not found")
            return

        # Подключаем пользователя к комнате
        await manager.connect(websocket, room_uid, user_uid)

        # Отправляем новому пользователю текущий список участников
        if room_uid in manager.active_connections:
            user_list = [str(user_uid) for _, user_uid in manager.active_connections[room_uid]]
            await websocket.send_json({"type": "user_list", "users": user_list})

        try:
            while True:
                data = await websocket.receive_text()
                message_data = {
                    "content": data,
                    "sender_uid": str(user_uid),
                    "room_uid": str(room_uid),
                    "content_type": "text",
                    "timestamp": datetime.utcnow().isoformat()
                }

                # Сохраняем сообщение в базу данных
                new_message = Message.create_message(db_session, message_data)
                logger.debug(f"Сообщение сохранено в базе данных: {new_message.uid}")

                # Рассылаем сообщение всем участникам комнаты
                await manager.broadcast(room_uid, {
                    "type": "message",
                    "uid": str(new_message.uid),
                    "content": new_message.text,
                    "content_type": new_message.content_type,
                    "sender_uid": str(new_message.author_uid),
                    "room_uid": str(new_message.room_uid),
                    "created_at": new_message.created_at.isoformat()
                })
                logger.info(f"Сообщение отправлено в комнату {room_uid}: {new_message.text}")

        except WebSocketDisconnect:
            logger.info("WebSocket отключен")
            manager.disconnect(websocket, room_uid)

    except Exception as e:
        logger.error(f"Ошибка WebSocket: {e}")
        await websocket.close(code=1011, reason="Internal server error")