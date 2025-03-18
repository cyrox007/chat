from fastapi import FastAPI, APIRouter, WebSocket, Depends
from views.rooms.ws_handlers import handle_websocket_connection
from components.auth.middleware import auth_middle_ws

def install(app: FastAPI):
    router = APIRouter(prefix='/rooms')

    @router.websocket("/{room_uid}")
    async def websocket_endpoint(
        websocket: WebSocket,
        room_uid: str,
        user=Depends(auth_middle_ws) 
    ):
        await handle_websocket_connection(websocket, room_uid, user)

    app.include_router(router)