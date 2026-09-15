from datetime import datetime
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.decorators.db import get_session
from components.identity.model import AccountRelationship, Persona, PrivacySettings
from components.message.model import PrivateMessage
from components.realtime import realtime_service
from components.room.model import RoomMember
from components.user.model import User
from settings import config
from socket_manager import private_manager
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def initialize_messenger_connection(
    websocket: WebSocket,
    user_uid: UUID,
    db_session: AsyncSession,
) -> None:
    await private_manager.connect_to_messenger(websocket, user_uid)
    await User.update_last_online(db_session, user_uid)


async def _dm_allowed(
    db_session: AsyncSession,
    sender_uid: UUID,
    receiver_uid: UUID,
) -> bool:
    if sender_uid == receiver_uid:
        return True

    blocked = await db_session.execute(
        select(AccountRelationship.id)
        .where(
            AccountRelationship.relation_type == "block",
            or_(
                and_(
                    AccountRelationship.from_account_uid == sender_uid,
                    AccountRelationship.to_account_uid == receiver_uid,
                ),
                and_(
                    AccountRelationship.from_account_uid == receiver_uid,
                    AccountRelationship.to_account_uid == sender_uid,
                ),
            ),
        )
        .limit(1)
    )
    if blocked.scalar_one_or_none() is not None:
        return False

    policy_result = await db_session.execute(
        select(PrivacySettings.dm_policy)
        .join(Persona, Persona.uid == PrivacySettings.persona_uid)
        .where(
            Persona.account_uid == receiver_uid,
            Persona.is_primary.is_(True),
        )
        .limit(1)
    )
    dm_policy = policy_result.scalar_one_or_none() or "shared_spaces"

    if dm_policy == "everyone":
        return True
    if dm_policy == "nobody":
        return False

    if dm_policy == "mutual":
        reciprocal = await db_session.execute(
            select(func.count(AccountRelationship.id)).where(
                AccountRelationship.relation_type == "friend",
                or_(
                    and_(
                        AccountRelationship.from_account_uid == sender_uid,
                        AccountRelationship.to_account_uid == receiver_uid,
                    ),
                    and_(
                        AccountRelationship.from_account_uid == receiver_uid,
                        AccountRelationship.to_account_uid == sender_uid,
                    ),
                ),
            )
        )
        return (reciprocal.scalar_one() or 0) >= 2

    if dm_policy == "shared_spaces":
        shared_space = await db_session.execute(
            select(RoomMember.room_uid)
            .where(
                RoomMember.user_uid.in_([sender_uid, receiver_uid]),
                RoomMember.is_banned.is_(False),
            )
            .group_by(RoomMember.room_uid)
            .having(func.count(func.distinct(RoomMember.user_uid)) >= 2)
            .limit(1)
        )
        return shared_space.scalar_one_or_none() is not None

    return False


async def _rate_limit_message(websocket: WebSocket, user_uid: UUID) -> bool:
    allowed = await realtime_service.allow_action(
        user_uid=user_uid,
        bucket="direct-message",
        limit=config.REALTIME_MESSAGE_RATE_LIMIT,
        window_seconds=config.REALTIME_MESSAGE_RATE_WINDOW_SECONDS,
    )
    if allowed:
        return True
    await websocket.send_json(
        {
            "type": "rate_limited",
            "scope": "direct_message",
            "retry_after": config.REALTIME_MESSAGE_RATE_WINDOW_SECONDS,
        }
    )
    return False


async def handle_private_messages(
    websocket: WebSocket,
    user_uid: UUID,
    db_session: AsyncSession,
) -> None:
    while True:
        data = await websocket.receive_json()
        action = data.get("action")
        frame_type = data.get("type")

        if frame_type in {"heartbeat", "pong"} or action == "heartbeat":
            await private_manager.touch_connection(websocket)
            continue

        await private_manager.touch_connection(websocket)

        if action == "send_message":
            if await _rate_limit_message(websocket, user_uid):
                await handle_send_private_message(data, user_uid, db_session, websocket)
        elif action == "mark_message_as_read":
            await handle_mark_as_read(data, user_uid, db_session, websocket)
        elif action == "get_conversation":
            await handle_get_conversation(data, user_uid, db_session, websocket)
        elif action == "subscribe_status":
            target_uids = [UUID(uid) for uid in data.get("userIds", [])]
            await private_manager.subscribe_to_status(user_uid, target_uids)
        elif action == "unsubscribe_status":
            target_uids = [UUID(uid) for uid in data.get("userIds", [])]
            await private_manager.unsubscribe_from_status(user_uid, target_uids)
        else:
            await websocket.send_json({"type": "error", "error_type": "unknown_action"})

        await private_manager.update_user_activity(db_session, user_uid)


