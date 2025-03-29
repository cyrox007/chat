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
        logger.warning("Отсутствующий токен в HTTP-запросе")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "bad", "error_type": "missing_token"}
        )

    # Логируем полученный токен
    logger.info(f"Полученный токен из заголовков: {token}")

    # Валидируем токен
    user_data = validate_access_token(token)
    if not user_data:
        logger.warning("Недопустимый токен в HTTP-запросе")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "bad", "error_type": "invalid_token"}
        )

    # Сохраняем данные пользователя в request.state для дальнейшего использования
    request.state.user = user_data
    logger.info(f"Аутентифицированный пользователь: {user_data}")


async def auth_middle_ws(token: str):
    logger.info(f"Проверка токена по пути: {token[:10]}...")  # Логируем только начало токена

    # Валидируем токен
    user_data = validate_access_token(token)
    if not user_data:
        logger.warning("Недопустимый токен в запросе WebSocket")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")

    logger.info(f"<WS>Аутентифицированный пользователь: {user_data}")
    return user_data