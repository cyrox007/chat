from fastapi import FastAPI, APIRouter, Query, WebSocket, Depends
from views.rooms.ws_handlers import handle_websocket_connection
from components.auth.middleware import auth_middle_ws
from utils.logger import setup_logger

logger = setup_logger(__name__)

def install(app: FastAPI):
    router = APIRouter(prefix='/ws')
    @router.websocket("/{token}/rooms/{room_uid}")
    async def websocket_endpoint(
        websocket: WebSocket,
        room_uid: str,
        token: str,
        user=Depends(auth_middle_ws)
    ):
        logger.info(f"Получен запрос на подключение WebSocket к комнате {room_uid} с токеном {token[:10]}...")
        try:
            await websocket.accept()
            logger.info(f"Установлено подключение к WebSocket для комнаты {room_uid}")
            await handle_websocket_connection(websocket, room_uid, user)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            #await websocket.close(code=1008, reason="Connection error")

    app.include_router(router)