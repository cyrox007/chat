import functools
from utils.logger import setup_logger
from database import Database
from fastapi import HTTPException, status

logger = setup_logger(__name__)

def get_session(func):
    @functools.wraps(func)
    async def _wrapper(*args, **kwargs):
        # Получаем асинхронную сессию
        db_session = await Database.get_session()
        try:
            kwargs['db_session'] = db_session
            response = await func(*args, **kwargs)
            return response
        except HTTPException as http_exc:
            logger.warning(f"HTTP exception raised: {http_exc.detail}")
            raise http_exc
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            if "websocket" in kwargs:
                websocket = kwargs["websocket"]
                try:
                    await websocket.close(code=1011, reason="Internal server error")
                except Exception as ws_error:
                    logger.error(f"WebSocket close error: {ws_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        finally:
            await db_session.close()  # Асинхронное закрытие сессии
    return _wrapper