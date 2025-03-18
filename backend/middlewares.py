from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
import logging

from utils.csrf import validate_csrf_token

logger = logging.getLogger(__name__)

def csrf_middleware(app):
    @app.middleware("http")
    async def csrf_handler(request: Request, call_next):
        try:
            if request.method in {"GET", "HEAD", "OPTIONS"}:
                return await call_next(request)
            if not validate_csrf_token(request):
                raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
            return await call_next(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        except Exception as exc:
            logger.error(f"CSRF validation failed: {str(exc)}")
            return JSONResponse(status_code=400, content={"detail": "CSRF validation error"})

def error_handling_middleware(app):
    @app.middleware("http")
    async def error_handler(request: Request, call_next):
        try:
            return await call_next(request)
        except OperationalError as exc:
            logger.error(f"Database connection error: {str(exc)}")
            return JSONResponse(status_code=503, content={"detail": "Database is temporarily unavailable."})
        except Exception as exc:
            logger.exception("Unexpected error occurred")
            return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})