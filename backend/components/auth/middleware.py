from fastapi import Request, HTTPException, WebSocket, status
from utils.jwt import validate_access_token
from typing import Optional

async def auth_middle(request: Request):
    # Получаем заголовок Authorization
    token = request.headers.get("authorization")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "bad", "error_type": "missing_token"}
        )

    # Валидируем токен
    user_data = validate_access_token(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "bad", "error_type": "invalid_token"}
        )

    # Сохраняем данные пользователя в request.state для дальнейшего использования
    request.state.user = user_data

from fastapi import WebSocketException, status
import logging

logger = logging.getLogger(__name__)

async def auth_middle_ws(websocket: WebSocket):
    # Извлекаем токен из параметров запроса
    token = websocket.query_params.get("token")
    logger.info(f"Received token: {token}")  # Логирование

    if not token:
        logger.warning("Missing token in WebSocket request")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")

    # Валидируем токен
    user_data = validate_access_token(f"Bearer {token}")
    if not user_data:
        logger.warning("Invalid token in WebSocket request")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")

    logger.info(f"User authenticated: {user_data}")
    return user_data