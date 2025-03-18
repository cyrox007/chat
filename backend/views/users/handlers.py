from json import JSONDecodeError
import re
import uuid
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from components.decorators.db import get_session
from components.user.model import User
from components.user.exceptions import UserValidationError
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Annotated

from utils.password import hash_password, verify_password
from utils.jwt import create_access_token, create_refresh_token

class UserRegistrationSchema(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=50)]
    email: EmailStr
    phone: str  # Убрана валидация через Field
    password: Annotated[str, Field(min_length=8)]
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None

    @validator('phone')
    def validate_phone(cls, v):
        # Очищаем от лишних символов
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Проверяем полное совпадение
        if not re.fullmatch(r'^\+?(375\d{9}|7\d{10})$', cleaned):
            raise ValueError(
                'Неверный формат номера. Примеры: '
                '+375291234567 (BY) или +79191234567 (RU)'
            )
        
        return cleaned

@get_session
async def register(request: Request, data: UserRegistrationSchema, db_session = None):
    """
    Регистрация нового пользователя.
    """
    # Проверка уникальности данных
    existing_user = User.get_user_by_credentials(db_session, data.username)
    if existing_user:
        raise HTTPException(status_code=409, detail="User already exists")
    
    # Создание пользователя
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
            gender=data.gender
        )
    except UserValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    if not new_user:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    return {
        'status': 'ok'
    }

@get_session
async def login(request: Request, db_session = None):
    """
    Авторизация пользователя.
    """
    try:
        data = await request.json()
    except JSONDecodeError:
        # Будет обработано декоратором и вернёт 400
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    
    # Остальная логика остается без изменений
    if not data:
        raise HTTPException(status_code=400, detail="Empty request body")
    
    # Проверка обязательных полей
    required_fields = ["identifier", "password"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")

    # Поиск пользователя по логину, почте или телефону
    identifier = data["identifier"]  # Это может быть username, email или phone
    user = User.get_user_by_credentials(db_session, identifier)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Проверка пароля
    if not verify_password(data["password"], user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Генерация уникального JTI
    jti = str(uuid.uuid4())  # Уникальный идентификатор токена
    # Преобразование user.uid в строку (если это UUID)
    user_uid = str(user.uid)

    # Генерация токенов
    access_token = create_access_token({"user_uid": user_uid})
    refresh_token = create_refresh_token({"user_uid": user_uid}, jti)

    # Формируем ответ
    response = JSONResponse(content={
        'status': 'ok',
        'access_token': access_token,
        'token_type': 'bearer',
        'user': {
            'uid': user_uid,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'avatar': user.avatar
        }
    })

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 86400
    )

    return response