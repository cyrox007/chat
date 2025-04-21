import json
from datetime import datetime, timezone

from fastapi import HTTPException, Request, Response, status
from utils.file_handler import save_file
from components.room.model import Room
from utils.logger import setup_logger
from components.user.model import Penalty, User
from components.decorators.db import get_session

from datetime import datetime
from uuid import UUID

logger = setup_logger(__name__)

@get_session
async def assign_penalty(request: Request, response: Response, db_session=None):
    """
    Назначение наказания пользователю.
    """
    try:
        # Извлекаем данные из запроса
        try:
            data: dict = await request.json()
            user_uid = data.get("user_uid")
            penalty_type = data.get("penalty_type")
            expires_at = data.get("expires_at")
            reason = data.get("reason")
        except json.JSONDecodeError:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'status': 'error',
                'message': "Invalid JSON data"
            }

        # Проверяем, что все необходимые поля присутствуют
        if not all([user_uid, penalty_type, expires_at]):
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'status': 'error',
                'message': "Недостаточно данных для назначения наказания",
                'details': {
                    'required_fields': ['user_uid', 'penalty_type', 'expires_at']
                }
            }

        # Проверяем, существует ли пользователь
        try:
            user = await User.get_user_by_uid(db_session, user_uid)
            if not user:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {
                    'status': 'error',
                    'message': "Пользователь не найден"
                }
        except ValueError:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'status': 'error',
                'message': "Некорректный формат user_uid"
            }

        # Преобразуем expires_at в datetime
        try:
            expires_at_datetime = datetime.fromisoformat(expires_at)

            # Проверяем, что временная зона указана как UTC (+00:00 или Z)
            if expires_at_datetime.tzinfo is None:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    'status': 'error',
                    'message': "Требуется указать временную зону UTC",
                    'details': {
                        'expected_format': "YYYY-MM-DDTHH:MM:SS+00:00 или YYYY-MM-DDTHH:MM:SSZ"
                    }
                }

            # Приводим к UTC явно (на случай если указана другая зона)
            expires_at_utc = expires_at_datetime.astimezone(timezone.utc)
            
            # Проверяем что время действительно в UTC
            if expires_at_utc.tzinfo != timezone.utc:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    'status': 'error',
                    'message': "Время должно быть в формате UTC",
                    'details': {
                        'received_timezone': str(expires_at_datetime.tzinfo)
                    }
                }

            # Сравниваем с текущим UTC временем
            now_utc = datetime.now(timezone.utc)

            if expires_at_utc <= now_utc:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    'status': 'error',
                    'message': "Дата окончания должна быть в будущем",
                    'details': {
                        'current_time_utc': now_utc.isoformat(),
                        'provided_expires_at': expires_at_utc.isoformat()
                    }
                }
        except ValueError:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'status': 'error',
                'message': "Некорректный формат даты",
                'details': {
                    'expected_format': "YYYY-MM-DDTHH:MM:SS"
                }
            }
        
        # Создаем запись о наказании
        penalty = await Penalty.create_penalty(
            db_session=db_session,
            user_uid=user.uid,
            penalty_type=penalty_type,
            expires_at=expires_at_datetime,
            issuer_uid=request.state.user['user_uid'],
            reason=reason,
        )

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
            }
        }

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        logger.error(f"Неожиданная ошибка при назначении наказания: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': "Internal server error"
        }

@get_session
async def delete_penalty(penalty_id: int, response: Response, db_session = None):
    try:
        response_data = await Penalty.delete_penalty(db_session, penalty_id)
        return response_data
    except HTTPException:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {'status': 'error', 'message': 'Неожиданная ошибка'}

@get_session
async def get_user_rooms(target_uid: UUID, request: Request, db_session = None):
    rooms = await Room.get_rooms_by_owner(
        db=db_session,
        owner_uid=target_uid
    )

    return {'status': 'ok', "rooms": rooms}

@get_session
async def get_user_penalties(target_uid: UUID, request: Request, db_session = None):
    penalties = await Penalty.get_user_penalties(
        db_session=db_session,
        user_uid=target_uid
    )

    return {'status': 'ok', "penalties": penalties}

@get_session
async def update_user(target_uid: UUID, request: Request, response: Response, db_session=None):
    try:
        try:
            data = await request.json()
            user_data = data.get('data', {})
            if not user_data:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    'status': 'error',
                    'message': 'Отсутствуют данные для обновления'
                }
        except json.JSONDecodeError:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'status':'error',
                'message': "Invalid JSON data",
            }

        # Проверка существования пользователя
        user = db_session.query(User).filter(User.uid == target_uid).first()
        if not user:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {
                'status': 'error', 
                'message': "Пользователь не найден",
            }
        
        # Обработка аватара, если он передан
        if 'avatar' in user_data and user_data['avatar']:
            try:
                # Сохраняем файл через утилиту save_file
                avatar_url = save_file(user_data['avatar'])
                user_data['avatar'] = avatar_url  # Заменяем Base64 на URL аватара
            except HTTPException as e:
                response.status_code = e.status_code
                return {
                    'status': 'error',
                    'message': e.detail,
                }

        # Обновление профиля
        updated_user = await User.update_profile(
            db_session=db_session,
            user_uid=target_uid,
            new_data=user_data
        )

        return {
            'status': 'ok',
            "user_uid": str(target_uid),
            "user": updated_user
        }

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        logger.error(
            f"Ошибка при обновлении пользователя: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': "Ошибка при обновлении данных пользователя",   
        }