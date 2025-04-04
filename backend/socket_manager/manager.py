import asyncio
from uuid import UUID

from sqlalchemy.orm import Session

from utils.logger import setup_logger


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