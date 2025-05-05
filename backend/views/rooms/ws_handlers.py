# System
import asyncio
import base64
import os
from pathlib import Path
from uuid import UUID
from datetime import datetime, timedelta
import uuid

# Other
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

# Custom
from components.user.model import Penalty
from components.room.model import Room, RoomBan, RoomMember
from components.message.model import Message
from components.decorators.db import get_session
from utils.logger import setup_logger
from utils.file_handler import save_file
from settings import config
from socket_manager import room_manager as manager

# Создаем логгер для этого модуля
logger = setup_logger(__name__)

# Init ws manager
# manager = ConnectionManager()

# Ограничение длянниы имени файла
MAX_FILENAME_LENGTH = 255

# Инициализация подключения к комнате
async def initialize_websocket(websocket: WebSocket, db_session, room_uid: UUID, user_uid: UUID):
    """Обновленная инициализация с проверкой бана"""
    # Проверяем бан перед подключением
    is_banned = await RoomBan.is_user_banned(db_session, room_uid, user_uid)
    if is_banned:
        ban_info = await RoomBan.get_active_ban_info(db_session, room_uid, user_uid)
        reason = "User is banned" + (f": {ban_info['reason']}" if ban_info and ban_info.get('reason') else "")
        # Ограничиваем длину reason для WebSocket
        reason = reason[:120]  # Максимальная длина для WebSocket close reason
        await websocket.close(code=4001, reason=reason)
        return

    # Остальная логика инициализации...
    room = await Room.get_room_by_uid(db_session, room_uid)
    if not room:
        logger.warning(f"Комната не найдена: {room_uid}")
        await websocket.close(code=1008, reason="Room not found")
        return

    # Подключение пользователя к комнате
    await manager.connect_to_room(websocket, room_uid, user_uid)
    await manager.update_user_activity(db_session, user_uid)

    # Проверка наличия активного mute
    active_mute = await Penalty.get_active_mute(db_session, user_uid)
    if active_mute:
        await websocket.send_json({
            "type": "mute_status",
            "status": "muted",
            "details": {
                "expires_at": active_mute["expires_at"],
                "reason": active_mute["reason"],
            },
        })

    # Отправка начальных данных
    await send_initial_data(websocket, db_session, room_uid, user_uid)

async def send_initial_data(websocket: WebSocket, db_session, room_uid: UUID, user_uid: UUID):
    # Получаем информацию о комнате с модераторами
    room_info = await Room.get_room_with_details(db_session, room_uid)
    if not room_info:
        return
        
    # Отправляем информацию о комнате
    await websocket.send_json({
        "type": "room_info",
        "room": room_info
    })
    
    # Отправляем последние сообщения
    last_messages = await Message.get_last_messages(db_session, room_uid, limit=5)
    await websocket.send_json({
        "type": "initial_data",
        "messages": last_messages
    })

async def process_incoming_messages(websocket: WebSocket, room_uid: UUID, user_uid: UUID, db_session):
    try:
        while True:
            data = await websocket.receive_json()
            
            # Добавляем обработку moderator_action
            if data.get("type") == "moderator_action":
                response = await handle_moderator_action(data, db_session, user_uid)
                await manager.broadcast_to_room(room_uid, response)
            elif data.get("type") == "ban_user":
                response = await handle_ban_user(data, db_session, room_uid, user_uid)
            else:
                content_type = data.get("content_type", "text")
                
                # Остальная обработка сообщений
                if content_type == "text":
                    await handle_text_message(data, room_uid, user_uid, db_session)
                elif content_type in ["file", "image", "video"]:
                    await handle_file_message(data, room_uid, user_uid, db_session)
                elif content_type == "voice":
                    await handle_audio_message(data, room_uid, user_uid, db_session)
                else:
                    logger.warning(f"Неизвестный тип контента: {content_type}")

            await manager.update_user_activity(db_session, user_uid)
    except WebSocketDisconnect:
        logger.info("WebSocket отключен")
        manager.disconnect(websocket, room_uid)

