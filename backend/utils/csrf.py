import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Request

from settings import config


def generate_csrf_token(session_id: str | None = None) -> str:
    config.ensure_security_settings()
    session_id = session_id or str(uuid4())
    expires = datetime.now(timezone.utc) + timedelta(minutes=config.CSRF_TOKEN_EXPIRE_MINUTES)
    expires_ts = int(expires.timestamp())
    signature = hmac.new(
        config.CSRF_SECRET_KEY.encode("utf-8"),
        f"{session_id}:{expires_ts}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{session_id}:{expires_ts}:{signature}"


def validate_csrf_token(request: Request) -> bool:
    config.ensure_security_settings()
    cookie_token = request.cookies.get("XSRF-TOKEN")
    if not cookie_token:
        return False

    try:
        session_id, expires_ts_str, signature = cookie_token.split(":", 2)
        expires_ts = int(expires_ts_str)
        if expires_ts < int(datetime.now(timezone.utc).timestamp()):
            return False

        expected_signature = hmac.new(
            config.CSRF_SECRET_KEY.encode("utf-8"),
            f"{session_id}:{expires_ts}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except (ValueError, TypeError):
        return False
