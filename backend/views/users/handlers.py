# Стандартные библиотеки Python
from datetime import datetime
from json import JSONDecodeError
import json
from typing import Any, Dict
from uuid import UUID

# Внешние зависимости
from fastapi import Depends, Request, HTTPException, Response, UploadFile, status
from fastapi.responses import JSONResponse

# Локальные модули
from services.auth_service import generate_tokens
from components.decorators.db import get_session
from components.device.model import UserDevice
from components.user.model import User
from utils.logger import setup_logger
from utils.password import hash_password, verify_password
from utils.user_agents import parse_user_agent
from utils.file_handler import save_file, save_uploaded_file
from components.auth.middleware import auth_middle, authorize_user


# Создаем логгер
logger = setup_logger(__name__)


# Helper functions
async def parse_request_data(request: Request):
    """
    Извлекает JSON-данные из запроса.
    """
    try:
        data = await request.json()
        if not data:
            logger.error("Пустое тело запроса")
            raise HTTPException(status_code=400, detail="Empty request body")
        logger.info("Данные запроса успешно извлечены")
        return data
    except JSONDecodeError:
        logger.error("Ошибка разбора JSON: Неверный формат данных")
        raise HTTPException(status_code=400, detail="Invalid JSON format")


def extract_client_metadata(request: Request):
    """
    Извлекает метаданные клиента: IP, User-Agent, информацию об устройстве.
    """
    ip_address = request.client.host
    user_agent = request.headers.get("User-Agent", "")
    parsed_user_agent = parse_user_agent(user_agent)
    logger.info(f"Метаданные клиента извлечены: IP={ip_address}, User-Agent={parsed_user_agent}")
    return {
        "ip_address": ip_address,
        "user_agent": user_agent,
        "device_info": parsed_user_agent,
    }


# Handlers
@get_session
async def register(request: Request, response: Response, db_session=None):
    """
    Регистрация нового пользователя.
    """
    logger.info("Начало обработки запроса на регистрацию пользователя")
    
    try:
        # Извлекаем данные строго из JSON тела запроса
        data: Dict[str, Any] = await request.json()
        
        # Валидация обязательных полей
        required_fields = ['username', 'email', 'phone', 'password']
        if missing_fields := [
            field for field in required_fields 
            if field not in data or not data[field]
        ]:
            error_msg = f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
            logger.warning(error_msg)
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                "status": "error",
                "message": error_msg,
                "details": {"missing_fields": missing_fields}
            }

        # Оптимизированная проверка уникальности
        uniqueness_checks = {
            'username': data['username'],
            'email': data['email'],
            'phone': data['phone']
        }
        
        existing_fields = {}
        for field, value in uniqueness_checks.items():
            if user := await User.get_user_by_credentials(db_session, value):
                existing_fields[field] = f"Пользователь с таким {field} уже существует"
        
        if existing_fields:
            logger.warning(f"Конфликт уникальности: {existing_fields}")
            response.status_code = status.HTTP_409_CONFLICT
            return {
                "status": "error",
                "message": "Пользователь с такими данными уже существует",
                "details": {"conflict_fields": existing_fields}
            }

        # Обработка аватара
        avatar_url = None
        if 'avatar' in data and data['avatar']:
            try:
                avatar_data = data['avatar']
                if not {'name', 'size', 'type', 'url'}.issubset(avatar_data.keys()):
                    raise ValueError("Неверный формат аватара: отсутствуют обязательные поля")
                
                avatar_url = save_file(avatar_data)
            except Exception as e:
                logger.error(f"Ошибка обработки аватара: {str(e)}")
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    "status": "error",
                    "message": "Некорректные данные аватара",
                    "details": {"avatar_error": str(e)}
                }

        # Обработка даты рождения
        date_of_birth = None
        if dob_str := data.get('date_of_birth'):
            try:
                date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Неверный формат даты рождения: {dob_str}")
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    "status": "error",
                    "message": "Неверный формат даты. Используйте YYYY-MM-DD",
                    "details": {"field": "date_of_birth"}
                }

        # Создание пользователя
        if not (new_user := await User.create_user(
            db_session=db_session,
            username=data['username'],
            email=data['email'],
            phone=data['phone'],
            password=hash_password(data['password']),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            gender=data.get('gender'),
            avatar=avatar_url,
            bio=data.get('bio'),
            date_of_birth=date_of_birth
        )):
            error_msg = "Ошибка при создании пользователя в БД"
            logger.error(error_msg)
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {
                "status": "error",
                "message": error_msg
            }

        logger.info(f"Успешная регистрация: {data['username']}")
        return {
            "status": "ok",
            "message": "Пользователь успешно зарегистрирован",
            "data": {
                "user_id": str(new_user.uid),
                "username": new_user.username,
                "email": new_user.email,
                "avatar": avatar_url
            }
        }

    except Exception as e:
        logger.exception("Ошибка при регистрации пользователя")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": "error",
            "message": "Внутренняя ошибка сервера",
            "details": str(e)
        }
        
    
