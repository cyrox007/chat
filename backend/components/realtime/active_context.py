from __future__ import annotations

import time
from uuid import UUID

from components.realtime.service import realtime_service
from settings import config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ActiveContextService:
    """Ephemeral notification-suppression context.

    This state is UX-only and must never participate in authorization. Messenger
    contexts are tracked per realtime connection in Redis ZSETs so multiple
    devices can coexist. Space context is already represented by the dedicated
    room WebSocket presence maintained by RealtimeService.
    """

    def __init__(self) -> None:
        self._fallback: dict[tuple[str, str, str, str], float] = {}

    @staticmethod
    def _messenger_key(account_uid: UUID | str, dialog_uid: UUID | str) -> str:
        return f"pubchat:rt:active:messenger:{account_uid}:{dialog_uid}"

    @staticmethod
    def _fallback_key(
        connection_id: str,
        account_uid: UUID | str,
        surface: str,
        resource_uid: UUID | str,
    ) -> tuple[str, str, str, str]:
        return (str(connection_id), str(account_uid), surface, str(resource_uid))

    async def set_messenger(
        self,
        connection_id: str,
        account_uid: UUID | str,
        dialog_uid: UUID | str,
    ) -> None:
        expires_at = time.time() + config.REALTIME_PRESENCE_TTL_SECONDS
        client = realtime_service.redis
        if client is not None:
            key = self._messenger_key(account_uid, dialog_uid)
            try:
                pipe = client.pipeline(transaction=False)
                pipe.zadd(key, {connection_id: expires_at})
                pipe.expire(key, config.REALTIME_PRESENCE_TTL_SECONDS * 2)
                await pipe.execute()
            except Exception:
                # Notification suppression is best-effort UX state. A Redis
                # failover must not disconnect an otherwise valid conversation.
                logger.warning("Could not refresh Messenger active context", exc_info=True)
            return

        if config.DEBUG:
            self._fallback[
                self._fallback_key(connection_id, account_uid, "messenger", dialog_uid)
            ] = expires_at

    async def clear_messenger(
        self,
        connection_id: str,
        account_uid: UUID | str,
        dialog_uid: UUID | str,
    ) -> None:
        client = realtime_service.redis
        if client is not None:
            try:
                await client.zrem(self._messenger_key(account_uid, dialog_uid), connection_id)
            except Exception:
                logger.warning("Could not clear Messenger active context", exc_info=True)
            return

        self._fallback.pop(
            self._fallback_key(connection_id, account_uid, "messenger", dialog_uid),
            None,
        )

    async def is_active(
        self,
        account_uid: UUID | str,
        surface: str,
        resource_uid: UUID | str,
    ) -> bool:
        if surface == "space":
            try:
                return str(account_uid) in await realtime_service.room_users(resource_uid)
            except Exception:
                logger.warning("Could not resolve Space active context", exc_info=True)
                return False

        if surface != "messenger":
            return False

        now = time.time()
        client = realtime_service.redis
        if client is not None:
            key = self._messenger_key(account_uid, resource_uid)
            try:
                await client.zremrangebyscore(key, "-inf", now)
                return bool(await client.zcount(key, now, "+inf"))
            except Exception:
                logger.warning("Could not resolve Messenger active context", exc_info=True)
                return False

        expired = [key for key, expires_at in self._fallback.items() if expires_at <= now]
        for key in expired:
            self._fallback.pop(key, None)
        return any(
            key_account == str(account_uid)
            and key_surface == "messenger"
            and key_resource == str(resource_uid)
            for _, key_account, key_surface, key_resource in self._fallback
        )


active_context_service = ActiveContextService()