async def handle_text_message(data: dict, room_uid: UUID, user_uid: UUID, db_session: AsyncSession):  
    content = data.get("content")
    if not content:
        logger.warning("Получено пустое текстовое сообщение")
        return
    
    message_data = {
        "content": content,
        "content_type": "text",
        "sender_uid": str(user_uid),
        "room_uid": str(room_uid),
        "reply_to_uid": data.get("reply_to_uid"),
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Создаем сообщение в БД
        formatted_message = await Message.create_message(db_session, message_data)
        formatted_message['frontId'] = data.get('frontId')  # Сохраняем frontId
        
        await manager.broadcast_to_room(room_uid, formatted_message)
        logger.info(f"Сообщение отправлено в комнату {room_uid}: {formatted_message}")

    except Exception as e:
        logger.error(f"Ошибка обработки текстового сообщения: {e}")
        raise

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
        await manager.broadcast_to_room(room_uid, error_message)
        return

    saved_files = []
    errors = []

    for file_data in files:
        try:
            # Извлекаем данные о файле
            file_url = file_data.get("url")
            file_type = file_data.get("type")
            file_name = file_data.get("name")
            file_size = file_data.get("size")

            if not all([file_url, file_type, file_name, file_size]):
                raise ValueError("Missing required file data")

            file_metadata = {
                "url": file_url,
                "type": file_type,
                "name": file_name,
                "size": file_size,
            }
            
            saved_file_url = save_file(file_metadata)
            saved_files.append({
                "url": saved_file_url,
                "type": file_type,
                "name": file_name,
                "size": file_size,
            })

        except Exception as e:
            logger.error(f"Ошибка при обработке файла '{file_data.get('name')}': {str(e)}")
            errors.append({
                "file_name": file_data.get("name"),
                "error": str(e),
            })

    if not saved_files:
        error_message = {
            "type": "error",
            "message": "All files failed to process.",
            "details": errors,
        }
        await manager.broadcast_to_room(room_uid, error_message)
        return

    # Создаём данные для сообщения
    message_data = {
        "content": data.get("content", ""),
        "content_type": data.get('content_type', 'other'),
        "sender_uid": str(user_uid),
        "room_uid": str(room_uid),
        "media_metadata": {
            "files": saved_files,
        },
        "reply_to_uid": data.get("reply_to_uid"),
    }

    try:
        formatted_message = await Message.create_message(db_session, message_data)
        formatted_message['frontId'] = data.get('frontId')
        await manager.broadcast_to_room(room_uid, formatted_message)
        logger.info(f"Файловое сообщение отправлено в комнату {room_uid}: {formatted_message}")

        if errors:
            partial_error_message = {
                "type": "partial_error",
                "message": "Some files failed to process.",
                "details": {
                    "success": saved_files,
                    "errors": errors,
                },
            }
            await manager.broadcast_to_room(room_uid, partial_error_message)
    except Exception as e:
        logger.error(f"Ошибка при создании файлового сообщения: {e}")
        raise

async def handle_audio_message(data: dict, room_uid: UUID, user_uid: UUID, db_session):
    audio_url: str = data.get("media_metadata", {}).get("voice")
    if not audio_url:
        logger.warning("Получено пустое аудио сообщение")
        return

    try:
        mime_type, encoded_data = audio_url.split(',', 1)
        file_content = base64.b64decode(encoded_data)

        if len(file_content) > config.MAX_FILE_SIZE:
            logger.warning(f"Аудиофайл слишком большой: {len(file_content)} байт")
            return

        extension = mime_type.split(';')[0].split('/')[1]
        upload_dir = Path("uploads/audio")
        os.makedirs(upload_dir, exist_ok=True)

        file_name = f"{uuid.uuid4()}.{extension}"
        file_path = upload_dir / file_name

        with open(file_path, "wb") as f:
            f.write(file_content)

        saved_audio_url = f"{config.BASE_URL}/uploads/audio/{file_name}"

        message_data = {
            "content": saved_audio_url,
            "content_type": "audio",
            "sender_uid": str(user_uid),
            "room_uid": str(room_uid),
            "reply_to_uid": data.get("reply_to_uid"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        formatted_message = await Message.create_message(db_session, message_data)
        formatted_message['frontId'] = data.get('frontId')
        await manager.broadcast_to_room(room_uid, formatted_message)
        logger.info(f"Аудио сообщение отправлено в комнату {room_uid}: {formatted_message}")

    except Exception as e:
        logger.error(f"Ошибка при обработке аудио: {e}")

async def handle_moderator_action(data: dict, db_session: AsyncSession, user_uid: UUID):
    """
    Обработчик действий с модераторами.
    """
    try:
        room_uid = UUID(data['room_uid'])
        target_user_uid = UUID(data['target_user_uid'])
        action = data['action']

        # Проверяем, что инициатор - владелец комнаты
        room = await Room.get_room_by_uid(db_session, room_uid)
        if not room or str(room.owner_uid) != str(user_uid):
            return {
                "type": "error",
                "message": "Только владелец комнаты может управлять модераторами"
            }

        # Обрабатываем действие
        if action == "add_moderator":
            try:
                await Room.add_moderator(db_session, room_uid, target_user_uid)
                # Получаем обновленный список модераторов
                moderators = await RoomMember.get_moderators(db_session, room_uid)

                return {
                    "type": "moderator_added",
                    "room_uid": str(room_uid),
                    "target_user_uid": str(target_user_uid),
                    "moderators": [str(m) for m in moderators],
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                return {
                    "type": "error",
                    "message": "Пользователь уже является модератором"
                }
                       

        elif action == "remove_moderator":
            await Room.remove_moderator(db_session, room_uid, target_user_uid)

            # Получаем обновленный список модераторов
            moderators = await RoomMember.get_moderators(db_session, room_uid)

            return {
                "type": "moderator_removed",
                "room_uid": str(room_uid),
                "target_user_uid": str(target_user_uid),
                "moderators": [str(m) for m in moderators],
                "timestamp": datetime.utcnow().isoformat()
            }

        else:
            return {
                "type": "error",
                "message": "Неизвестное действие"
            }

    except Exception as e:
        logger.error(f"Ошибка обработки moderator_action: {e}")
        return {
            "type": "error",
            "message": "Внутренняя ошибка сервера"
        }
    
async def handle_ban_user(data: dict, db_session: AsyncSession, room_uid: UUID, user_uid: UUID):
    """
    Обработчик бана пользователя в комнате
    """
    try:
        target_user_uid = data.get('target_user_uid', None)
        reason = data.get('reason', 'Нарушение правил чата')
        ban_duration = timedelta(days=7) if not data.get('permanent', False) else None
        
        if target_user_uid is None:
            return {
                "type": 'error',
                'message': 'targer uid not found'
            }
        # Проверяем права (владелец или модератор)
        room = await Room.get_room_by_uid(db_session, room_uid)
        if not room:
            return {"type": "error", "message": "Комната не найдена"}
        
        is_owner = str(room.owner_uid) == str(user_uid)
        is_moderator = await RoomMember.is_moderator(db_session, room_uid, user_uid)
        
        if not (is_owner or is_moderator):
            return {
                "type": "error",
                "message": "Недостаточно прав для блокировки пользователя"
            }
        print(target_user_uid)
        # Создаем запись о бане
        ban = await RoomBan.ban_user(
            db_session,
            room_uid=room_uid,
            user_uid=target_user_uid,
            banned_by_uid=user_uid,
            reason=reason,
            ban_duration=ban_duration
        )
        
        # Получаем соединение пользователя
        target_connection = manager.get_user_connection(room_uid, target_user_uid)
        
        # Если пользователь онлайн - отправляем уведомление перед отключением
        if target_connection:
            ban_notification = {
                "type": "user_banned",
                "room_uid": str(room_uid),
                "reason": reason,
                "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
                "permanent": ban.expires_at is None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                await target_connection.send_json(ban_notification)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления о бане: {e}")
        
        # Отключаем пользователя от комнаты
        if target_connection:
            await manager.disconnect_user_from_room(room_uid, target_user_uid)
        
        # Уведомляем остальных участников
        return {
            "type": "user_banned_notification",
            "room_uid": str(room_uid),
            "target_user_uid": str(target_user_uid),
            "banned_by": str(user_uid),
            "reason": reason,
            "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка обработки бана пользователя: {e}")
        return {
            "type": "error",
            "message": "Внутренняя ошибка сервера"
        }

@get_session
async def handle_websocket_connection(websocket: WebSocket, room_uid: str, user, db_session: AsyncSession = None):
    try:
        room_uid = UUID(room_uid)
        user_uid = UUID(user["user_uid"])

        await initialize_websocket(websocket, db_session, room_uid, user_uid)
        await process_incoming_messages(websocket, room_uid, user_uid, db_session)
    except Exception as e:
        logger.error(f"Ошибка WebSocket: {e}")
        await websocket.close(code=1011, reason="Internal server error")