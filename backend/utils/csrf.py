import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Request

from settings import config


CSRF_COOKIE_NAME = "XSRF-TOKEN"
CSRF_HEADER_NAME = "X-CSRF-Token"


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


def _valid_signed_token(token: str) -> bool:
    try:
        session_id, expires_ts_str, signature = token.split(":", 2)
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


def validate_csrf_token(request: Request) -> bool:
    """Validate an explicit cookie + header CSRF proof.

    The signed token is stored in an HttpOnly SameSite cookie and echoed to the
    SPA once by /csrf/get. The SPA keeps that proof in memory and sends it in
    X-CSRF-Token for unsafe requests. A cross-site form can send cookies but
    cannot read the token response or set this custom header without passing
    the configured CORS policy.
    """
    config.ensure_security_settings()
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_token or not header_token:
        return False
    if not hmac.compare_digest(cookie_token, header_token):
        return False
    return _valid_signed_token(cookie_token)
