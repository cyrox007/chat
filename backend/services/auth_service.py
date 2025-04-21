from fastapi import HTTPException

from utils.logger import setup_logger
from components.user.model import User
from utils.jwt import create_access_token, create_refresh_token
from utils.password import verify_password

# Создаем логгер
logger = setup_logger(__name__)

""" def authenticate_user(db_session, identifier: str, password: str) -> User:
    # Пытаемся получить пользователя
    user = User.get_user_by_credentials(db_session, identifier)
    if not user or not verify_password(password, user.hashed_password):
        logger.warning(f"Неверные учетные данные для пользователя: {identifier}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return user """

def generate_tokens(user_uid: str) -> dict:
    access_token = create_access_token({"user_uid": user_uid})
    refresh_token = create_refresh_token({"user_uid": user_uid})
    return {"access": access_token, "refresh": refresh_token}