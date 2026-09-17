from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from components.device.model import UserDevice
from components.identity.model import Account, IdentitySession
from components.moderation.model import PlatformRestriction
from components.realtime import RealtimeUnavailable, realtime_service
from utils.logger import setup_logger

logger = setup_logger(__name__)

ACCOUNT_ACCESS_CAPABILITY = "account.access"

# A suspended Account must retain the minimum surface needed to understand and
# challenge the sanction, keep its limited session alive, and explicitly log out.
ACCOUNT_ACCESS_HTTP_EXEMPTIONS: tuple[tuple[str, str], ...] = (
    ("GET", "/identity/v2/me"),
    ("GET", "/trust-safety/v1/me/restrictions"),
    ("GET", "/trust-safety/v1/me/restriction-appeals"),
)


def _restriction_projection(restriction: PlatformRestriction) -> dict:
    return {
        "uid": str(restriction.uid),
        "capability": restriction.capability,
        "scope_type": restriction.scope_type,
        "scope_uid": str(restriction.scope_uid) if restriction.scope_uid else None,
        "public_explanation": restriction.public_explanation,
        "starts_at": restriction.starts_at.isoformat(),
        "expires_at": restriction.expires_at.isoformat() if restriction.expires_at else None,
    }


def is_account_access_http_exempt(request: Request) -> bool:
    method = request.method.upper()
    path = request.url.path.rstrip("/") or "/"
    if (method, path) in ACCOUNT_ACCESS_HTTP_EXEMPTIONS:
        return True
    if method == "POST" and path.startswith("/trust-safety/v1/restrictions/") and path.endswith("/appeals"):
        return True
    return False


async def _resolve_account_uid(db: AsyncSession, subject_uid: UUID | str) -> UUID | None:
    try:
        uid = UUID(str(subject_uid))
    except (TypeError, ValueError, AttributeError):
        return None

    result = await db.execute(
        select(Account.uid)
        .where(
            or_(Account.uid == uid, Account.legacy_user_uid == uid),
            Account.deleted_at.is_(None),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def active_account_access_restriction(
    db: AsyncSession,
    subject_uid: UUID | str,
) -> PlatformRestriction | None:
    account_uid = await _resolve_account_uid(db, subject_uid)
    if account_uid is None:
        return None

    now = datetime.utcnow()
    result = await db.execute(
        select(PlatformRestriction)
        .where(
            PlatformRestriction.target_account_uid == account_uid,
            PlatformRestriction.capability == ACCOUNT_ACCESS_CAPABILITY,
            PlatformRestriction.scope_type == "platform",
            PlatformRestriction.status == "active",
            PlatformRestriction.starts_at <= now,
            or_(PlatformRestriction.expires_at.is_(None), PlatformRestriction.expires_at > now),
        )
        .order_by(PlatformRestriction.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def account_access_projection(
    db: AsyncSession,
    subject_uid: UUID | str,
) -> dict | None:
    restriction = await active_account_access_restriction(db, subject_uid)
    return _restriction_projection(restriction) if restriction else None


async def assert_http_account_access(
    db: AsyncSession,
    request: Request,
    subject_uid: UUID | str,
) -> None:
    if is_account_access_http_exempt(request):
        return
    restriction = await active_account_access_restriction(db, subject_uid)
    if restriction is None:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error_type": "account_access_restricted",
            "restriction": _restriction_projection(restriction),
        },
    )


async def revoke_account_sessions(db: AsyncSession, account: Account) -> None:
    now = datetime.utcnow()
    await db.execute(
        update(IdentitySession)
        .where(
            IdentitySession.account_uid == account.uid,
            IdentitySession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )

    device_subjects = [account.uid]
    if account.legacy_user_uid and account.legacy_user_uid != account.uid:
        device_subjects.append(account.legacy_user_uid)
    await db.execute(
        update(UserDevice)
        .where(
            UserDevice.user_uid.in_(device_subjects),
            UserDevice.is_active.is_(True),
        )
        .values(is_active=False)
    )


async def disconnect_account_realtime(account_uid: UUID, explanation: str) -> None:
    try:
        await realtime_service.publish(
            {
                "kind": "account_control",
                "action": "disconnect_account",
                "user_uid": str(account_uid),
                "reason": explanation[:120] or "Account access restricted",
            }
        )
    except RealtimeUnavailable:
        # The durable restriction and revoked sessions remain authoritative.
        # Existing sockets also re-check account.access on every client frame.
        logger.warning(
            "Realtime unavailable while disconnecting restricted account=%s",
            account_uid,
        )
    except Exception:
        logger.exception(
            "Unexpected realtime disconnect failure for restricted account=%s",
            account_uid,
        )
