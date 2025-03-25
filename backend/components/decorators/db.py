import functools
import logging
from database import Database
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

def get_session(func):
    @functools.wraps(func)
    async def _wrapper(*args, **kwargs):
        db_session = Database.connect_database()
        try:
            kwargs['db_session'] = db_session
            response = await func(*args, **kwargs)
            return response
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            if "websocket" in kwargs:
                await kwargs["websocket"].close(code=1011, reason="Internal server error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        finally:
            db_session.close()
    return _wrapper