import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from fastapi import WebSocket

from components.realtime import realtime_service
from components.user.model import User
from settings import config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ConnectionManager:
    """
    Keeps only process-local WebSocket objects in memory.

    Delivery, tickets and presence are delegated to realtime_service so multiple
    Uvicorn workers can participate in one logical PubChat realtime network.
    """

    def __init__(self):
        self.room_connections: Dict[UUID, List[Tuple[WebSocket, UUID]]] = {}
        self.user_connections: Dict[UUID, List[WebSocket]] = {}
        self.active_dialogs: Dict[WebSocket, UUID] = {}
        self.user_last_seen: Dict[UUID, datetime] = {}
        self.status_subscriptions: Dict[UUID, Set[UUID]] = defaultdict(set)
        self.connection_ids: Dict[WebSocket, str] = {}
        realtime_service.register_callback(self._handle_bus_event)

    @property
    def active_connections(self) -> Dict[UUID, List[WebSocket]]:
        return self.user_connections

    @property
    def online_users_count(self) -> int:
        return len(self.user_connections)

    def _connection_id(self, websocket: WebSocket) -> str:
        connection_id = self.connection_ids.get(websocket)
        if not connection_id:
            connection_id = str(uuid4())
            self.connection_ids[websocket] = connection_id
        return connection_id

    async def _send_json(self, websocket: WebSocket, message: dict) -> None:
        """Bound per-socket send latency so a slow consumer cannot block fan-out."""
        await asyncio.wait_for(
            websocket.send_json(message),
            timeout=config.REALTIME_SEND_TIMEOUT_SECONDS,
        )

    async def connect_to_room(self, websocket: WebSocket, room_uid: UUID, user_uid: UUID):
        self.room_connections.setdefault(room_uid, []).append((websocket, user_uid))
        connection_id = self._connection_id(websocket)
        was_online = await realtime_service.is_online(user_uid)
        await realtime_service.register_connection(
            connection_id=connection_id,
            user_uid=user_uid,
            target="room",
            room_uid=room_uid,
        )
        logger.info("Пользователь %s подключился к пространству %s", user_uid, room_uid)
        if not was_online:
            await realtime_service.publish_status(user_uid, True)
        await self.broadcast_user_list(room_uid)

    async def connect_to_messenger(self, websocket: WebSocket, user_uid: UUID):
        self.user_connections.setdefault(user_uid, []).append(websocket)
        connection_id = self._connection_id(websocket)
        was_online = await realtime_service.is_online(user_uid)
        await realtime_service.register_connection(
            connection_id=connection_id,
            user_uid=user_uid,
            target="messenger",
        )
        logger.info("Пользователь %s подключился к messenger", user_uid)
        if not was_online:
            await realtime_service.publish_status(user_uid, True)

    async def disconnect(self, websocket: WebSocket, room_uid: Optional[UUID] = None):
        affected_user_uid: Optional[UUID] = None

        if room_uid is not None:
            connections = self.room_connections.get(room_uid, [])
            for connection, user_uid in connections:
                if connection is websocket:
                    affected_user_uid = user_uid
                    break
            remaining = [conn for conn in connections if conn[0] is not websocket]
            if remaining:
                self.room_connections[room_uid] = remaining
            else:
                self.room_connections.pop(room_uid, None)
        else:
            for user_uid, connections in list(self.user_connections.items()):
                if websocket in connections:
                    affected_user_uid = user_uid
                    remaining = [connection for connection in connections if connection is not websocket]
                    if remaining:
                        self.user_connections[user_uid] = remaining
                    else:
                        self.user_connections.pop(user_uid, None)
                    break
            self.active_dialogs.pop(websocket, None)

        connection_id = self.connection_ids.pop(websocket, None)
        if connection_id:
            record = await realtime_service.unregister_connection(connection_id)
            if affected_user_uid is None and record and record.get("user_uid"):
                try:
                    affected_user_uid = UUID(record["user_uid"])
                except ValueError:
                    pass

        if room_uid is not None:
            await self.broadcast_user_list(room_uid)

        if affected_user_uid and not await realtime_service.is_online(affected_user_uid):
            await realtime_service.publish_status(affected_user_uid, False)

    async def touch_connection(self, websocket: WebSocket) -> None:
        connection_id = self.connection_ids.get(websocket)
        if connection_id:
            await realtime_service.touch_connection(connection_id)

    async def broadcast_user_list(self, room_uid: UUID):
        users = await realtime_service.room_users(room_uid)
        await realtime_service.publish_room(
            room_uid,
            {"type": "user_list", "users": users, "protocol": 2},
        )

    async def broadcast_to_room(self, room_uid: UUID, message: dict):
        await realtime_service.publish_room(room_uid, message)

    async def send_to_user(self, user_uid: UUID | str, message: dict):
        try:
            normalized_uid = UUID(str(user_uid))
        except ValueError:
            logger.error("Некорректный UUID пользователя для realtime delivery: %s", user_uid)
            return
        await realtime_service.publish_user(normalized_uid, message)

    async def _send_local_room(
        self,
        room_uid: UUID,
        message: dict,
        exclude_user: Optional[UUID] = None,
    ) -> None:
        stale: list[WebSocket] = []
        coroutines = []
        sockets = []
        for websocket, user_uid in list(self.room_connections.get(room_uid, [])):
            if exclude_user and user_uid == exclude_user:
                continue
            sockets.append(websocket)
            coroutines.append(self._send_json(websocket, message))

        if coroutines:
            results = await asyncio.gather(*coroutines, return_exceptions=True)
            for websocket, result in zip(sockets, results):
                if isinstance(result, Exception):
                    stale.append(websocket)
                    if isinstance(result, asyncio.TimeoutError):
                        logger.warning("Realtime room consumer exceeded send timeout: room=%s", room_uid)

        for websocket in stale:
            await self.disconnect(websocket, room_uid)

    async def _send_local_user(self, user_uid: UUID, message: dict) -> None:
        sockets = list(self.user_connections.get(user_uid, []))
        if not sockets:
            return
        results = await asyncio.gather(
            *(self._send_json(websocket, message) for websocket in sockets),
            return_exceptions=True,
        )
        for websocket, result in zip(sockets, results):
            if isinstance(result, Exception):
                if isinstance(result, asyncio.TimeoutError):
                    logger.warning("Realtime DM consumer exceeded send timeout: user=%s", user_uid)
                await self.disconnect(websocket)

    async def _handle_bus_event(self, event: dict) -> None:
        kind = event.get("kind")
        if kind == "room":
            try:
                room_uid = UUID(event["room_uid"])
            except (KeyError, ValueError):
                return
            exclude_user = None
            if event.get("exclude_user"):
                try:
                    exclude_user = UUID(event["exclude_user"])
                except ValueError:
                    pass
            await self._send_local_room(room_uid, event.get("payload", {}), exclude_user)
            return

        if kind == "user":
            try:
                user_uid = UUID(event["user_uid"])
            except (KeyError, ValueError):
                return
            await self._send_local_user(user_uid, event.get("payload", {}))
            return

        if kind == "status":
            try:
                target_uid = UUID(event["user_uid"])
            except (KeyError, ValueError):
                return
            message = {
                "type": "status_update",
                "statuses": {str(target_uid): bool(event.get("is_online"))},
            }
            for subscriber_uid in tuple(self.status_subscriptions.get(target_uid, set())):
                await self._send_local_user(subscriber_uid, message)
            return

        if kind == "room_control" and event.get("action") == "disconnect_user":
            try:
                room_uid = UUID(event["room_uid"])
                user_uid = UUID(event["user_uid"])
            except (KeyError, ValueError):
                return
            reason = str(event.get("reason") or "Access to this space was restricted")[:120]
            for websocket, connection_user_uid in list(self.room_connections.get(room_uid, [])):
                if connection_user_uid != user_uid:
                    continue
                try:
                    await asyncio.wait_for(
                        websocket.close(code=4001, reason=reason),
                        timeout=config.REALTIME_SEND_TIMEOUT_SECONDS,
                    )
                except Exception:
                    pass
                finally:
                    await self.disconnect(websocket, room_uid)

    def set_active_dialog(self, websocket: WebSocket, dialog_with_uid: UUID):
        self.active_dialogs[websocket] = dialog_with_uid

    def get_active_dialog(self, websocket: WebSocket) -> Optional[UUID]:
        return self.active_dialogs.get(websocket)

    async def send_to_specific_user(self, websocket: WebSocket, message: dict):
        try:
            await self._send_json(websocket, message)
        except Exception:
            logger.exception("Ошибка отправки realtime сообщения на конкретное устройство")
            await self.disconnect(websocket)

    async def update_user_activity(self, db_session, user_uid: UUID):
        self.user_last_seen[user_uid] = datetime.now()
        await User.update_last_online(db_session, user_uid)

    async def subscribe_to_status(self, subscriber_uid: UUID, target_uids: List[UUID]):
        statuses = {}
        for target_uid in target_uids:
            self.status_subscriptions[target_uid].add(subscriber_uid)
            statuses[str(target_uid)] = await realtime_service.is_online(target_uid)
        await self._send_local_user(
            subscriber_uid,
            {"type": "status_update", "statuses": statuses},
        )

    async def unsubscribe_from_status(self, subscriber_uid: UUID, target_uids: List[UUID]):
        for target_uid in target_uids:
            subscribers = self.status_subscriptions.get(target_uid)
            if not subscribers:
                continue
            subscribers.discard(subscriber_uid)
            if not subscribers:
                self.status_subscriptions.pop(target_uid, None)

    async def broadcast_status_update(self, user_uid: UUID, is_online: bool):
        await realtime_service.publish_status(user_uid, is_online)

    def get_user_connection(self, room_uid: UUID, user_uid: UUID) -> Optional[WebSocket]:
        for connection, uid in self.room_connections.get(room_uid, []):
            if uid == user_uid:
                return connection
        return None

    async def disconnect_user_from_room(
        self,
        room_uid: UUID,
        user_uid: UUID,
        reason: str = "Access to this space was restricted",
    ):
        await realtime_service.publish(
            {
                "kind": "room_control",
                "action": "disconnect_user",
                "room_uid": str(room_uid),
                "user_uid": str(user_uid),
                "reason": reason[:120],
            }
        )

    async def broadcast_to_room_except(
        self,
        room_uid: UUID,
        message: dict,
        exclude_user: UUID | None = None,
    ):
        await realtime_service.publish(
            {
                "kind": "room",
                "room_uid": str(room_uid),
                "exclude_user": str(exclude_user) if exclude_user else None,
                "payload": message,
            }
        )
