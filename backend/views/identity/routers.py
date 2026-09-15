from fastapi import APIRouter, Depends, FastAPI, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from components.auth.middleware import auth_middle
from components.identity.schemas import (
    LoginRequest,
    PersonaUpdateRequest,
    PrivacyUpdateRequest,
    RegisterRequest,
)
from components.identity.service import (
    authenticate_account,
    build_identity_projection,
    build_public_profile,
    get_account_by_uid,
    register_account,
    revoke_session,
    rotate_session,
    update_primary_persona,
    update_privacy,
)
from database import Database
from settings import config


COOKIE_NAME = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=config.SERVER_HTTP_PROTOCOL.lower().startswith("https"),
        samesite="lax",
        max_age=config.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )


def install(app: FastAPI):
    router = APIRouter(prefix="/identity/v2", tags=["identity-v2"])

    @router.post("/register", status_code=status.HTTP_201_CREATED)
    async def register(
        payload: RegisterRequest,
        request: Request,
        response: Response,
        db: AsyncSession = Depends(Database.session_generator),
    ):
        account, tokens = await register_account(db, payload, request)
        projection = await build_identity_projection(db, account)
        _set_refresh_cookie(response, tokens["refresh"])
        return {
            "status": "ok",
            "access_token": tokens["access"],
            "token_type": "bearer",
            **projection,
        }

    @router.post("/login")
    async def login(
        payload: LoginRequest,
        request: Request,
        response: Response,
        db: AsyncSession = Depends(Database.session_generator),
    ):
        account, tokens = await authenticate_account(db, payload.identifier, payload.password, request)
        projection = await build_identity_projection(db, account)
        _set_refresh_cookie(response, tokens["refresh"])
        return {
            "status": "ok",
            "access_token": tokens["access"],
            "token_type": "bearer",
            **projection,
        }

    @router.post("/refresh")
    async def refresh(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(Database.session_generator),
    ):
        refresh_token = request.cookies.get(COOKIE_NAME)
        account, tokens = await rotate_session(db, refresh_token or "", request)
        _set_refresh_cookie(response, tokens["refresh"])
        return {
            "status": "ok",
            "access_token": tokens["access"],
            "token_type": "bearer",
            "account_uid": str(account.uid),
        }

    @router.post("/logout")
    async def logout(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(Database.session_generator),
    ):
        await revoke_session(db, request.cookies.get(COOKIE_NAME))
        response.delete_cookie(COOKIE_NAME, path="/")
        return {"status": "ok"}

    @router.get("/me")
    async def me(
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        account = await get_account_by_uid(db, current_user["user_uid"])
        return {"status": "ok", **(await build_identity_projection(db, account))}

    @router.get("/profiles/{account_uid}")
    async def public_profile(
        account_uid: str,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        account = await get_account_by_uid(db, account_uid)
        profile = await build_public_profile(db, account, current_user["user_uid"])
        return {"status": "ok", "profile": profile}

    @router.patch("/persona")
    async def patch_persona(
        payload: PersonaUpdateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        account = await get_account_by_uid(db, current_user["user_uid"])
        return {"status": "ok", **(await update_primary_persona(db, account, payload))}

    @router.patch("/privacy")
    async def patch_privacy(
        payload: PrivacyUpdateRequest,
        current_user: dict = Depends(auth_middle),
        db: AsyncSession = Depends(Database.session_generator),
    ):
        account = await get_account_by_uid(db, current_user["user_uid"])
        return {"status": "ok", **(await update_privacy(db, account, payload))}

    app.include_router(router)
