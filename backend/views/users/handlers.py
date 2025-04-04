# Стандартные библиотеки Python
from json import JSONDecodeError
import re
import uuid

# Внешние зависимости
from fastapi import Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Annotated, List

# Локальные модули
from services.auth_service import authenticate_user, generate_tokens
from components.decorators.db import get_session
from components.device.model import UserDevice
from components.user.model import User
from components.user.exceptions import UserValidationError
from utils.jwt import create_access_token, create_refresh_token
from utils.logger import setup_logger
from utils.password import hash_password, verify_password
from utils.user_agents import parse_user_agent
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
    logger.info(f"Метаданные клиента извлечены: IP={ip_address}, User-Agent={user_agent}")
    return {
        "ip_address": ip_address,
        "user_agent": user_agent,
        "device_info": parsed_user_agent["device"],
    }


# Pydantic schema
class UserRegistrationSchema(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=50)]
    email: EmailStr
    phone: str
    password: Annotated[str, Field(min_length=8)]
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None

    @validator("phone")
    def validate_phone(cls, v):
        # Очищаем от лишних символов
        cleaned = re.sub(r"[^\d+]", "", v)

        # Проверяем полное совпадение
        if not re.fullmatch(r"^\+?(375\d{9}|7\d{10})$", cleaned):
            logger.error(f"Неверный формат номера телефона: {v}")
            raise ValueError(
                "Неверный формат номера. Примеры: +375291234567 (BY) или +79191234567 (RU)"
            )

        logger.info(f"Номер телефона успешно валидирован: {cleaned}")
        return cleaned


# Handlers
@get_session
async def register(request: Request, db_session=None):
    """
    Регистрация нового пользователя.
    """
    logger.info("Начало обработки запроса на регистрацию пользователя")
    try:
        data = UserRegistrationSchema(**await parse_request_data(request))
        logger.debug("Данные для регистрации успешно валидированы")

        if User.get_user_by_credentials(db_session, data.username):
            logger.warning(f"Пользователь с таким username уже существует: {data.username}")
            raise HTTPException(status_code=409, detail="User already exists")

        hashed_password = hash_password(data.password)
        new_user = User.create_user(
            db_session=db_session,
            username=data.username,
            email=data.email,
            phone=data.phone,
            password=hashed_password,
            first_name=data.first_name,
            last_name=data.last_name,
            gender=data.gender,
        )

        if not new_user:
            logger.error("Не удалось создать пользователя")
            raise HTTPException(status_code=500, detail="Failed to create user")

        logger.info(f"Пользователь успешно зарегистрирован: {data.username}")
        return {"status": "ok", "message": "User registered successfully"}

    except Exception as e:
        logger.exception("Произошла ошибка при регистрации пользователя")
        raise HTTPException(status_code=500, detail="Internal server error")


@get_session
async def login(request: Request, db_session=None):
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
            raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")

        identifier = data["identifier"]
        user = authenticate_user(db_session, data["identifier"], data["password"])

        tokens = generate_tokens(str(user.uid))

        client_metadata = extract_client_metadata(request)
        UserDevice.create(
            db_session=db_session,
            user_uid=str(user.uid),
            token=tokens['refresh'],
            ip_address=client_metadata["ip_address"],
            user_agent=client_metadata["user_agent"],
            device_info=client_metadata["device_info"],
        )

        response = JSONResponse(
            content={
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
        )
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh"],
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=30 * 86400,
        )

        logger.info(f"Пользователь успешно авторизован: {identifier}")
        return response

    except Exception as e:
        logger.exception("Произошла ошибка при авторизации пользователя")
        raise HTTPException(status_code=500, detail="Internal server error")


@get_session
async def logout(request: Request, db_session=None):
    """
    Выход пользователя.
    """
    logger.info("Начало обработки запроса на выход пользователя")
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            logger.info("Пользователь уже вышел из системы")
            return JSONResponse(content={"status": "ok", "message": "Already logged out"})

        try:
            UserDevice.deactivate_token(db_session, refresh_token)
            logger.info("Токен успешно деактивирован")
        except ValueError:
            logger.warning("Токен уже деактивирован или отсутствует")

        response = JSONResponse(content={"status": "ok", "message": "Logged out successfully"})
        response.delete_cookie(key="refresh_token")
        logger.info("Пользователь успешно вышел из системы")
        return response

    except Exception as e:
        logger.exception("Произошла ошибка при выходе пользователя")
        raise HTTPException(status_code=500, detail="Internal server error")


@get_session
async def get_users_by_uids(request: Request, db_session=None):
    """
    Получение данных о пользователях по их user_uid.
    """
    logger.info("Начало обработки запроса на получение данных пользователей")
    try:
        data = await parse_request_data(request)
        user_uids = data.get('user_uids')

        if not isinstance(user_uids, list) or not user_uids:
            logger.warning("Получен некорректный или пустой список user_uids")
            raise HTTPException(status_code=400, detail="Invalid or empty user_uids list")

        users_data = User.get_users_by_uids(db_session, user_uids)
        logger.info(f"Данные о пользователях успешно получены: {len(users_data)} пользователей")
        return {"status": "ok", "users": users_data}

    except Exception as e:
        logger.exception("Произошла ошибка при получении данных пользователей")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@get_session
async def get_user_by_uid(
    uid: str,
    #current_user=Depends(auth_middle),  # Сначала разрешаем аутентификацию
    db_session=None  # Затем передаем сессию БД через декоратор
):
    """
    Получение данных пользователя по его UID.
    """
    user = User.get_user_by_uid(db_session, uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    #is_owner = current_user.uid == user.uid
    user_data = {
        "full": {
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
        },
        "limited": {
            "uid": user.uid,
            "username": user.username,
            "avatar": user.avatar,
            "global_role": user.global_role,
            "rating": user.rating,
            "city": user.city,
            "country": user.country,
            "bio": user.bio,
        },
    }

    return {"status": "ok", "user": user_data["full"] }#if is_owner else user_data["limited"]}