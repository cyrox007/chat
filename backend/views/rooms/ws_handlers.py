import base64
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from components.decorators.db import get_session
from components.message.model import Message
from components.notification.space_message_delivery import notify_online_space_members
from components.realtime import realtime_service
from components.room.model import Room, RoomBan, RoomMember
from components.user.model import Penalty
from settings import config
from socket_manager import room_manager as manager
from utils.file_handler import save_file
from utils.logger import setup_logger

logger = setup_logger(__name__)

MAX_FILENAME_LENGTH = 255


async def initialize_websocket(
    websocket: WebSocket,
    db_session: AsyncSession,
    room_uid: UUID,
    user_uid: UUID,
) -> bool:
    if await RoomBan.is_user_banned(db_session, room_uid, user_uid):
        ban_info = await RoomBan.get_active_ban_info(db_session, room_uid, user_uid)
        reason = "Доступ к пространству ограничен"
        if ban_info and ban_info.get("reason"):
            reason = f"{reason}: {ban_info['reason']}"
        await websocket.close(code=4001, reason=reason[:120])
        return False

    room = await Room.get_room_by_uid(db_session, room_uid)
    if not room or not room.is_active:
        logger.warning("Пространство не найдено: %s", room_uid)
        await websocket.close(code=1008, reason="Space not found")
        return False

    await manager.connect_to_room(websocket, room_uid, user_uid)
    await manager.update_user_activity(db_session, user_uid)

    active_mute = await Penalty.get_active_mute(db_session, user_uid)
    if active_mute:
        await websocket.send_json(
            {
                "type": "mute_status",
                "status": "muted",
                "details": {
                    "expires_at": active_mute["expires_at"],
                    "reason": active_mute["reason"],
                },
            }
        )

    await send_initial_data(websocket, db_session, room_uid)
    return True


async def send_initial_data(
    websocket: WebSocket,
    db_session: AsyncSession,
    room_uid: UUID,
) -> None:
    room_info = await Room.get_room_with_details(db_session, room_uid)
    if not room_info:
        return

    await websocket.send_json({"type": "room_info", "room": room_info})

    # Re-send a recent window after reconnect. The SPA de-duplicates by the
    # canonical server uid and the client event id (`frontId`).
    last_messages = await Message.get_last_messages(db_session, room_uid, limit=20)
    await websocket.send_json(
        {
            "type": "initial_data",
            "messages": last_messages,
            "resume": True,
        }
    )


async def _rate_limit_message(websocket: WebSocket, user_uid: UUID) -> bool:
    allowed = await realtime_service.allow_action(
        user_uid=user_uid,
        bucket="space-message",
        limit=config.REALTIME_MESSAGE_RATE_LIMIT,
        window_seconds=config.REALTIME_MESSAGE_RATE_WINDOW_SECONDS,
    )
    if allowed:
        return True

    await websocket.send_json(
        {
            "type": "rate_limited",
            "scope": "message",
            "retry_after": config.REALTIME_MESSAGE_RATE_WINDOW_SECONDS,
        }
    )
    return False


def _event_scope(room_uid: UUID) -> str:
    return f"space-message:{room_uid}"


async def _claim_client_event(
    websocket: WebSocket,
    room_uid: UUID,
    user_uid: UUID,
    front_id: str | None,
) -> bool:
    claimed = await realtime_service.claim_event(
        user_uid=user_uid,
        scope=_event_scope(room_uid),
        event_id=front_id,
    )
    if claimed:
        return True

    await websocket.send_json(
        {
            "type": "duplicate_ignored",
            "frontId": front_id,
            "scope": "space_message",
        }
    )
    return False


async def _release_client_event(room_uid: UUID, user_uid: UUID, front_id: str | None) -> None:
    await realtime_service.release_event(
        user_uid=user_uid,
        scope=_event_scope(room_uid),
        event_id=front_id,
    )


async def _notify_online_members(
    db_session: AsyncSession,
    room_uid: UUID,
    user_uid: UUID,
    formatted_message: dict,
) -> None:
    # Secondary alerts are deliberately best-effort. The canonical room message
    # has already been persisted and broadcast; notification failure must never
    # turn a successful send into a client-visible retry/duplicate situation.
    await notify_online_space_members(
        db_session,
        room_uid=room_uid,
        sender_uid=user_uid,
        formatted_message=formatted_message,
    )


