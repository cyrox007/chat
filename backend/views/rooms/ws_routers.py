from fastapi import FastAPI, APIRouter, Query, WebSocket, Depends
from views.rooms.ws_handlers import handle_websocket_connection
from components.auth.middleware import auth_middle_ws


import logging

logger = logging.getLogger(__name__)

def install(app: FastAPI):
    router = APIRouter(prefix='/ws/rooms')
    @router.websocket("/{room_uid}")
    async def websocket_endpoint(
        websocket: WebSocket,
        room_uid: str,
        token: str = Query(...),
        user=Depends(auth_middle_ws)
    ):
        logger.info(f"WebSocket request received for room {room_uid}")
        try:
            await websocket.accept()
            logger.info(f"WebSocket connection established for room {room_uid}")
            await handle_websocket_connection(websocket, room_uid, user)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close(code=1008, reason="Connection error")

    app.include_router(router)