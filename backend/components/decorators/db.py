import functools
from utils.logger import setup_logger
from database import Database
from fastapi import HTTPException, status

logger = setup_logger(__name__)

def get_session(func):
    @functools.wraps(func)
    async def _wrapper(*args, **kwargs):
        db_session = await Database.get_session()
        try:
            kwargs['db_session'] = db_session
            response = await func(*args, **kwargs)
            await db_session.commit()  # Явный коммит успешной операции
            return response
        except HTTPException as http_exc:
            await db_session.rollback()
            logger.warning(f"HTTP exception: {http_exc.detail}")
            raise http_exc
        except Exception as e:
            await db_session.rollback()
            logger.error(f"Database error: {str(e)}")
            if "websocket" in kwargs:
                try:
                    await kwargs["websocket"].close(code=1011, reason="Internal error")
                except Exception as ws_err:
                    logger.error(f"WebSocket close error: {ws_err}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )
        finally:
            await db_session.close()
    return _wrapper