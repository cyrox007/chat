import functools
import logging
from database import Database
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

def get_session(func):
    @functools.wraps(func)
    async def _wrapper(*args, **kwargs):
        kwargs['db_session'] = Database.connect_database()
        try:
            response = await func(*args, **kwargs)
            return response
        except HTTPException as http_exc:
            # Пробрасываем HTTPException дальше
            raise http_exc
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        finally:
            kwargs['db_session'].close()
    return _wrapper