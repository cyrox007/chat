from datetime import datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from components.device.model import UserDevice
from components.identity.model import (
    Account,
    AccountRole,
    Credential,
    IdentitySession,
    Persona,
    PlatformRole,
    PrivacySettings,
)
from components.identity.schemas import PersonaUpdateRequest, PrivacyUpdateRequest, RegisterRequest
from components.user.model import User
from services.auth_service import generate_tokens
from settings import config
from utils.password import hash_password, verify_password
from utils.user_agents import parse_user_agent
from utils.jwt import validate_refresh_token


def _token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _client_metadata(request: Request) -> tuple[str, str, dict]:
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    return ip_address, user_agent, parse_user_agent(user_agent)


async def _role_name(db: AsyncSession, account_uid: UUID) -> str:
    result = await db.execute(
        select(PlatformRole.name)
        .join(AccountRole, AccountRole.role_id == PlatformRole.id)
        .where(AccountRole.account_uid == account_uid)
        .order_by(PlatformRole.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none() or "user"


async def _primary_persona(db: AsyncSession, account_uid: UUID) -> Persona | None:
    result = await db.execute(
        select(Persona)
        .where(Persona.account_uid == account_uid, Persona.is_primary.is_(True))
        .order_by(Persona.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def build_identity_projection(db: AsyncSession, account: Account) -> dict:
    persona = await _primary_persona(db, account.uid)
    role = await _role_name(db, account.uid)
    privacy = None
    if persona:
        privacy = await db.get(PrivacySettings, persona.uid)

    persona_data = None
    if persona:
        persona_data = {
            "uid": str(persona.uid),
            "handle": persona.handle,
            "display_name": persona.display_name,
            "avatar": persona.avatar,
            "bio": persona.bio,
            "city": persona.city,
            "country": persona.country,
            "social_intent": persona.social_intent,
            "is_primary": persona.is_primary,
        }

    privacy_data = None
    if privacy:
        privacy_data = {
            "profile_visibility": privacy.profile_visibility,
            "dm_policy": privacy.dm_policy,
            "show_last_seen": privacy.show_last_seen,
            "show_age": privacy.show_age,
            "show_location": privacy.show_location,
        }

    # `user` is a compatibility projection for the current Vuex store. It will
    # disappear when the remaining legacy UI switches to account/persona.
    compatibility_user = None
    if persona:
        compatibility_user = {
            "uid": str(account.uid),
            "username": persona.handle,
            "display_name": persona.display_name,
            "avatar": persona.avatar,
            "bio": persona.bio,
            "city": persona.city,
            "country": persona.country,
            "global_role": role,
            "trust_level": account.trust_level,
            "social_intent": persona.social_intent,
            "persona_uid": str(persona.uid),
        }

    return {
        "account": {
            "uid": str(account.uid),
            "status": account.status,
            "trust_level": account.trust_level,
            "created_at": account.created_at.isoformat() if account.created_at else None,
        },
        "persona": persona_data,
        "privacy": privacy_data,
        "role": role,
        "user": compatibility_user,
    }


async def _issue_session(db: AsyncSession, account: Account, request: Request) -> dict:
    tokens = generate_tokens(str(account.uid))
    refresh_hash = _token_hash(tokens["refresh"])
    ip_address, user_agent, device_info = _client_metadata(request)
    expires_at = datetime.utcnow() + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS)

    db.add(
        IdentitySession(
            account_uid=account.uid,
            refresh_token_hash=refresh_hash,
            device_label=device_info.get("device") or device_info.get("device_type"),
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
        )
    )

    # Compatibility for the legacy /refresh and /logout paths while the SPA is
    # migrated. New identity code treats IdentitySession as authoritative.
    db.add(
        UserDevice(
            id=str(uuid4()),
            user_uid=account.uid,
            token=tokens["refresh"],
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
            expires_at=expires_at,
            is_active=True,
        )
    )
    return tokens


async def register_account(db: AsyncSession, payload: RegisterRequest, request: Request) -> tuple[Account, dict]:
    handle = payload.handle.strip()
    normalized_handle = handle.casefold()

    existing_handle = await db.execute(
        select(Persona.uid).where(func.lower(Persona.handle) == normalized_handle).limit(1)
    )
    if existing_handle.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_type": "handle_taken", "field": "handle"},
        )

    email = str(payload.email).strip().casefold() if payload.email else None
    if email:
        existing_email = await db.execute(
            select(Credential.uid).where(
                Credential.kind == "email",
                Credential.value_normalized == email,
            ).limit(1)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_type": "email_taken", "field": "email"},
            )

    account_uid = uuid4()
    password_hash = hash_password(payload.password)
    display_name = payload.display_name or handle

    legacy_user = User(
        uid=account_uid,
        username=handle,
        email=email,
        phone=None,
        hashed_password=password_hash,
        avatar="/static/default_male.webp",
        global_role="user",
        rating=0,
        is_active=True,
        is_verified=False,
        bio=payload.bio,
    )
    db.add(legacy_user)
    await db.flush()

    account = Account(
        uid=account_uid,
        legacy_user_uid=account_uid,
        status="active",
        trust_level="new",
    )
    persona = Persona(
        account_uid=account_uid,
        handle=handle,
        display_name=display_name,
        avatar=legacy_user.avatar,
        bio=payload.bio,
        social_intent=payload.social_intent,
        is_primary=True,
    )
    db.add(account)
    await db.flush()
    db.add(persona)
    await db.flush()

    db.add(
        Credential(
            account_uid=account_uid,
            kind="password",
            secret_hash=password_hash,
            is_primary=True,
        )
    )
    if email:
        db.add(
            Credential(
                account_uid=account_uid,
                kind="email",
                value_normalized=email,
                is_primary=True,
            )
        )

    db.add(PrivacySettings(persona_uid=persona.uid))
    db.add(AccountRole(account_uid=account_uid, role_id=1))

    tokens = await _issue_session(db, account, request)
    await db.commit()
    await db.refresh(account)
    return account, tokens


async def authenticate_account(db: AsyncSession, identifier: str, password: str, request: Request) -> tuple[Account, dict]:
    normalized = identifier.strip().casefold()

    persona_result = await db.execute(
        select(Persona).where(func.lower(Persona.handle) == normalized).limit(1)
    )
    persona = persona_result.scalar_one_or_none()
    account_uid = persona.account_uid if persona else None

    if account_uid is None:
        credential_result = await db.execute(
            select(Credential).where(
                Credential.kind.in_(["email", "phone"]),
                Credential.value_normalized == normalized,
            ).limit(1)
        )
        identifier_credential = credential_result.scalar_one_or_none()
        account_uid = identifier_credential.account_uid if identifier_credential else None

    if account_uid is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error_type": "invalid_credentials"})

    account = await db.get(Account, account_uid)
    if not account or account.status != "active" or account.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error_type": "account_unavailable"})

    password_result = await db.execute(
        select(Credential).where(
            Credential.account_uid == account.uid,
            Credential.kind == "password",
        ).limit(1)
    )
    password_credential = password_result.scalar_one_or_none()
    if not password_credential or not password_credential.secret_hash or not verify_password(password, password_credential.secret_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error_type": "invalid_credentials"})

    tokens = await _issue_session(db, account, request)
    await db.commit()
    return account, tokens


async def rotate_session(db: AsyncSession, refresh_token: str, request: Request) -> tuple[Account, dict]:
    payload = validate_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error_type": "invalid_refresh_token"})

    token_hash = _token_hash(refresh_token)
    result = await db.execute(
        select(IdentitySession).where(
            IdentitySession.refresh_token_hash == token_hash,
            IdentitySession.revoked_at.is_(None),
            IdentitySession.expires_at > datetime.utcnow(),
        ).with_for_update().limit(1)
    )
    identity_session = result.scalar_one_or_none()
    if not identity_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error_type": "session_not_found"})

    account = await db.get(Account, identity_session.account_uid)
    if not account or account.status != "active" or str(account.uid) != payload.get("user_uid"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error_type": "account_unavailable"})

    tokens = generate_tokens(str(account.uid))
    identity_session.refresh_token_hash = _token_hash(tokens["refresh"])
    identity_session.last_seen_at = datetime.utcnow()
    identity_session.expires_at = datetime.utcnow() + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS)

    legacy_device_result = await db.execute(
        select(UserDevice).where(UserDevice.token == refresh_token, UserDevice.is_active.is_(True)).limit(1)
    )
    legacy_device = legacy_device_result.scalar_one_or_none()
    if legacy_device:
        ip_address, user_agent, _ = _client_metadata(request)
        legacy_device.token = tokens["refresh"]
        legacy_device.ip_address = ip_address
        legacy_device.user_agent = user_agent
        legacy_device.expires_at = identity_session.expires_at

    await db.commit()
    return account, tokens


async def revoke_session(db: AsyncSession, refresh_token: str | None) -> None:
    if not refresh_token:
        return

    token_hash = _token_hash(refresh_token)
    result = await db.execute(
        select(IdentitySession).where(
            IdentitySession.refresh_token_hash == token_hash,
            IdentitySession.revoked_at.is_(None),
        ).limit(1)
    )
    identity_session = result.scalar_one_or_none()
    if identity_session:
        identity_session.revoked_at = datetime.utcnow()

    legacy_result = await db.execute(
        select(UserDevice).where(UserDevice.token == refresh_token, UserDevice.is_active.is_(True)).limit(1)
    )
    legacy_device = legacy_result.scalar_one_or_none()
    if legacy_device:
        legacy_device.is_active = False

    await db.commit()


async def get_account_by_uid(db: AsyncSession, account_uid: str) -> Account:
    try:
        uid = UUID(str(account_uid))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error_type": "invalid_subject"}) from exc

    account = await db.get(Account, uid)
    if not account or account.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_type": "account_not_found"})
    return account


async def update_primary_persona(db: AsyncSession, account: Account, payload: PersonaUpdateRequest) -> dict:
    persona = await _primary_persona(db, account.uid)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_type": "persona_not_found"})

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(persona, field, value)

    # Keep fields consumed by legacy room/messenger UI synchronized during migration.
    legacy_user = await db.get(User, account.legacy_user_uid) if account.legacy_user_uid else None
    if legacy_user:
        for field in ("avatar", "bio", "city", "country"):
            if field in updates:
                setattr(legacy_user, field, updates[field])

    await db.commit()
    await db.refresh(persona)
    return await build_identity_projection(db, account)


async def update_privacy(db: AsyncSession, account: Account, payload: PrivacyUpdateRequest) -> dict:
    persona = await _primary_persona(db, account.uid)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_type": "persona_not_found"})

    privacy = await db.get(PrivacySettings, persona.uid)
    if not privacy:
        privacy = PrivacySettings(persona_uid=persona.uid)
        db.add(privacy)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(privacy, field, value)

    await db.commit()
    return await build_identity_projection(db, account)