async def handle_send_private_message(
    data: dict,
    sender_uid: UUID,
    db_session: AsyncSession,
    websocket: WebSocket,
) -> None:
    try:
        receiver_uid = UUID(str(data.get("receiver_uid")))
    except (TypeError, ValueError):
        await websocket.send_json(
            {
                "type": "error",
                "error_type": "invalid_receiver",
                "frontId": data.get("frontId"),
            }
        )
        return

    if not await _dm_allowed(db_session, sender_uid, receiver_uid):
        await websocket.send_json(
            {
                "type": "error",
                "error_type": "dm_not_allowed",
                "frontId": data.get("frontId"),
            }
        )
        return

    try:
        formatted_message = await PrivateMessage.create_private_message(
            db_session,
            {
                "content": data.get("content"),
                "content_type": data.get("content_type", "text"),
                "sender_uid": str(sender_uid),
                "receiver_uid": str(receiver_uid),
                "media_metadata": data.get("media_metadata"),
            },
        )
        formatted_message["frontId"] = data.get("frontId")

        await private_manager.send_to_user(sender_uid, formatted_message)
        if receiver_uid != sender_uid:
            await private_manager.send_to_user(receiver_uid, formatted_message)
    except Exception:
        logger.exception("Ошибка отправки private message")
        await websocket.send_json(
            {
                "type": "error",
                "error_type": "message_send_failed",
                "frontId": data.get("frontId"),
            }
        )


async def handle_mark_as_read(
    data: dict,
    user_uid: UUID,
    db_session: AsyncSession,
    websocket: WebSocket,
) -> None:
    message_uid = data.get("message_uid")
    if not message_uid:
        return

    try:
        message = await PrivateMessage.mark_as_read(db_session, message_uid)
        if not message:
            return
        if str(message.receiver_uid) != str(user_uid):
            await db_session.rollback()
            await websocket.send_json({"type": "error", "error_type": "read_receipt_not_allowed"})
            return

        await private_manager.send_to_user(
            message.sender_uid,
            {
                "type": "message_read",
                "message_uid": str(message_uid),
                "read_at": datetime.utcnow().isoformat(),
            },
        )
    except Exception:
        logger.exception("Ошибка read receipt")


async def handle_get_conversation(
    data: dict,
    user_uid: UUID,
    db_session: AsyncSession,
    websocket: WebSocket,
) -> None:
    try:
        other_user_uid = UUID(str(data.get("other_user_uid")))
        messages = await PrivateMessage.get_conversation(
            db_session,
            user1_uid=user_uid,
            user2_uid=other_user_uid,
        )
        await private_manager.send_to_specific_user(
            websocket,
            {
                "type": "conversation",
                "other_user_uid": str(other_user_uid),
                "messages": messages,
                "request_id": data.get("request_id"),
                "resume": True,
            },
        )
    except Exception:
        logger.exception("Ошибка получения conversation")
        await private_manager.send_to_specific_user(
            websocket,
            {
                "type": "error",
                "error_type": "conversation_failed",
                "request_id": data.get("request_id"),
            },
        )


@get_session
async def handle_messenger_connection(
    websocket: WebSocket,
    user: dict,
    db_session: AsyncSession = None,
):
    user_uid = UUID(user["user_uid"])
    connected = False

    try:
        await initialize_messenger_connection(websocket, user_uid, db_session)
        connected = True
        await handle_private_messages(websocket, user_uid, db_session)
    except WebSocketDisconnect:
        logger.info("Messenger realtime disconnected: user=%s", user_uid)
    except Exception:
        logger.exception("Messenger realtime handler failed")
        try:
            await websocket.close(code=1011, reason="Realtime messenger error")
        except Exception:
            pass
    finally:
        if connected:
            await private_manager.disconnect(websocket)
