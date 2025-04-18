from fastapi import Request, HTTPException, status
from utils.logger import setup_logger
from components.user.model import Penalty, PenaltyType, User
from components.decorators.db import get_session

from datetime import datetime
from uuid import UUID

logger = setup_logger(__name__)

@get_session
async def assign_penalty(request: Request, db_session=None):
    """
    Назначение наказания пользователю.
    :param request: Запрос FastAPI.
    :param db_session: Сессия базы данных.
    :return: JSON-ответ о статусе операции.
    """
    try:
        # Извлекаем данные из запроса
        data: dict = await request.json()
        user_uid = data.get("user_uid")
        penalty_type = data.get("penalty_type")
        expires_at = data.get("expires_at")
        reason = data.get("reason")

        # Проверяем, что все необходимые поля присутствуют
        if not all([user_uid, penalty_type, expires_at]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недостаточно данных для назначения наказания"
            )

        # Проверяем, существует ли пользователь
        user = db_session.query(User).filter(User.uid == UUID(user_uid)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )

        # Преобразуем expires_at в datetime
        expires_at_datetime = datetime.fromisoformat(expires_at)
        
        # Создаем запись о наказании через метод модели
        penalty = Penalty.create_penalty(
            db_session=db_session,
            user_uid=user.uid,
            penalty_type=penalty_type,
            expires_at=expires_at_datetime,
            issuer_uid=request.state.user['user_uid'],  # UID администратора
            reason=reason,
        )

        # Возвращаем успешный ответ
        return {
            "status": "ok",
            "message": "Наказание успешно назначено",
            "data": {
                "penalty_id": penalty.id,
                "user_uid": str(penalty.user_uid),
                "penalty_type": penalty.penalty_type.value,
                "issued_at": penalty.issued_at.isoformat(),
                "expires_at": penalty.expires_at.isoformat(),
                "issuer_uid": str(penalty.issuer_uid),
                "reason": penalty.reason,
            },
        }

    except HTTPException as http_error:
        # Логируем ошибку и возвращаем JSON-ответ
        logger.error(f"Ошибка при назначении наказания: {http_error.detail}")
        return {
            "status": "error",
            "message": http_error.detail,
        }, http_error.status_code

    except Exception as e:
        # Логируем ошибку и возвращаем HTTP-ошибку
        logger.error(f"Неожиданная ошибка при назначении наказания: {e}")
        return {
            "status": "error",
            "message": "Internal server error",
        }, status.HTTP_500_INTERNAL_SERVER_ERROR