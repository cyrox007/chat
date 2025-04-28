from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import InterfaceError, IntegrityError
from sqlalchemy.orm import relationship

from database import Database
from utils.logger import setup_logger

logger = setup_logger(__name__)

class UserDevice(Database.Base):
    __tablename__ = 'user_devices'

    # Fields
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_uid = Column(PG_UUID(as_uuid=True), ForeignKey('users.uid'), nullable=False)
    token = Column(String, unique=True, nullable=False)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=False)
    device_info = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    # Constants
    DEFAULT_EXPIRATION_DAYS = 30

    # Utility methods
    @staticmethod
    def _log_token(token: str) -> str:
        """Логирование части токена для безопасности."""
        return f"{token[:10]}..." if token else "empty_token"

    @classmethod
    async def _execute_scalar(cls, db_session: AsyncSession, query) -> Optional['UserDevice']:
        """Универсальный метод выполнения запроса с возвратом одного результата."""
        result = await db_session.execute(query)
        return result.scalar_one_or_none()

    # CRUD Operations
    @classmethod
    async def create(
        cls,
        db_session: AsyncSession,
        user_uid: UUID,
        token: str,
        ip_address: str,
        user_agent: str,
        device_info: Optional[dict] = None,
        expires_in_days: int = DEFAULT_EXPIRATION_DAYS
    ) -> Optional['UserDevice']:
        """Создает новую запись устройства пользователя."""
        logger.info(f"Создание устройства для пользователя {user_uid}")

        try:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            device = cls(
                user_uid=user_uid,
                token=token,
                ip_address=ip_address,
                user_agent=user_agent,
                device_info=device_info,
                expires_at=expires_at
            )

            db_session.add(device)
            await db_session.commit()
            logger.info(f"Устройство создано: {device.id}")
            return device

        except IntegrityError as e:
            logger.error(f"Ошибка уникальности токена: {cls._log_token(token)}")
            await db_session.rollback()
            raise ValueError("Токен уже существует") from e
        except Exception as e:
            logger.error(f"Ошибка создания устройства: {str(e)}")
            await db_session.rollback()
            raise

    @classmethod
    async def update_token(
        cls,
        db_session: AsyncSession,
        old_token: str,
        new_token: str,
        ip_address: str,
        user_agent: str,
        expires_in_days: int = DEFAULT_EXPIRATION_DAYS
    ) -> Optional['UserDevice']:
        """Атомарное обновление токена устройства."""
        logger.info(f"Обновление токена {cls._log_token(old_token)} -> {cls._log_token(new_token)}")

        try:
            async with db_session.begin():
                # Получаем и блокируем устройство
                device = await cls._get_and_lock_device(db_session, old_token)
                if not device:
                    return None

                # Проверяем новый токен
                if await cls._is_token_used(db_session, new_token):
                    return None

                # Обновляем данные
                return cls._update_device(
                    device,
                    new_token,
                    ip_address,
                    user_agent,
                    expires_in_days
                )

        except InterfaceError as e:
            logger.error(f"Ошибка соединения: {str(e)}")
            raise ValueError("Database connection error") from e
        except Exception as e:
            logger.error(f"Ошибка обновления: {str(e)}")
            raise

    @classmethod
    async def deactivate_token(
        cls,
        db_session: AsyncSession,
        token: str
    ) -> Optional['UserDevice']:
        """Деактивирует устройство по токену."""
        logger.info(f"Деактивация устройства {cls._log_token(token)}")

        device = await cls.find_active_by_token(db_session, token)
        if not device:
            logger.warning("Устройство не найдено или уже деактивировано")
            return None

        try:
            device.is_active = False
            await db_session.commit()
            logger.info(f"Устройство {device.id} деактивировано")
            return device
        except Exception as e:
            logger.error(f"Ошибка деактивации: {str(e)}")
            await db_session.rollback()
            raise

    # Query methods
    @classmethod
    async def find_active_by_token(
        cls,
        db_session: AsyncSession,
        token: str
    ) -> Optional['UserDevice']:
        """Находит активное устройство по токену."""
        query = select(cls).where(
            and_(
                cls.token == token,
                cls.is_active == True,
                cls.expires_at > datetime.utcnow()
            )
        )
        return await cls._execute_scalar(db_session, query)

    @classmethod
    async def get_user_devices(
        cls,
        db_session: AsyncSession,
        user_uid: UUID
    ) -> List['UserDevice']:
        """Возвращает все активные устройства пользователя."""
        query = select(cls).where(
            and_(
                cls.user_uid == user_uid,
                cls.is_active == True,
                cls.expires_at > datetime.utcnow()
            )
        ).order_by(cls.created_at.desc())

        result = await db_session.execute(query)
        return result.scalars().all()

    # Private helpers
    @classmethod
    async def _get_and_lock_device(
        cls,
        db_session: AsyncSession,
        token: str
    ) -> Optional['UserDevice']:
        """Находит и блокирует устройство для обновления."""
        query = select(cls).where(
            and_(
                cls.token == token,
                cls.is_active == True
            )
        ).with_for_update().limit(1)

        device = await cls._execute_scalar(db_session, query)
        if not device:
            logger.warning(f"Устройство не найдено: {cls._log_token(token)}")
        return device

    @classmethod
    async def _is_token_used(
        cls,
        db_session: AsyncSession,
        token: str
    ) -> bool:
        """Проверяет, используется ли токен другим устройством."""
        query = select(cls.id).where(
            and_(
                cls.token == token,
                cls.is_active == True
            )
        ).limit(1)

        result = await cls._execute_scalar(db_session, query)
        if result:
            logger.warning(f"Токен уже используется: {cls._log_token(token)}")
        return bool(result)

    @classmethod
    def _update_device(
        cls,
        device: 'UserDevice',
        new_token: str,
        ip_address: str,
        user_agent: str,
        expires_in_days: int
    ) -> 'UserDevice':
        """Обновляет данные устройства."""
        device.token = new_token
        device.ip_address = ip_address
        device.user_agent = user_agent
        device.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        logger.info(f"Устройство обновлено: {device.id}")
        return device