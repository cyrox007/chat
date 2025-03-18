import uuid
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from components.device.model import UserDevice
from components.decorators.db import get_session
from utils.jwt import validate_refresh_token, create_access_token, create_refresh_token

def get_server():
    return {}

@get_session
async def refresh_tokens(request: Request, db_session=None):
    # Извлекаем refresh_token из кук
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token is missing")

    # Извлечение метаданных клиента
    ip_address = request.client.host
    user_agent = request.headers.get("User-Agent")

    # Генерация новых токенов
    new_jti = str(uuid.uuid4())
    user_uid = validate_refresh_token(refresh_token)  # Предполагается, что эта функция возвращает user_uid

    new_access_token = create_access_token({"user_uid": user_uid})
    new_refresh_token = create_refresh_token({"user_uid": user_uid}, new_jti)

    # Обновление записи о токене через метод модели
    try:
        UserDevice.update_token(
            db_session=db_session,
            old_token=refresh_token,
            new_token=new_refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Устанавливаем новый refresh_token в куки
    response = JSONResponse(content={"access_token": new_access_token})
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 86400
    )

    return response