import asyncio
import base64
import os
from pathlib import Path
from uuid import UUID
from datetime import datetime
import uuid
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

async def initialize_websocket(websocket: WebSocket, db_session, room_uid: UUID, user_uid: UUID):
    # Проверка существования комнаты
    room = Room.get_room_by_uid(db_session, room_uid)
    if not room:
        logger.warning(f"Комната не найдена: {room_uid}")
        await websocket.close(code=1008, reason="Room not found")
        return

    # Подключение пользователя к комнате
    await manager.connect(websocket, room_uid, user_uid)

    # Отправка начальных данных
    await send_initial_data(websocket, db_session, room_uid, user_uid)

async def send_initial_data(websocket: WebSocket, db_session, room_uid: UUID, user_uid: UUID):
    # Отправляем текущий список участников
    """ if room_uid in manager.active_connections:
        user_list = [str(user_uid) for _, user_uid in manager.active_connections[room_uid]] """
        

    # Отправляем последние сообщения
    last_messages = Message.get_last_messages(db_session, room_uid, limit=5)
    formatted_messages = format_messages(last_messages)
    await websocket.send_json({"type": "initial_data", "messages": formatted_messages})

def format_messages(messages):
    return [
        {
            "type": "message",
            "uid": str(msg.uid),
            "content": msg.text,
            "content_type": msg.content_type,
            "sender": {
                "uid": str(msg.author_uid),
                "name": msg.author.username if msg.author else "Unknown",
                "avatar": msg.author.avatar if msg.author else None,
            },
            "room_uid": str(msg.room_uid),
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]

async def process_incoming_messages(websocket: WebSocket, room_uid: UUID, user_uid: UUID, db_session):
    try:
        while True:
            data = await websocket.receive_json()
            content_type = data.get("content_type", "text")

            # Обработка разных типов контента
            if content_type == "text":
                await handle_text_message(data, room_uid, user_uid, db_session)
            elif content_type == "file":
                await handle_file_message(data, room_uid, user_uid, db_session)
            elif content_type == "audio":
                await handle_audio_message(data, room_uid, user_uid, db_session)
            else:
                logger.warning(f"Неизвестный тип контента: {content_type}")

    except WebSocketDisconnect:
        logger.info("WebSocket отключен")
        manager.disconnect(websocket, room_uid)

async def handle_text_message(data:dict, room_uid: UUID, user_uid: UUID, db_session):
    content = data.get("content")
    if not content:
        logger.warning("Получено пустое текстовое сообщение")
        return
    
    message_data = {
        "content": content,
        "content_type": "text",
        "sender_uid": str(user_uid),
        "room_uid": str(room_uid),
        "timestamp": datetime.utcnow().isoformat(),
    }

    new_message = Message.create_message(db_session, message_data)
    new_message['tempId'] = data.get('tempId')
    await manager.broadcast(room_uid, new_message)
    logger.info(f"Текстовое сообщение отправлено в комнату {room_uid}: {new_message}")

async def handle_file_message(data: dict, room_uid: UUID, user_uid: UUID, db_session):
    files = data.get("files", [])
    if not files:
        logger.warning("Получено пустое файловое сообщение")
        return

    saved_files = []
    for file_data in files:
        # Извлекаем MIME-тип и кодировку из Base64
        mime_type, encoded_data = file_data.split(',', 1)
        extension = mime_type.split(';')[0].split('/')[1]  # Извлекаем расширение файла
        file_name = f"{uuid.uuid4()}.{extension}"
        file_path = Path("uploads") / file_name
        os.makedirs("uploads", exist_ok=True)

        # Декодируем и сохраняем файл
        with open(file_path, "wb") as f:
            file_content = base64.b64decode(encoded_data)
            f.write(file_content)

        saved_files.append(str(file_path))

    # Создаём данные для сообщения
    message_data = {
        "content": data.get("text", ""),  # Текст сообщения (если есть)
        "content_type": "file",
        "sender_uid": str(user_uid),
        "room_uid": str(room_uid),
        "media_metadata": {  # Метаданные для файлов
            "files": saved_files,
        },
    }

    # Создаём сообщение в базе данных
    new_message = Message.create_message(db_session, message_data)
    new_message['tempId'] = data.get('tempId')

    # Рассылаем сообщение участникам комнаты
    await manager.broadcast(room_uid, new_message)
    logger.info(f"Файловое сообщение отправлено в комнату {room_uid}: {new_message}")

async def handle_audio_message(data, room_uid: UUID, user_uid: UUID, db_session):
    audio_url = data.get("audio")
    if not audio_url:
        logger.warning("Получено пустое аудио сообщение")
        return

    message_data = {
        "content": audio_url,
        "content_type": "audio",
        "sender_uid": str(user_uid),
        "room_uid": str(room_uid),
        "timestamp": datetime.utcnow().isoformat(),
    }

    new_message = Message.create_message(db_session, message_data)
    await manager.broadcast(room_uid, new_message)
    logger.info(f"Аудио сообщение отправлено в комнату {room_uid}: {new_message}")

@get_session
async def handle_websocket_connection(websocket: WebSocket, room_uid: str, user, db_session=None):
    try:
        # Инициализация соединения
        room_uid = UUID(room_uid)
        user_uid = UUID(user["user_uid"])
        await initialize_websocket(websocket, db_session, room_uid, user_uid)

        # Обработка входящих сообщений
        await process_incoming_messages(websocket, room_uid, user_uid, db_session)

    except Exception as e:
        logger.error(f"Ошибка WebSocket: {e}")
        await websocket.close(code=1011, reason="Internal server error")