from fastapi import APIRouter, Depends, FastAPI, WebSocket, status

from utils.jwt import validate_access_token
from views.messenger.ws_handlers import handle_messenger_connection
from utils.logger import setup_logger
from components.auth.middleware import auth_middle_ws

logger = setup_logger(__name__)

def install(app: FastAPI):
    router = APIRouter(prefix='/ws')

    @router.websocket("/{token}/messenger")
    async def websocket_endpoint(websocket: WebSocket, token: str):
        # 1. Проверяем токен ДО принятия соединения
        user_data = validate_access_token(token)
        if not user_data:
            logger.error("Неверный токен, закрываем соединение с кодом 1008")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return  # Важно: завершаем функцию, иначе FastAPI попытается принять соединение

        # 2. Если токен валиден, принимаем соединение
        await websocket.accept()
        
        try:
            await handle_messenger_connection(websocket, user_data)
        except Exception as e:
            logger.error(f"Ошибка в WebSocket: {e}")
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Server error")
    app.include_router(router)