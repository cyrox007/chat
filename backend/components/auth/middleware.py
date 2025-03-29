from fastapi import Request, HTTPException, WebSocket, WebSocketException, status
from utils.jwt import validate_access_token
from utils.logger import setup_logger
from starlette.status import WS_1008_POLICY_VIOLATION

# Создаем логгер для этого модуля
logger = setup_logger(__name__)

async def auth_middle(request: Request):
    # Получаем заголовок Authorization
    token = request.headers.get("authorization")
    if not token:
        logger.warning("Missing token in HTTP request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "bad", "error_type": "missing_token"}
        )

    # Логируем полученный токен
    logger.info(f"Received token from headers: {token}")

    # Валидируем токен
    user_data = validate_access_token(token)
    if not user_data:
        logger.warning("Invalid token in HTTP request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "bad", "error_type": "invalid_token"}
        )

    # Сохраняем данные пользователя в request.state для дальнейшего использования
    request.state.user = user_data
    logger.info(f"User authenticated: {user_data}")


async def auth_middle_ws(websocket: WebSocket):
    # Извлекаем токен из заголовков
    token = websocket.headers.get("Authorization")
    logger.info(f"Received token from headers: {token}")  # Логирование

    if not token or not token.startswith("Bearer "):
        logger.warning("Missing or invalid token in WebSocket headers")
        raise WebSocketException(code=WS_1008_POLICY_VIOLATION, reason="Missing or invalid token")

    # Убираем префикс "Bearer " из токена
    token = token.split(" ")[1]

    # Валидируем токен
    user_data = validate_access_token(token)
    if not user_data:
        logger.warning("Invalid token in WebSocket request")
        raise WebSocketException(code=WS_1008_POLICY_VIOLATION, reason="Invalid token")

    logger.info(f"User authenticated: {user_data}")
    return user_data