@get_session
async def check_username(request: Request, db_session=None):
    data = await parse_request_data(request)
    username = data.get("username")
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    is_unique = not await User.get_user_by_credentials(db_session, username)
    return {"isUnique": is_unique}

@get_session
async def check_email(request: Request, db_session=None):
    data = await parse_request_data(request)
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    is_unique = not await User.get_user_by_credentials(db_session, email)
    return {"isUnique": is_unique}

@get_session
async def check_phone(request: Request, db_session=None):
    data = await parse_request_data(request)
    phone = data.get("phone")
    if not phone:
        raise HTTPException(status_code=400, detail="Phone is required")
    is_unique = not await User.get_user_by_credentials(db_session, phone)
    return {"isUnique": is_unique}

@get_session
async def login(request: Request, response: Response, db_session=None):
    """
    Авторизация пользователя.
    """
    logger.info("Начало обработки запроса на авторизацию пользователя")
    try:
        data = await parse_request_data(request)

        required_fields = ["identifier", "password"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            logger.warning(f"Отсутствуют обязательные поля: {', '.join(missing_fields)}")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {'status': 'error', 'message': f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"}

        
        user = await User.get_user_by_credentials(db_session, data["identifier"])
        if not user or not verify_password(data["password"], user.hashed_password):
            logger.warning(f"Неверные учетные данные для пользователя: {data['identifier']}")
            response.status_code = status.HTTP_403_FORBIDDEN
            return {'status': 'error', 'message': f"Неверные учетные данные для пользователя: {data['identifier']}"}
    
        tokens = generate_tokens(str(user.uid))

        client_metadata = extract_client_metadata(request)
        await UserDevice.create(
            db_session=db_session,
            user_uid=str(user.uid),
            token=tokens['refresh'],
            ip_address=client_metadata["ip_address"],
            user_agent=client_metadata["user_agent"],
            device_info=client_metadata["device_info"],
        )

        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh"],
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=30 * 86400,
        )

        logger.info(f"Пользователь успешно авторизован: {data['identifier']}")
        return {
            "status": "ok",
            "access_token": tokens["access"],
            "token_type": "bearer",
            "user": {
                "uid": str(user.uid),
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "avatar": user.avatar,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "global_role": user.global_role,
                "rating": user.rating,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "city": user.city,
                "country": user.country,
                "bio": user.bio,
                "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
                "gender": user.gender,
                "career": user.career,
                "education": user.education,
                "marital_status": user.marital_status,
                "last_online": user.last_online.isoformat() if user.last_online else None,
            },
        }

    except Exception as e:
        logger.exception("Произошла ошибка при авторизации пользователя")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {'status': 'error', 'message': f"Internal server error"}


@get_session
async def logout(request: Request, response: Response, db_session=None):
    """
    Выход пользователя.
    """
    logger.info("Начало обработки запроса на выход пользователя")
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            logger.info("Пользователь уже вышел из системы")
            return {"status": "ok", "message": "Already logged out"}

        try:
            await UserDevice.deactivate_token(db_session, refresh_token)
            logger.info("Токен успешно деактивирован")
        except ValueError:
            logger.warning("Токен уже деактивирован или отсутствует")

        response.delete_cookie(key="refresh_token")
        logger.info("Пользователь успешно вышел из системы")
        return {"status": "ok", "message": "Logged out successfully"}

    except Exception as e:
        logger.exception("Произошла ошибка при выходе пользователя")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {'status': 'error', 'message': f"Internal server error"}


@get_session
async def get_users_by_uids(request: Request, response: Response, db_session = None):
    """Получение данных о пользователях по их user_uid."""
    logger.info("Начало обработки запроса на получение данных пользователей")
    try:
        # Парсим входные данные
        data = await parse_request_data(request)
        user_uids = data.get('user_uids')

        # Проверяем, что user_uids существует и является списком
        if not user_uids or not isinstance(user_uids, list):
            logger.warning("Получен некорректный или пустой список user_uids")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"status": "error", "message": "Получен некорректный или пустой список user_uids"}

        # Получаем пользователей из базы данных
        users_list = await User.get_users_by_uids(db_session, user_uids)

        logger.info(f"Данные успешно получены для {len(users_list)} пользователей")
        return {"status": "ok", "users": users_list}

    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении данных пользователей: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "message": "Произошла внутренняя ошибка сервера"}


