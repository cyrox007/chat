from fastapi import APIRouter, Depends, FastAPI, WebSocket

from views.messenger.ws_handlers import handle_messenger_connection
from utils.logger import setup_logger
from components.auth.middleware import auth_middle_ws

logger = setup_logger(__name__)

def install(app: FastAPI):
    router = APIRouter(prefix='/ws')

    @router.websocket("/{token}/messenger")
    async def websocket_endpoint(
        websocket: WebSocket,
        token: str,
        user=Depends(auth_middle_ws)
    ):
        logger.info(f"Получен запрос на подключение WebSocket к диалогам с токеном {token[:10]}...")
        try:
            await websocket.accept()
            logger.info(f"Установлено подключение к WebSocket для диалогов")
            await handle_messenger_connection(websocket, user)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close(code=1008, reason="Connection error")
    app.include_router(router)