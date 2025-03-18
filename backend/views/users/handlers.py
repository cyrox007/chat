from json import JSONDecodeError
import re
import uuid
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from components.device.model import UserDevice
from utils.user_agents import parse_user_agent
from components.decorators.db import get_session
from components.user.model import User
from components.user.exceptions import UserValidationError
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Annotated

from utils.password import hash_password, verify_password
from utils.jwt import create_access_token, create_refresh_token


# Helper functions
async def parse_request_data(request: Request):
    """
    Извлекает JSON-данные из запроса.
    """
    try:
        data = await request.json()
        if not data:
            raise HTTPException(status_code=400, detail="Empty request body")
        return data
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")


def extract_client_metadata(request: Request):
    """
    Извлекает метаданные клиента: IP, User-Agent, информацию об устройстве.
    """
    ip_address = request.client.host
    user_agent = request.headers.get("User-Agent", "")
    parsed_user_agent = parse_user_agent(user_agent)
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
            raise ValueError(
                "Неверный формат номера. Примеры: +375291234567 (BY) или +79191234567 (RU)"
            )

        return cleaned


# Handlers
@get_session
async def register(request: Request, db_session=None):
    """
    Регистрация нового пользователя.
    """
    data = UserRegistrationSchema(**await parse_request_data(request))

    existing_user = User.get_user_by_credentials(db_session, data.username)
    if existing_user:
        raise HTTPException(status_code=409, detail="User already exists")

    hashed_password = hash_password(data.password)
    try:
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
    except UserValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    if not new_user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    return {"status": "ok"}


@get_session
async def login(request: Request, db_session=None):
    """
    Авторизация пользователя.
    """
    data = await parse_request_data(request)

    required_fields = ["identifier", "password"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")

    identifier = data["identifier"]
    user = User.get_user_by_credentials(db_session, identifier)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data["password"], user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    jti = str(uuid.uuid4())
    user_uid = str(user.uid)
    access_token = create_access_token({"user_uid": user_uid})
    refresh_token = create_refresh_token({"user_uid": user_uid}, jti)

    client_metadata = extract_client_metadata(request)

    UserDevice.create(
        db_session=db_session,
        user_uid=user_uid,
        token=refresh_token,
        ip_address=client_metadata["ip_address"],
        user_agent=client_metadata["user_agent"],
        device_info=client_metadata["device_info"],
    )

    response = JSONResponse(
        content={
            "status": "ok",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "uid": user_uid,
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "avatar": user.avatar,
            },
        }
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 86400,
    )

    return response

@get_session
async def logout(request: Request, db_session=None):
    """
    Выход пользователя.
    """
    # Извлекаем refresh_token из кук
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return JSONResponse(content={"status": "ok", "message": "Already logged out"})

    # Деактивируем токен в базе данных
    try:
        UserDevice.deactivate_token(db_session, refresh_token)
    except ValueError:
        pass  # Токен уже деактивирован или отсутствует

    # Очищаем куки
    response = JSONResponse(content={"status": "ok", "message": "Logged out successfully"})
    response.delete_cookie(key="refresh_token")
    return response