@get_session
async def get_user_by_uid(user_uid: UUID, response: Response, db_session = None):
    """
    Получение данных пользователя по его UID.
    """
    user = await User.get_user_by_uid(db_session, str(user_uid))
    if not user:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"status": "ok", "message":"Пользователь не найден"}

    user_data = {
        "uid": user.uid,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar": user.avatar,
        "global_role": user.global_role,
        "rating": user.rating,
        "city": user.city,
        "country": user.country,
        "bio": user.bio,
        "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
        "gender": user.gender,
        "career": user.career,
        "education": user.education,
        "marital_status": user.marital_status,
        "last_online": user.last_online.isoformat() if user.last_online else None,
    }

    return {"status": "ok", "user": user_data }

@get_session
async def get_user_statuses(request: Request, response: Response, db_session = None):
    try:
        # Получаем данные из запроса
        data: dict = await request.json()
        user_uids = data.get('user_ids')

        # Проверяем, что user_ids существует и является списком
        if not user_uids or not isinstance(user_uids, list):
            response.status_code = status.HTTP_400_BAD_REQUEST
            #raise HTTPException(status_code=400, detail="Invalid or missing 'user_ids' in request")
            return {"status": "error", "message": "Invalid or missing 'user_ids' in request"}

        # Получаем пользователей из базы данных
        users = await User.get_users_by_uids(db_session, user_uids)

        # Формируем статусы пользователей
        statuses = {
            str(user.uid): {
                "last_online": user.last_online.isoformat() if user.last_online else None
            }
            for user in users
        }

        return {"status": "ok", "statuses": statuses}

    except Exception as e:
        # Логируем ошибку и возвращаем HTTP-ошибку
        logger.error(f"Ошибка при получении статусов пользователей: {e}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        #raise HTTPException(status_code=500, detail="Internal server error")
        return {"status": "error", "message": "Произошла внутренняя ошибка сервера"}

@get_session
async def delete_user(request: Request, response: Response, db_session = None):
    """
    Мягкое удаление пользователя (обновление поля deleted_at).

    :param request: Запрос FastAPI.
    :param db_session: Сессия базы данных.
    :return: Ответ о статусе операции.
    """
    try:
        # Получаем UID пользователя из запроса
        user_uid = request.state.user_uid # Предполагается, что UID текущего пользователя доступен через request.state.user

        # Выполняем "мягкое" удаление через метод модели
        await User.soft_delete(db_session, user_uid)

        # Возвращаем успешный ответ в формате JSON
        return {"status": "ok", "message": "Профиль успешно удален"}

    except HTTPException as http_error:
        # Логируем ошибку и возвращаем JSON-ответ
        logger.error(f"Ошибка при удалении пользователя: {http_error.detail}")
        response.status_code = http_error.status_code
        return {"status": "error", "message": http_error.detail}

    except Exception as e:
        # Логируем неожиданную ошибку и возвращаем JSON-ответ
        logger.error(f"Неожиданная ошибка при удалении пользователя: {str(e)}")
        db_session.rollback()  # Откатываем изменения в случае ошибки
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "message": "Произошла внутренняя ошибка сервера"}
    
@get_session
async def update_profile(request: Request, response: Response, db_session=None):
    """Обновление данных профиля пользователя."""
    logger.info("Начало обработки запроса на обновление профиля")
    try:
        # Парсим входные данные
        data = await request.json()
        target_user_uid = data.get("user_uid")
        updated_data = data.get("data")
        
        # Проверяем, что все необходимые поля присутствуют
        if not target_user_uid or not updated_data:
            logger.warning("Отсутствуют обязательные поля: user_uid или updated_data")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"status": "error", "message": "Missing required fields"}

        if 'avatar' in updated_data and updated_data['avatar']:
            try:
                # Сохраняем файл через утилиту save_file
                avatar_url = save_file(updated_data['avatar'])
                updated_data['avatar'] = avatar_url  # Заменяем Base64 на URL аватара
            except HTTPException as e:
                response.status_code = e.status_code
                return {
                    'status': 'error',
                    'message': e.detail,
                }
        print(updated_data)
        user = await User.update_profile(db_session, target_user_uid, updated_data)
        
        if not user: 
            logger.warning("ОБновление не произошло")
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        logger.info(f"Данные пользователя {target_user_uid} успешно обновлены")
        return {"status": "ok", "user": user.__dict__}

    except HTTPException as http_error:
        logger.error(f"Ошибка при обновлении профиля: {http_error.detail}")
        response.status_code = http_error.status_code
        return {"status": "error", "message": f"Ошибка при обновлении профиля: {http_error.detail}"}

    except Exception as e:
        logger.error(f"Неожиданная ошибка при обновлении профиля: {str(e)}")
        db_session.rollback()
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "message": "Произошла внутренняя ошибка сервера"}