async def process_incoming_messages(
    websocket: WebSocket,
    room_uid: UUID,
    user_uid: UUID,
    db_session: AsyncSession,
) -> None:
    while True:
        data = await websocket.receive_json()
        frame_type = data.get("type")

        if frame_type in {"heartbeat", "pong"}:
            await manager.touch_connection(websocket)
            continue

        await manager.touch_connection(websocket)

        if frame_type == "moderator_action":
            response = await handle_moderator_action(data, db_session, user_uid)
            await manager.broadcast_to_room(room_uid, response)
            await manager.update_user_activity(db_session, user_uid)
            continue

        if frame_type == "ban_user":
            response = await handle_ban_user(data, db_session, room_uid, user_uid)
            if response:
                await manager.broadcast_to_room(room_uid, response)
            await manager.update_user_activity(db_session, user_uid)
            continue

        if not await _rate_limit_message(websocket, user_uid):
            continue

        content_type = data.get("content_type", "text")
        if content_type == "text":
            await handle_text_message(data, room_uid, user_uid, db_session, websocket)
        elif content_type in {"file", "image", "video"}:
            await handle_file_message(data, room_uid, user_uid, db_session, websocket)
        elif content_type in {"voice", "audio"}:
            await handle_audio_message(data, room_uid, user_uid, db_session, websocket)
        else:
            await websocket.send_json(
                {
                    "type": "error",
                    "error_type": "unsupported_content_type",
                    "frontId": data.get("frontId"),
                }
            )

        await manager.update_user_activity(db_session, user_uid)


