# System
import base64
import mimetypes
import os
from pathlib import Path
from uuid import UUID
from datetime import datetime
import uuid

# Other
from fastapi import WebSocket, WebSocketDisconnect

# Custom
from components.room.model import Room
from components.message.model import Message
from components.decorators.db import get_session
from utils.logger import setup_logger
from utils.file_handler import save_file
from settings import config
from socket_manager.manager import ConnectionManager

# Создаем логгер для этого модуля
logger = setup_logger(__name__)

# Init ws manager
manager = ConnectionManager()

# Ограничение длянниы имени файла
MAX_FILENAME_LENGTH = 255

# Инициализация подключения к комнате
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
            "media_metadata": msg.media_metadata,
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
            elif content_type == "file" or content_type == 'image' or content_type == 'video':
                await handle_file_message(data, room_uid, user_uid, db_session)
            elif content_type == "voice":
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
    new_message['frontId'] = data.get('frontId')
    await manager.broadcast(room_uid, new_message)
    logger.info(f"Текстовое сообщение отправлено в комнату {room_uid}: {new_message}")

async def handle_file_message(data: dict, room_uid: UUID, user_uid: UUID, db_session):
    files = data.get("media_metadata", {}).get("files", [])
    if not files:
        logger.warning("Получено пустое файловое сообщение")
        return

    # Проверка количества файлов
    if len(files) > config.MAX_FILES_LIMIT:
        error_message = {
            "type": "error",
            "message": f"Too many files. Maximum allowed is {config.MAX_FILES_LIMIT}.",
            "details": {
                "received_files_count": len(files),
                "max_allowed_files": config.MAX_FILES_LIMIT,
            },
        }
        await manager.broadcast(room_uid, error_message)
        return

    saved_files = []
    errors = []

    for file_data in files:
        try:
            # Извлекаем данные о файле
            file_url = file_data.get("url")
            file_type = file_data.get("type")  # Тип файла (image, video, audio, etc.)
            file_name = file_data.get("name")  # Оригинальное имя файла
            file_size = file_data.get("size")  # Размер файла

            # Проверяем, что все необходимые поля присутствуют
            if not all([file_url, file_type, file_name, file_size]):
                raise ValueError("Missing required file data")

            # Сохраняем файл через утилиту
            file_metadata = {
                "url": file_url,
                "type": file_type,  # Используем нормализованный тип
                "name": file_name,
                "size": file_size,
            }
            
            saved_file_url = save_file(file_metadata)
            saved_files.append({
                "url": saved_file_url,
                "type": file_type,  # Сохраняем нормализованный тип
                "name": file_name,
                "size": file_size,
            })

        except Exception as e:
            # Логируем ошибку и добавляем её в список
            logger.error(f"Ошибка при обработке файла '{file_data.get('name')}': {str(e)}")
            errors.append({
                "file_name": file_data.get("name"),
                "error": str(e),
            })

    # Если ни один файл не был сохранён, отправляем ошибку клиенту
    if not saved_files:
        error_message = {
            "type": "error",
            "message": "All files failed to process.",
            "details": errors,
        }
        await manager.broadcast(room_uid, error_message)
        return

    # Создаём данные для сообщения
    message_data = {
        "content": data.get("content", ""),  # Преобразуем в JSON-строку
        "content_type": data.get('content_type', 'other'),  # Используем тип первого файла
        "sender_uid": str(user_uid),
        "room_uid": str(room_uid),
        "media_metadata": {
            "files": saved_files,
        },
    }

    # Создаём сообщение в базе данных
    new_message = Message.create_message(db_session, message_data)
    new_message['frontId'] = data.get('frontId')

    # Рассылаем сообщение участникам комнаты
    await manager.broadcast(room_uid, new_message) 
    logger.info(f"Файловое сообщение отправлено в комнату {room_uid}: {new_message}")

    # Если были ошибки, отправляем уведомление о частичной обработке
    if errors:
        partial_error_message = {
            "type": "partial_error",
            "message": "Some files failed to process.",
            "details": {
                "success": saved_files,
                "errors": errors,
            },
        }
        await manager.broadcast(room_uid, partial_error_message)

async def handle_audio_message(data: dict, room_uid: UUID, user_uid: UUID, db_session):
    audio_url: str = data.get("media_metadata", {}).get("voice")
    if not audio_url:
        logger.warning("Получено пустое аудио сообщение")
        return

    try:
        # Извлекаем MIME-тип и кодировку из Base64
        mime_type, encoded_data = audio_url.split(',', 1)
        file_content = base64.b64decode(encoded_data)

        # Проверка размера файла
        if len(file_content) > config.MAX_FILE_SIZE:
            logger.warning(f"Аудиофайл слишком большой: {len(file_content)} байт")
            return

        # Определение расширения файла
        extension = mime_type.split(';')[0].split('/')[1]

        # Создаем папку для аудио
        upload_dir = Path("uploads/audio")
        os.makedirs(upload_dir, exist_ok=True)

        # Генерируем уникальное имя файла
        file_name = f"{uuid.uuid4()}.{extension}"
        file_path = upload_dir / file_name

        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Формируем URL для доступа к файлу
        saved_audio_url = f"{config.BASE_URL}/uploads/audio/{file_name}"

        # Создаём данные для сообщения
        message_data = {
            "content": saved_audio_url,
            "content_type": "audio",
            "sender_uid": str(user_uid),
            "room_uid": str(room_uid),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Создаём сообщение в базе данных
        new_message = Message.create_message(db_session, message_data)
        new_message['frontId'] = data.get('frontId')

        # Рассылаем сообщение участникам комнаты
        await manager.broadcast(room_uid, new_message)
        logger.info(f"Аудио сообщение отправлено в комнату {room_uid}: {new_message}")

    except Exception as e:
        logger.error(f"Ошибка при обработке аудио: {e}")

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