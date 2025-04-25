from sqlalchemy import UUID, Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
from typing import Optional

from database import Database
from utils.logger import setup_logger

logger = setup_logger(__name__)

class UserDevice(Database.Base):
    __tablename__ = 'user_devices'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_uid = Column(UUID(as_uuid=True), ForeignKey('users.uid'), nullable=False)
    token = Column(String, unique=True, nullable=False)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=False)
    device_info = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    # Связь с моделью User
    user = relationship("User", back_populates="refresh_tokens")

    @classmethod
    async def create(cls, db_session: AsyncSession, user_uid, token, ip_address, user_agent, 
                    device_info: Optional[str] = None, expires_in_days: int = 30):
        """
        Асинхронно создает новую запись о токене устройства.
        """
        logger.info(f"Создание новой записи для токена устройства.")
        try:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            new_record = cls(
                user_uid=user_uid,
                token=token,
                ip_address=ip_address,
                user_agent=user_agent,
                device_info=device_info,
                expires_at=expires_at,
            )
            db_session.add(new_record)
            await db_session.commit()
            logger.info(f"Запись успешно создана: {new_record}")
            return new_record
        except Exception as e:
            logger.error(f"Ошибка при создании записи: {e}")
            await db_session.rollback()
            raise

    @classmethod
    async def update_token(cls, db_session: AsyncSession, old_token: str, new_token: str, 
                        ip_address: str, user_agent: str, expires_in_days: int = 30):
        """
        Асинхронно обновляет существующий токен устройства с улучшенной обработкой ошибок.
        """
        logger.info(f"Обновление токена: {old_token[:10]}... -> {new_token[:10]}...")
        
        try:
            # 1. Быстрая проверка существования нового токена без блокировки
            if (await db_session.execute(
                select(cls.id).where(cls.token == new_token, cls.is_active == True)
            )).scalar_one_or_none():
                logger.info("Новый токен уже существует")
                return None

            # 2. Короткая транзакция для обновления
            async with db_session.begin_nested():
                # Получаем запись с блокировкой (но быстро)
                record = (await db_session.execute(
                    select(cls)
                    .where(cls.token == old_token, cls.is_active == True)
                    .with_for_update(skip_locked=True)  # Пропускаем заблокированные
                    .limit(1)
                )).scalar_one_or_none()

                if not record:
                    logger.warning("Токен не найден или неактивен")
                    return None

                # Обновляем данные
                record.token = new_token
                record.ip_address = ip_address
                record.user_agent = user_agent
                record.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
                
            logger.info("Токен успешно обновлен")
            return record

        except Exception as e:
            logger.error(f"Ошибка обновления токена: {type(e).__name__}: {str(e)}")
            await db_session.rollback()
            raise ValueError("Token update failed") from e

    @classmethod
    async def deactivate_token(cls, db_session: AsyncSession, token: str):
        """
        Асинхронно деактивирует токен (например, при выходе пользователя).
        """
        logger.info(f"Начало деактивации токена: {token}")
        try:
            stmt = select(cls).where(
                cls.token == token,
                cls.is_active == True
            )
            result = await db_session.execute(stmt)
            record = result.scalar_one_or_none()
            
            if not record:
                logger.warning(f"Запись с токеном {token} не найдена или уже деактивирована.")
                raise ValueError("Invalid or inactive token")

            logger.debug(f"Текущая запись перед деактивацией: {record}")

            # Деактивация токена
            record.is_active = False
            await db_session.commit()

            logger.info(f"Токен успешно деактивирован: {record}")
            return record
        except Exception as e:
            logger.error(f"Ошибка при деактивации токена: {e}")
            await db_session.rollback()
            raise

    @classmethod
    async def find_active_by_token(cls, db_session: AsyncSession, token: str):
        """
        Асинхронно находит активную запись по токену.
        """
        try:
            stmt = select(cls).where(
                cls.token == token,
                cls.is_active == True,
                cls.expires_at > datetime.utcnow()
            )
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при поиске токена: {e}")
            raise

    @classmethod
    async def get_user_devices(cls, db_session: AsyncSession, user_uid: UUID):
        """
        Асинхронно получает все активные устройства пользователя.
        """
        try:
            stmt = select(cls).where(
                cls.user_uid == user_uid,
                cls.is_active == True,
                cls.expires_at > datetime.utcnow()
            ).order_by(cls.created_at.desc())
            
            result = await db_session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка при получении устройств пользователя: {e}")
            raise