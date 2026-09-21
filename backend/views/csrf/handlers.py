from uuid import uuid4

from fastapi import Request, Response

from settings import config
from utils.csrf import CSRF_COOKIE_NAME, generate_csrf_token
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def get_csrf(request: Request, response: Response):
    session_id = str(uuid4())
    token = generate_csrf_token(session_id)
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=config.SERVER_HTTP_PROTOCOL.lower().startswith("https"),
        samesite="lax",
        max_age=config.CSRF_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    logger.debug("CSRF token issued")
    # This proof is intentionally returned to same-origin JavaScript and kept
    # in memory only. The authoritative copy remains the signed HttpOnly cookie.
    return {"status": "ok", "csrf_token": token}
