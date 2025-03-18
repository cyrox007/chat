from uuid import uuid4
from fastapi import APIRouter, Response, Request
from utils.csrf import generate_csrf_token

async def get_csrf(request: Request, response: Response):
    # Генерируем новый session_id для каждого запроса
    session_id = str(uuid4())
    token = generate_csrf_token(session_id)
    
    response.set_cookie(
        key="XSRF-TOKEN",
        value=token,
        httponly=True,
        secure=False,  # True в production
        samesite="lax",
        max_age=1800  # 30 минут
    )
    
    return {"status": "ok"}