async def handle_text_message(
    data: dict,
    room_uid: UUID,
    user_uid: UUID,
    db_session: AsyncSession,
    websocket: WebSocket,
) -> None:
    content = data.get("content")
    if not isinstance(content, str) or not content.strip():
        return

    front_id = data.get("frontId")
    if not await _claim_client_event(websocket, room_uid, user_uid, front_id):
        return

    try:
        formatted_message = await Message.create_message(
            db_session,
            {
                "content": content,
                "content_type": "text",
                "sender_uid": str(user_uid),
                "room_uid": str(room_uid),
                "reply_to_uid": data.get("reply_to_uid"),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        formatted_message["frontId"] = front_id
        await manager.broadcast_to_room(room_uid, formatted_message)
        await _notify_online_members(db_session, room_uid, user_uid, formatted_message)
    except Exception:
        await _release_client_event(room_uid, user_uid, front_id)
        raise


async def handle_file_message(
    data: dict,
    room_uid: UUID,
    user_uid: UUID,
    db_session: AsyncSession,
    websocket: WebSocket,
) -> None:
    files = data.get("media_metadata", {}).get("files", [])
    if not files:
        return

    if len(files) > config.MAX_FILES_LIMIT:
        await websocket.send_json(
            {
                "type": "error",
                "error_type": "too_many_files",
                "frontId": data.get("frontId"),
                "details": {"max_allowed_files": config.MAX_FILES_LIMIT},
            }
        )
        return

    front_id = data.get("frontId")
    if not await _claim_client_event(websocket, room_uid, user_uid, front_id):
        return

    saved_files = []
    errors = []
    try:
        for file_data in files:
            try:
                file_url = file_data.get("url")
                file_type = file_data.get("type")
                file_name = str(file_data.get("name") or "")[:MAX_FILENAME_LENGTH]
                file_size = file_data.get("size")
                if not all([file_url, file_type, file_name, file_size]):
                    raise ValueError("Missing required file data")

                saved_file_url = save_file(
                    {
                        "url": file_url,
                        "type": file_type,
                        "name": file_name,
                        "size": file_size,
                    }
                )
                saved_files.append(
                    {
                        "url": saved_file_url,
                        "type": file_type,
                        "name": file_name,
                        "size": file_size,
                    }
                )
            except Exception as exc:
                logger.warning("Не удалось сохранить realtime attachment: %s", exc)
                errors.append({"file_name": file_data.get("name"), "error": "upload_failed"})

        if not saved_files:
            await _release_client_event(room_uid, user_uid, front_id)
            await websocket.send_json(
                {
                    "type": "error",
                    "error_type": "attachments_failed",
                    "frontId": front_id,
                    "details": errors,
                }
            )
            return

        formatted_message = await Message.create_message(
            db_session,
            {
                "content": data.get("content", ""),
                "content_type": data.get("content_type", "file"),
                "sender_uid": str(user_uid),
                "room_uid": str(room_uid),
                "media_metadata": {"files": saved_files},
                "reply_to_uid": data.get("reply_to_uid"),
            },
        )
        formatted_message["frontId"] = front_id
        await manager.broadcast_to_room(room_uid, formatted_message)
        await _notify_online_members(db_session, room_uid, user_uid, formatted_message)

        if errors:
            await websocket.send_json(
                {
                    "type": "partial_error",
                    "error_type": "some_attachments_failed",
                    "frontId": front_id,
                    "details": errors,
                }
            )
    except Exception:
        await _release_client_event(room_uid, user_uid, front_id)
        raise


async def handle_audio_message(
    data: dict,
    room_uid: UUID,
    user_uid: UUID,
    db_session: AsyncSession,
    websocket: WebSocket,
) -> None:
    audio_url = data.get("media_metadata", {}).get("voice")
    if not audio_url:
        return

    front_id = data.get("frontId")
    if not await _claim_client_event(websocket, room_uid, user_uid, front_id):
        return

    try:
        mime_type, encoded_data = audio_url.split(",", 1)
        file_content = base64.b64decode(encoded_data)
        if len(file_content) > config.MAX_FILE_SIZE:
            raise ValueError("audio_too_large")

        extension = mime_type.split(";")[0].split("/")[1]
        if extension not in {"webm", "ogg", "mp3", "mpeg", "wav", "m4a", "mp4"}:
            raise ValueError("unsupported_audio_type")

        upload_dir = Path("uploads/audio")
        os.makedirs(upload_dir, exist_ok=True)
        file_name = f"{uuid.uuid4()}.{extension}"
        file_path = upload_dir / file_name
        with open(file_path, "wb") as file_handle:
            file_handle.write(file_content)

        saved_audio_url = f"{config.BASE_URL}/uploads/audio/{file_name}"
        formatted_message = await Message.create_message(
            db_session,
            {
                "content": saved_audio_url,
                "content_type": "audio",
                "sender_uid": str(user_uid),
                "room_uid": str(room_uid),
                "reply_to_uid": data.get("reply_to_uid"),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        formatted_message["frontId"] = front_id
        await manager.broadcast_to_room(room_uid, formatted_message)
        await _notify_online_members(db_session, room_uid, user_uid, formatted_message)
    except Exception as exc:
        await _release_client_event(room_uid, user_uid, front_id)
        logger.warning("Не удалось обработать audio frame: %s", exc)
        await websocket.send_json(
            {
                "type": "error",
                "error_type": "audio_failed",
                "frontId": front_id,
            }
        )


async def handle_moderator_action(
    data: dict,
    db_session: AsyncSession,
    user_uid: UUID,
) -> dict:
    try:
        room_uid = UUID(str(data["room_uid"]))
        target_user_uid = UUID(str(data["target_user_uid"]))
        action = data["action"]

        room = await Room.get_room_by_uid(db_session, room_uid)
        if not room or str(room.owner_uid) != str(user_uid):
            return {
                "type": "error",
                "error_type": "space_owner_required",
                "message": "Только владелец пространства может управлять ролями",
            }

        if action == "add_moderator":
            await Room.add_moderator(db_session, room_uid, target_user_uid)
            event_type = "moderator_added"
        elif action == "remove_moderator":
            await Room.remove_moderator(db_session, room_uid, target_user_uid)
            event_type = "moderator_removed"
        else:
            return {"type": "error", "error_type": "unknown_moderator_action"}

        moderators = await RoomMember.get_moderators(db_session, room_uid)
        return {
            "type": event_type,
            "room_uid": str(room_uid),
            "target_user_uid": str(target_user_uid),
            "moderators": [str(item) for item in moderators],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception:
        logger.exception("Ошибка изменения scoped роли пространства")
        return {"type": "error", "error_type": "moderator_action_failed"}


async def handle_ban_user(
    data: dict,
    db_session: AsyncSession,
    room_uid: UUID,
    user_uid: UUID,
) -> dict:
    try:
        target_user_uid = UUID(str(data["target_user_uid"]))
        reason = str(data.get("reason") or "Нарушение правил пространства")[:500]
        ban_duration = None if data.get("permanent", False) else timedelta(days=7)

        room = await Room.get_room_by_uid(db_session, room_uid)
        if not room:
            return {"type": "error", "error_type": "space_not_found"}

        is_owner = str(room.owner_uid) == str(user_uid)
        is_moderator = await RoomMember.is_moderator(db_session, room_uid, user_uid)
        if not (is_owner or is_moderator):
            return {"type": "error", "error_type": "space_moderator_required"}

        ban = await RoomBan.ban_user(
            db_session,
            room_uid=room_uid,
            user_uid=target_user_uid,
            banned_by_uid=user_uid,
            reason=reason,
            ban_duration=ban_duration,
        )

        notification = {
            "type": "user_banned",
            "room_uid": str(room_uid),
            "target_user_uid": str(target_user_uid),
            "restricted_by": str(user_uid),
            "reason": reason,
            "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
            "permanent": ban.expires_at is None,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await manager.disconnect_user_from_room(room_uid, target_user_uid, reason=reason)
        return notification
    except (KeyError, ValueError):
        return {"type": "error", "error_type": "invalid_restriction_target"}
    except Exception:
        logger.exception("Ошибка ограничения доступа к пространству")
        return {"type": "error", "error_type": "space_restriction_failed"}


@get_session
async def handle_websocket_connection(
    websocket: WebSocket,
    room_uid: UUID | str,
    user: dict,
    db_session: AsyncSession = None,
):
    normalized_room_uid = UUID(str(room_uid))
    user_uid = UUID(user["user_uid"])
    connected = False

    try:
        connected = await initialize_websocket(
            websocket,
            db_session,
            normalized_room_uid,
            user_uid,
        )
        if not connected:
            return
        await process_incoming_messages(
            websocket,
            normalized_room_uid,
            user_uid,
            db_session,
        )
    except WebSocketDisconnect:
        logger.info("Room realtime disconnected: user=%s room=%s", user_uid, normalized_room_uid)
    except Exception:
        logger.exception("Room realtime handler failed")
        try:
            await websocket.close(code=1011, reason="Realtime room error")
        except Exception:
            pass
    finally:
        if connected:
            await manager.disconnect(websocket, normalized_room_uid)
