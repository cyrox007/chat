from uuid import uuid4
from fastapi import APIRouter, Response, Request
from utils.csrf import generate_csrf_token
from utils.logger import setup_logger  # Импортируем централизованный логгер

# Создаем логгер для этого модуля
logger = setup_logger(__name__)

async def get_csrf(request: Request, response: Response):
    try:
        # Логируем начало генерации CSRF-токена
        logger.info("Generating CSRF token")

        # Генерируем новый session_id для каждого запроса
        session_id = str(uuid4())
        logger.debug(f"Generated session_id: {session_id}")

        # Генерируем CSRF-токен
        token = generate_csrf_token(session_id)
        logger.debug(f"Generated CSRF token for session_id: {session_id}")

        # Устанавливаем CSRF-токен в куки
        response.set_cookie(
            key="XSRF-TOKEN",
            value=token,
            httponly=True,
            secure=False,  # True в production
            samesite="lax",
            max_age=1800  # 30 минут
        )
        logger.info("CSRF token successfully set in cookies")

        return {"status": "ok"}

    except Exception as e:
        # Логируем ошибку при генерации CSRF-токена
        logger.error(f"Error generating CSRF token: {str(e)}")
        raise