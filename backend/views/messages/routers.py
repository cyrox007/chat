from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.message.actions import (
    edit_message,
    ensure_message_access,
    load_message,
    reaction_projection,
    soft_delete_message,
    toggle_reaction,
)
from components.message.model import Message, PrivateMessage
from components.moderation.policy import assert_allowed
from components.room.model import RoomMember
from database import Database
from socket_manager import private_manager, room_manager
from views.messenger.ws_handlers import _dm_allowed


class EditMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class ReactionRequest(BaseModel):
    emoji: str = Field(min_length=1, max_length=32)


class ForwardMessageRequest(BaseModel):
    target_surface: str
    target_uid: UUID


def _user_uid(current_user: dict) -> UUID:
    try:
        return UUID(str(current_user["user_uid"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail={"error_type": "invalid_account"}) from exc


async def _publish_update(surface: str, message, payload: dict) -> None:
    event = {"type": "message_updated", "surface": surface, **payload}
    if surface == "room":
        await room_manager.broadcast_to_room(message.room_uid, event)
    else:
        await private_manager.send_to_user(message.sender_uid, event)
        if message.receiver_uid != message.sender_uid:
            await private_manager.send_to_user(message.receiver_uid, event)


async def _publish_reactions(surface: str, message, reactions: list[dict]) -> None:
    event = {
        "type": "message_reactions",
        "surface": surface,
        "message_uid": str(message.uid),
        "reactions": reactions,
    }
    if surface == "room":
        await room_manager.broadcast_to_room(message.room_uid, event)
    else:
        await private_manager.send_to_user(message.sender_uid, event)
        if message.receiver_uid != message.sender_uid:
            await private_manager.send_to_user(message.receiver_uid, event)


def install(app: FastAPI):
    router = APIRouter(prefix="/messages/v2", tags=["messages-v2"])

    @router.patch("/{surface}/{message_uid}")
    async def patch_message(
        surface: str,
        message_uid: UUID,
        payload: EditMessageRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        user_uid = _user_uid(current_user)
        await assert_allowed(db, user_uid, "messenger.send" if surface == "messenger" else "space.chat.send")
        message = await load_message(db, surface, message_uid)
        result = await edit_message(db, surface, message_uid, user_uid, payload.content)
        await _publish_update(surface, message, result)
        return {"status": "ok", "message": result}

    @router.delete("/{surface}/{message_uid}")
    async def delete_message(
        surface: str,
        message_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        user_uid = _user_uid(current_user)
        message = await load_message(db, surface, message_uid)
        result = await soft_delete_message(db, surface, message_uid, user_uid)
        await _publish_update(surface, message, result)
        return {"status": "ok", "message": result}

    @router.get("/{surface}/{message_uid}/reactions")
    async def get_reactions(
        surface: str,
        message_uid: UUID,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        user_uid = _user_uid(current_user)
        message = await load_message(db, surface, message_uid)
        await ensure_message_access(db, surface, message, user_uid)
        return {"status": "ok", "reactions": await reaction_projection(db, surface, message.uid, user_uid)}

    @router.post("/{surface}/{message_uid}/reactions")
    async def react_message(
        surface: str,
        message_uid: UUID,
        payload: ReactionRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        user_uid = _user_uid(current_user)
        message = await load_message(db, surface, message_uid)
        result = await toggle_reaction(db, surface, message_uid, user_uid, payload.emoji)
        await _publish_reactions(surface, message, result["reactions"])
        return {"status": "ok", **result}

    @router.post("/{surface}/{message_uid}/forward", status_code=status.HTTP_201_CREATED)
    async def forward_message(
        surface: str,
        message_uid: UUID,
        payload: ForwardMessageRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        user_uid = _user_uid(current_user)
        source = await load_message(db, surface, message_uid)
        await ensure_message_access(db, surface, source, user_uid)
        if source.content_type == "deleted":
            raise HTTPException(status_code=409, detail={"error_type": "message_deleted"})
        metadata = dict(source.media_metadata or {})
        metadata["forwarded_from"] = {
            "surface": surface,
            "message_uid": str(source.uid),
            "author_uid": str(source.author_uid if surface == "room" else source.sender_uid),
        }

        if payload.target_surface == "room":
            await assert_allowed(db, user_uid, "space.chat.send")
            membership = (
                await db.execute(
                    select(RoomMember.id).where(
                        RoomMember.room_uid == payload.target_uid,
                        RoomMember.user_uid == user_uid,
                        RoomMember.is_banned.is_(False),
                    ).limit(1)
                )
            ).scalar_one_or_none()
            if membership is None:
                raise HTTPException(status_code=403, detail={"error_type": "space_access_required"})
            forwarded = await Message.create_message(
                db,
                {
                    "content": source.text,
                    "content_type": source.content_type,
                    "media_metadata": metadata,
                    "room_uid": str(payload.target_uid),
                    "sender_uid": str(user_uid),
                },
            )
            await room_manager.broadcast_to_room(payload.target_uid, forwarded)
        elif payload.target_surface == "messenger":
            await assert_allowed(db, user_uid, "messenger.send")
            if not await _dm_allowed(db, user_uid, payload.target_uid):
                raise HTTPException(status_code=403, detail={"error_type": "dm_not_allowed"})
            forwarded = await PrivateMessage.create_private_message(
                db,
                {
                    "content": source.text,
                    "content_type": source.content_type,
                    "media_metadata": metadata,
                    "sender_uid": str(user_uid),
                    "receiver_uid": str(payload.target_uid),
                },
            )
            await private_manager.send_to_user(user_uid, forwarded)
            if payload.target_uid != user_uid:
                await private_manager.send_to_user(payload.target_uid, forwarded)
        else:
            raise HTTPException(status_code=422, detail={"error_type": "invalid_target_surface"})

        return {"status": "ok", "message": forwarded}

    app.include_router(router)
