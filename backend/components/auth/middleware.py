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
        #await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")

    logger.info(f"<WS>Аутентифицированный пользователь: {user_data}")
    return user_data

async def authorize_user(current_user, target_user_uid, required_role=None):
    """
    Проверяет права доступа пользователя.
    :param current_user: Данные текущего пользователя (из токена).
    :param target_user_uid: UID целевого пользователя.
    :param required_role: Требуемая роль (необязательно).
    :return: True, если доступ разрешен.
    """
    # Если пользователь запрашивает свои собственные данные
    if current_user["uid"] == target_user_uid:
        logger.info("Пользователь запрашивает свои собственные данные")
        return True

    # Если требуется роль (например, администратор)
    if required_role and current_user["role"] != required_role:
        logger.warning(f"Пользователь {current_user['uid']} не имеет роли {required_role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"status": "bad", "error_type": "insufficient_permissions"}
        )

    # Ограниченный доступ для других пользователей
    logger.info(f"Пользователь {current_user['uid']} запрашивает данные другого пользователя {target_user_uid}")
    return False