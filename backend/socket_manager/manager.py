import asyncio
from datetime import datetime
from uuid import UUID
from typing import Dict, List, Tuple, Optional
from fastapi import WebSocket

from components.user.model import User
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ConnectionManager:
    def __init__(self):
        # Для комнатных чатов: {room_uid: [(websocket, user_uid), ...]}
        self.room_connections: Dict[UUID, List[Tuple[WebSocket, UUID]]] = {}

        # Для приватных сообщений: {user_uid: [websocket, ...]}
        self.user_connections: Dict[UUID, List[WebSocket]] = {}

        # Для хранения активных диалогов: {websocket: dialog_with_uid}
        self.active_dialogs: Dict[WebSocket, UUID] = {}

        # Время последней активности
        self.user_last_seen: Dict[UUID, datetime] = {}

    async def connect_to_room(self, websocket: WebSocket, room_uid: UUID, user_uid: UUID):
        """Подключение к комнатному чату"""
        if room_uid not in self.room_connections:
            self.room_connections[room_uid] = []

        self.room_connections[room_uid].append((websocket, user_uid))
        logger.info(
            f"Пользователь {user_uid} подключился к комнате {room_uid}")
        await self.broadcast_user_list(room_uid)

    async def connect_to_messenger(self, websocket: WebSocket, user_uid: UUID):
        """Подключение к мессенджеру (для приватных сообщений)"""
        if user_uid not in self.user_connections:
            self.user_connections[user_uid] = []

        self.user_connections[user_uid].append(websocket)
        logger.info(f"Пользователь {user_uid} подключился к мессенджеру")

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
                logger.info(f"Пользователь отключился от комнаты {room_uid}")
                asyncio.create_task(self.broadcast_user_list(room_uid))
        else:
            # Отключение от мессенджера
            for uid, connections in list(self.user_connections.items()):
                if websocket in connections:
                    connections.remove(websocket)
                    if not connections:  # Если больше нет соединений для пользователя
                        del self.user_connections[uid]
                    logger.info(
                        f"Пользователь {uid} отключился от мессенджера")
                    break

    async def broadcast_user_list(self, room_uid: UUID):
        """Отправляет обновленный список пользователей в комнате"""
        if room_uid in self.room_connections:
            user_list = [str(user_uid)
                         for _, user_uid in self.room_connections[room_uid]]
            message = {"type": "user_list", "users": user_list}
            await self.broadcast_to_room(room_uid, message)

    async def broadcast_to_room(self, room_uid: UUID, message: dict):
        """Отправляет сообщение всем в комнате"""
        if room_uid in self.room_connections:
            for connection, _ in self.room_connections[room_uid]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(
                        f"Ошибка при отправке сообщения в комнату {room_uid}: {e}")

    async def send_to_user(self, user_uid: UUID, message: dict):
        # Преобразуем user_uid в UUID, если это строка
        if isinstance(user_uid, str):
            try:
                user_uid = UUID(user_uid)
            except ValueError:
                logger.error(
                    f"Некорректный формат UUID для user_uid: {user_uid}")
                return

        # logger.debug(f"Ищем пользователя {user_uid} среди подключенных")
        if user_uid in self.user_connections:
            # logger.debug(f"Нашли подключения {user_uid}: {self.user_connections[user_uid]}")
            for websocket in self.user_connections[user_uid]:
                # logger.debug(f"Отправляем на клиент {websocket}")
                try:
                    await websocket.send_json(message)
                    logger.info(
                        f"Сообщение успешно отправлено пользователю {user_uid}")
                except Exception as e:
                    logger.error(
                        f"Ошибка при отправке сообщения пользователю {user_uid}: {e}")
                    # Удаляем недоступное соединение
                    self.user_connections[user_uid].remove(websocket)
                    # Если больше нет соединений
                    if not self.user_connections[user_uid]:
                        del self.user_connections[user_uid]
                    logger.warning(
                        f"Соединение с пользователем {user_uid} удалено из-за ошибки")
        else:
            logger.error(
                f"Пользователь {user_uid} не найден среди активных соединений")

    def set_active_dialog(self, websocket: WebSocket, dialog_with_uid: UUID):
        """Устанавливает активный диалог для пользователя"""
        self.active_dialogs[websocket] = dialog_with_uid
        logger.info(
            f"Для WebSocket установлен активный диалог с пользователем {dialog_with_uid}")

    def get_active_dialog(self, websocket: WebSocket) -> Optional[UUID]:
        """Возвращает UID пользователя, с которым ведется активный диалог"""
        return self.active_dialogs.get(websocket)

    async def send_to_specific_user(self, websocket: WebSocket, message: dict):
        """
        Отправляет сообщение только на конкретное устройство (websocket).
        """
        try:
            await websocket.send_json(message)
            logger.info(f"Сообщение отправлено на конкретное устройство")
        except Exception as e:
            logger.error(
                f"Ошибка при отправке сообщения на конкретное устройство: {e}")
            # Удаляем недоступное соединение
            for user_uid, connections in list(self.user_connections.items()):
                if websocket in connections:
                    connections.remove(websocket)
                    if not connections:  # Если больше нет соединений для пользователя
                        del self.user_connections[user_uid]
                    logger.warning(
                        f"Удалено недоступное соединение для пользователя {user_uid}")
                    break

    async def update_user_activity(self, db_session, user_uid: UUID):
        """Обновляет время последней активности пользователя"""
        self.user_last_seen[user_uid] = datetime.now()

        # Обновляем last_online в базе данных
        User.update_last_online(db_session, user_uid)

    async def check_user_activity(self):
        """Периодическая проверка активности пользователей"""
        while True:
            current_time = datetime.now()
            for user_uid, last_seen in list(self.user_last_seen.items()):
                if (current_time - last_seen).total_seconds() > 30:
                    # Считаем пользователя оффлайн
                    del self.user_last_seen[user_uid]
                    #asyncio.create_task(self.broadcast_user_status(user_uid, "offline"))
            await asyncio.sleep(10)  # Проверяем каждые 10 секунд
