from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from jwt import PyJWTError

from components.device.model import UserDevice
from components.decorators.db import get_session
from utils.jwt import validate_refresh_token, validate_access_token, create_access_token, create_refresh_token
from utils.logger import setup_logger

logger = setup_logger(__name__)

def get_server():
    return {}

@get_session
async def refresh_tokens(request: Request, db_session=None):
    try:
        # Логирование начала обработки запроса
        logger.info("Начало обработки запроса на обновление токенов.")

        # Извлекаем refresh_token из кук
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            logger.warning("Refresh token отсутствует в куках.")
            raise HTTPException(status_code=403, detail="Refresh token is missing")

        logger.debug(f"Получен refresh_token: {refresh_token}")

        # Извлечение метаданных клиента
        ip_address = request.client.host
        user_agent = request.headers.get("User-Agent")
        logger.debug(f"IP-адрес клиента: {ip_address}, User-Agent: {user_agent}")

        # Валидация refresh_token
        logger.info("Начало валидации refresh_token.")
        try:
            user_uid = validate_refresh_token(refresh_token).get('user_uid')
            if not user_uid:
                logger.warning("Не удалось получить user_uid из refresh_token.")
                raise HTTPException(status_code=403, detail="Invalid refresh token")
        except PyJWTError:
            logger.warning("Ошибка валидации refresh_token.")
            raise HTTPException(status_code=403, detail="Invalid refresh token")
        
        logger.info(f"Refresh token успешно валидирован для пользователя: {user_uid}")

        # Генерация новых токенов
        logger.info("Генерация новых access_token и refresh_token.")
        new_access_token = create_access_token({"user_uid": user_uid})
        new_refresh_token = create_refresh_token({"user_uid": user_uid})

        #logger.debug(f"Сгенерирован новый access_token: {new_access_token}")
        #logger.debug(f"Сгенерирован новый refresh_token: {new_refresh_token}")

        # Обновление записи о токене через метод модели
        logger.info("Обновление записи о токене в базе данных.")
        try:
            await UserDevice.update_token(
                db_session=db_session,
                old_token=refresh_token,
                new_token=new_refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except ValueError as e:
            logger.error(f"Ошибка при обновлении токена в базе данных: {e}")
            
            # Проверяем, существует ли новый токен
            existing_record = await UserDevice.find_active_by_token(db_session, new_access_token)
            
            if existing_record:
                logger.info(f"Новый токен {new_refresh_token} уже существует. Возвращаем существующий токен.")
                # Формируем ответ с уже существующим токеном
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
            else:
                return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"status": "bed", "message": "Invalid or inactive refresh token"} )

        logger.info("Запись о токене успешно обновлена в базе данных.")

        # Создание ответа с новым access_token и установка нового refresh_token в куки
        response = JSONResponse(content={"access_token": new_access_token})
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=30 * 86400
        )

        logger.info("Ответ успешно сформирован и отправлен клиенту.")
        return response

    except Exception as e:
        logger.error(f"Произошла необработанная ошибка: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@get_session
async def check_token(request: Request, response: Response, db_session=None):
    try:
        # Получаем токен из параметров запроса
        access_token = request.headers.get("authorization")
        if not access_token:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"status": "error", "message": "Access token is missing"}, 400

        # Проверяем токен
        payload = validate_access_token(access_token)
        if not payload:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return {"status": "error", "message": "Invalid or expired token"}, 401

        # Если токен действителен, возвращаем успешный ответ
        return {"status": "ok", "message": "Token is valid"}

    except Exception as e:
        # Логируем ошибку для отладки
        print(f"Unexpected error in check_token: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "message": "Internal server error"}, 500