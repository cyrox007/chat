from fastapi import HTTPException, Request, status
from sqlalchemy import select

from components.auth.middleware import auth_middle
from components.identity.model import Account, AccountRole, PlatformRole
from database import Database
from utils.logger import setup_logger

logger = setup_logger(__name__)

SAFE_PROFILE_UPDATE_FIELDS = frozenset(
    {
        "username",
        "first_name",
        "last_name",
        "avatar",
        "city",
        "country",
        "bio",
        "date_of_birth",
        "gender",
        "career",
        "education",
        "marital_status",
    }
)


async def _current_user_data(request: Request) -> dict:
    user_data = getattr(request.state, "user", None)
    if not user_data:
        user_data = await auth_middle(request)
    return user_data


async def require_admin(request: Request):
    """Require an active platform administrator from Identity v2 RBAC."""
    user_data = await _current_user_data(request)
    session = await Database.get_session()
    try:
        account = await session.get(Account, user_data["user_uid"])
        if not account or account.deleted_at or account.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"status": "bad", "error_type": "account_unavailable"},
            )

        role_result = await session.execute(
            select(PlatformRole.name)
            .join(AccountRole, AccountRole.role_id == PlatformRole.id)
            .where(
                AccountRole.account_uid == account.uid,
                PlatformRole.name == "admin",
            )
            .limit(1)
        )
        if role_result.scalar_one_or_none() != "admin":
            logger.warning("Запрещен доступ к admin API для account=%s", account.uid)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"status": "bad", "error_type": "admin_required"},
            )

        request.state.auth_account = account
        return account
    finally:
        await session.close()


async def validate_profile_update(request: Request):
    """
    Protect the legacy profile endpoint from IDOR and mass assignment.

    This dependency exists only while old clients finish migrating to
    /identity/v2/persona. New code must not add fields to this allow-list.
    """
    user_data = await _current_user_data(request)

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "bad", "error_type": "invalid_json"},
        ) from exc

    target_user_uid = str(payload.get("user_uid") or "")
    if target_user_uid != str(user_data["user_uid"]):
        logger.warning(
            "Отклонена попытка обновления чужого профиля: actor=%s target=%s",
            user_data["user_uid"],
            target_user_uid,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"status": "bad", "error_type": "profile_owner_required"},
        )

    update_data = payload.get("data")
    if not isinstance(update_data, dict) or not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "bad", "error_type": "invalid_profile_update"},
        )

    forbidden_fields = sorted(set(update_data) - SAFE_PROFILE_UPDATE_FIELDS)
    if forbidden_fields:
        logger.warning(
            "Отклонены запрещенные поля legacy-профиля для пользователя %s: %s",
            user_data["user_uid"],
            forbidden_fields,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "bad",
                "error_type": "forbidden_profile_fields",
                "fields": forbidden_fields,
            },
        )

    return user_data
