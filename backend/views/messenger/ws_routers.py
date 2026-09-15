from fastapi import APIRouter, FastAPI, WebSocket, status

from utils.logger import setup_logger
from views.messenger.ws_handlers import handle_messenger_connection
from views.realtime.ws_auth import authenticate_websocket

logger = setup_logger(__name__)


def install(app: FastAPI):
    router = APIRouter(prefix="/ws/v2")

    @router.websocket("/messenger")
    async def websocket_endpoint(websocket: WebSocket):
        user = await authenticate_websocket(
            websocket=websocket,
            target="messenger",
        )
        if not user:
            return

        try:
            await handle_messenger_connection(websocket, user)
        except Exception as exc:
            logger.exception("Messenger WebSocket error: %s", exc)
            try:
                await websocket.close(
                    code=status.WS_1011_INTERNAL_ERROR,
                    reason="Realtime messenger error",
                )
            except Exception:
                pass

    app.include_router(router)
