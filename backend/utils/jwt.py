import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from settings import config

logger = logging.getLogger(__name__)

def create_access_token(payload: Dict[str, Any]) -> str:
    """Генерация JWT access-токена"""
    try:
        return jwt.encode(
            {
                "sub": payload.get("user_uid"),  # Стандартное поле для субъекта
                "exp": datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
                "type": "access",
                "data": payload
            },
            config.JWT_ACCESS_SECRET_KEY,
            algorithm=config.JWT_ALGORITHM
        )
    except Exception as e:
        logger.error(f"Ошибка генерации access-токена: {e}")
        raise

def create_refresh_token(payload: Dict[str, Any], jti: str) -> str:
    """Генерация JWT refresh-токена"""
    try:
        return jwt.encode(
            {
                "sub": payload.get("user_uid"),
                "exp": datetime.utcnow() + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS),
                "type": "refresh",
                "jti": jti,  # Уникальный идентификатор токена
                "data": payload
            },
            config.JWT_REFRESH_SECRET_KEY,
            algorithm=config.JWT_ALGORITHM
        )
    except Exception as e:
        logger.error(f"Ошибка генерации refresh-токена: {e}")
        raise

def validate_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Валидация access-токена"""
    try:
        if not token:
            return None
            
        # Безопасное извлечение токена из заголовка
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
            
        payload = jwt.decode(
            token,
            config.JWT_ACCESS_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            options={"verify_exp": True}
        )
        
        if payload.get("type") != "access":
            logger.warning("Попытка использовать не access-токен")
            return None
            
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
        payload = jwt.decode(
            token,
            config.JWT_REFRESH_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            options={"verify_exp": True}
        )
        
        if payload.get("type") != "refresh":
            logger.warning("Попытка использовать не refresh-токен")
            return None
            
        return {
            "jti": payload.get("jti"),
            "user_uid": payload.get("sub"),
            "data": payload.get("data")
        }
        
    except jwt.ExpiredSignatureError:
        logger.info("Истек срок действия refresh-токена")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Невалидный refresh-токен: {e}")
        return None