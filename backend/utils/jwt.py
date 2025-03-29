import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from settings import config
from utils.logger import setup_logger  # Импортируем централизованный логгер

# Создаем логгер для этого модуля
logger = setup_logger(__name__)

def create_access_token(payload: Dict[str, Any]) -> str:
    """Генерация JWT access-токена"""
    try:
        user_uid = str(payload.get("user_uid"))  # Преобразуем user_uid в строку
        if not user_uid:
            raise ValueError("user_uid is required")

        logger.debug(f"Генерация access-токена для пользователя: {user_uid}")
        return jwt.encode(
            {
                "sub": user_uid,
                "exp": datetime.utcnow() + timedelta(seconds=config.ACCESS_TOKEN_EXPIRE_MINUTES),
                "type": "access",
                "data": payload,
            },
            config.JWT_ACCESS_SECRET_KEY,
            algorithm=config.JWT_ALGORITHM,
        )
    except Exception as e:
        logger.error(f"Ошибка генерации access-токена: {e}")
        raise


def create_refresh_token(payload: Dict[str, Any], jti: str) -> str:
    """Генерация JWT refresh-токена"""
    try:
        user_uid = str(payload.get("user_uid"))  # Преобразуем user_uid в строку
        if not user_uid:
            raise ValueError("user_uid is required")

        logger.debug(f"Генерация refresh-токена для пользователя: {user_uid}")
        return jwt.encode(
            {
                "sub": user_uid,
                "exp": datetime.utcnow() + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS),
                "type": "refresh",
                "jti": jti,
                "data": payload,
            },
            config.JWT_REFRESH_SECRET_KEY,
            algorithm=config.JWT_ALGORITHM,
        )
    except Exception as e:
        logger.error(f"Ошибка генерации refresh-токена: {e}")
        raise


def validate_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Валидация access-токена"""
    try:
        if not token:
            logger.warning("Получен пустой access-токен")
            return None
        
        # Безопасное извлечение токена из заголовка
        if token.startswith("Bearer "):
            token = token.split(" ")[1]

        logger.debug(f"Валидация access-токена: {token[:10]}...")  # Логируем начало токена
        payload = jwt.decode(
            token,
            config.JWT_ACCESS_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            options={"verify_exp": True},
        )

        if payload.get("type") != "access":
            logger.warning("Попытка использовать не access-токен")
            return None

        sub = payload.get("sub")
        if not isinstance(sub, str):  # Проверяем, что sub — строка
            logger.warning("Subject must be a string")
            return None

        logger.info(f"Access-токен успешно валидирован для пользователя: {sub}")
        return payload.get("data")

    except jwt.ExpiredSignatureError:
        logger.info("Истек срок действия access-токена")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Невалидный access-токен: {e}")
        return None


def validate_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Валидация refresh-токена"""
    try:
        logger.debug(f"Валидация refresh-токена: {token[:10]}...")  # Логируем начало токена
        payload = jwt.decode(
            token,
            config.JWT_REFRESH_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            options={"verify_exp": True},
        )

        if payload.get("type") != "refresh":
            logger.warning("Попытка использовать не refresh-токен")
            return None

        sub = payload.get("sub")
        if not isinstance(sub, str):  # Проверяем, что sub — строка
            logger.warning("Subject must be a string")
            return None

        logger.info(f"Refresh-токен успешно валидирован для пользователя: {sub}")
        return {
            "jti": payload.get("jti"),
            "user_uid": sub,
            "data": payload.get("data"),
        }

    except jwt.ExpiredSignatureError:
        logger.info("Истек срок действия refresh-токена")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Невалидный refresh-токен: {e}")
        return None