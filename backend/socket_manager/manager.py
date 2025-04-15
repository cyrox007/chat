import asyncio
from uuid import UUID
from typing import Dict, List, Tuple, Optional
from fastapi import WebSocket

from utils.logger import setup_logger

logger = setup_logger(__name__)

class ConnectionManager:
    def __init__(self):
        # Для комнатных чатов: {room_uid: [(websocket, user_uid), ...]}
        self.room_connections: Dict[UUID, List[Tuple[WebSocket, UUID]]] = {}
        
        # Для приватных сообщений: {user_uid: websocket}
        self.user_connections: Dict[UUID, WebSocket] = {}
        
        # Для хранения активных диалогов: {user_uid: dialog_with_uid}
        self.active_dialogs: Dict[UUID, UUID] = {}

    async def connect_to_room(self, websocket: WebSocket, room_uid: UUID, user_uid: UUID):
        """Подключение к комнатному чату"""
        if room_uid not in self.room_connections:
            self.room_connections[room_uid] = []
        self.room_connections[room_uid].append((websocket, user_uid))
        logger.info(f"User {user_uid} connected to room {room_uid}")
        await self.broadcast_user_list(room_uid)

    async def connect_to_messenger(self, websocket: WebSocket, user_uid: UUID):
        """Подключение к мессенджеру (для приватных сообщений)"""
        self.user_connections[user_uid] = websocket
        logger.info(f"User {user_uid} connected to messenger")

    def disconnect(self, websocket: WebSocket, room_uid: Optional[UUID] = None):
        """Отключение от комнаты или мессенджера"""
        if room_uid is not None:
            # Отключение от комнаты
            if room_uid in self.room_connections:
                self.room_connections[room_uid] = [
                    conn for conn in self.room_connections[room_uid] 
                    if conn[0] != websocket
                ]
                if not self.room_connections[room_uid]:
                    del self.room_connections[room_uid]
                logger.info(f"User disconnected from room {room_uid}")
                asyncio.create_task(self.broadcast_user_list(room_uid))
        else:
            # Отключение от мессенджера
            for uid, ws in list(self.user_connections.items()):
                if ws == websocket:
                    del self.user_connections[uid]
                    logger.info(f"User {uid} disconnected from messenger")
                    break

    async def broadcast_user_list(self, room_uid: UUID):
        """Отправляет обновленный список пользователей в комнате"""
        if room_uid in self.room_connections:
            user_list = [str(user_uid) for _, user_uid in self.room_connections[room_uid]]
            message = {"type": "user_list", "users": user_list}
            await self.broadcast_to_room(room_uid, message)

    async def broadcast_to_room(self, room_uid: UUID, message: dict):
        """Отправляет сообщение всем в комнате"""
        if room_uid in self.room_connections:
            for connection, _ in self.room_connections[room_uid]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to room {room_uid}: {e}")

    async def send_to_user(self, user_uid: UUID, message: dict):
        # Преобразуем user_uid в UUID, если это строка
        if isinstance(user_uid, str):
            try:
                user_uid = UUID(user_uid)
            except ValueError:
                logger.error(f"Invalid UUID format for user_uid: {user_uid}")
                return

        # Логирование для отладки
        #logger.debug(f"Type of user_uid: {type(user_uid)}")
        #logger.debug(f"Types of keys in user_connections: {[type(k) for k in self.user_connections.keys()]}")

        if user_uid in self.user_connections:
            try:
                await self.user_connections[user_uid].send_json(message)
                logger.info(f"Message sent to user {user_uid}: {message}")
            except Exception as e:
                logger.error(f"Error sending to user {user_uid}: {e}")
                # Удаляем соединение, если оно недоступно
                del self.user_connections[user_uid]
                logger.warning(f"Removed user {user_uid} from active connections due to error")
        else:
            logger.error(f"User {user_uid} not found in active connections")
            #logger.debug(f"{self.user_connections}")

    def set_active_dialog(self, user_uid: UUID, dialog_with_uid: UUID):
        """Устанавливает активный диалог для пользователя"""
        self.active_dialogs[user_uid] = dialog_with_uid
        logger.info(f"User {user_uid} set active dialog with {dialog_with_uid}")

    def get_active_dialog(self, user_uid: UUID) -> Optional[UUID]:
        """Возвращает uid пользователя, с которым ведется активный диалог"""
        return self.active_dialogs.get(user_uid)