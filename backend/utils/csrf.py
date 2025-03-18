import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import Request

SECRET_KEY = "ваш-секретный-ключ"
MSK_TZ = timezone(timedelta(hours=3))

def generate_csrf_token(session_id: str = None) -> str:
    session_id = session_id or str(uuid4())
    # Используем локальное время сервера (MSK)
    expires = datetime.now(MSK_TZ).replace(microsecond=0) + timedelta(minutes=30)
    expires_ts = int(expires.timestamp())
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        f"{session_id}:{expires_ts}".encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    token = f"{session_id}:{expires_ts}:{signature}"
    #print(f"Generated Token (MSK): {expires}")
    return token

def validate_csrf_token(request: Request) -> bool:
    cookie_token = request.cookies.get("XSRF-TOKEN")
    if not cookie_token:
        return False
    
    try:
        session_id, expires_ts_str, signature = cookie_token.split(":", 2)
        expires_ts = int(expires_ts_str)
        # Преобразуем timestamp в datetime с учётом MSK
        expires = datetime.fromtimestamp(expires_ts, tz=MSK_TZ)
        current_time = datetime.now(MSK_TZ).replace(microsecond=0)
        
        #print(f"Expires (MSK): {expires}, Current (MSK): {current_time}")
        
        if expires < current_time:
            print("Token expired")
            return False
        
        expected_signature = hmac.new(
            SECRET_KEY.encode('utf-8'),
            f"{session_id}:{expires_ts}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except (ValueError, TypeError) as e:
        print(f"Validation error: {str(e)}")
        return False