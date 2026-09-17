from fastapi import HTTPException, Request, status

from components.moderation.account_access import assert_http_account_access
from database import Database
from utils.jwt import validate_access_token
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def auth_middle(request: Request):
    token = request.headers.get("authorization")
    if not token:
        logger.warning("Отсутствующий токен в HTTP-запросе")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "bad", "error_type": "missing_token"},
        )

    user_data = validate_access_token(token)
    if not user_data:
        logger.warning("Недопустимый токен в HTTP-запросе")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "bad", "error_type": "invalid_token"},
        )

    request.state.user = user_data
    request.state.user_uid = user_data["user_uid"]

    # Access JWTs are intentionally stateless and short-lived, so a platform
    # suspension cannot rely only on refresh-token revocation. Every authenticated
    # HTTP request re-checks the durable account.access restriction. The narrow
    # exemption list keeps Safety/Appeal and identity bootstrap reachable.
    session = await Database.get_session()
    try:
        await assert_http_account_access(
            session,
            request,
            user_data["user_uid"],
        )
    finally:
        await session.close()

    logger.info("HTTP-аутентификация успешна для пользователя %s", user_data["user_uid"])
    return user_data


async def authorize_user(current_user, target_user_uid, required_role=None):
    """
    Legacy authorization helper kept for compatibility during the revival migration.

    Role checks must not rely on JWT claims. Use server-side permission dependencies
    that read the current role from the database.
    """
    current_uid = current_user.get("user_uid")
    if current_uid == str(target_user_uid):
        return True

    if required_role:
        logger.warning(
            "Отклонена legacy-проверка роли %s для пользователя %s",
            required_role,
            current_uid,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"status": "bad", "error_type": "insufficient_permissions"},
        )

    return False
