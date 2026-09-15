import asyncio
from typing import Optional
from uuid import UUID

from fastapi import WebSocket, status
from pydantic import ValidationError

from components.realtime import realtime_service
from components.realtime.schemas import RealtimeAuthFrame
from settings import config
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def authenticate_websocket(
    websocket: WebSocket,
    target: str,
    resource_uid: Optional[UUID] = None,
) -> Optional[dict]:
    """
    Accept a WebSocket and authenticate it through the first protocol frame.

    No credential is carried in the URL. The HTTP-issued ticket is short-lived,
    one-time and scoped to the requested realtime target/resource.
    """
    await websocket.accept()

    try:
        raw_frame = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=config.REALTIME_AUTH_TIMEOUT_SECONDS,
        )
        frame = RealtimeAuthFrame.model_validate(raw_frame)
    except asyncio.TimeoutError:
        await websocket.close(code=4401, reason="Realtime authentication timed out")
        return None
    except (ValidationError, ValueError, TypeError):
        await websocket.close(code=4401, reason="Invalid realtime authentication frame")
        return None
    except Exception:
        logger.exception("Ошибка чтения realtime auth frame")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Realtime handshake failed")
        return None

    ticket_payload = await realtime_service.consume_ticket(
        raw_ticket=frame.ticket,
        target=target,
        resource_uid=resource_uid,
    )
    if not ticket_payload:
        await websocket.close(code=4401, reason="Invalid or expired realtime ticket")
        return None

    user_data = {
        "user_uid": ticket_payload["account_uid"],
        "realtime_protocol": 2,
        "resume_token": frame.resume_token,
    }
    await websocket.send_json(
        {
            "type": "realtime_ready",
            "protocol": 2,
            "target": target,
            "resource_uid": str(resource_uid) if resource_uid else None,
            "heartbeat_seconds": config.REALTIME_HEARTBEAT_SECONDS,
        }
    )
    return user_data
