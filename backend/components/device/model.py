from sqlalchemy import UUID, Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Session, relationship
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import uuid

from database import Database
from utils.logger import setup_logger

logger = setup_logger(__name__)

class UserDevice(Database.Base):
    __tablename__ = 'user_devices'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_uid = Column(UUID(as_uuid=True), ForeignKey('users.uid'), nullable=False)  # Связь с пользователем
    token = Column(String, unique=True, nullable=False)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=False)
    device_info = Column(String, nullable=True)  # Дополнительная информация об устройстве
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    # Связь с моделью User
    user = relationship("User", back_populates="refresh_tokens")

    @classmethod
    def create(cls, db_session: Session, user_uid, token, ip_address, user_agent, device_info=None, expires_in_days=30):
        """
        Создает новую запись о токене устройства.
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
            db_session.commit()
            logger.info(f"Запись успешно создана: {new_record}")
            return new_record
        except Exception as e:
            logger.error(f"Ошибка при создании записи: {e}")
            db_session.rollback()
            raise

    @classmethod
    def update_token(cls, db_session: Session, old_token, new_token, ip_address, user_agent, expires_in_days=30):
        """
        Обновляет существующий токен устройства.
        """
        logger.info(f"Начало обновления токена: старый токен={old_token}, новый токен={new_token}")
        try:
            # Используем SELECT FOR UPDATE для блокировки записи
            record = db_session.query(cls).filter_by(token=old_token, is_active=True).with_for_update().first()
            if not record:
                logger.warning(f"Запись с токеном {old_token} не найдена или неактивна.")
                raise ValueError("Invalid or inactive token")

            logger.debug(f"Текущая запись перед обновлением: {record}")

            # Обновление данных
            record.token = new_token
            record.ip_address = ip_address
            record.user_agent = user_agent
            record.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            db_session.commit()

            logger.info(f"Токен успешно обновлен: {record}")
            return record
        except IntegrityError as e:
            db_session.rollback()
            logger.error(f"Конфликт при обновлении токена: {e}")
            raise ValueError("Token update conflict")
        except Exception as e:
            db_session.rollback()
            logger.error(f"Ошибка при обновлении токена: {e}")
            raise

    @classmethod
    def deactivate_token(cls, db_session: Session, token):
        """
        Деактивирует токен (например, при выходе пользователя).
        """
        logger.info(f"Начало деактивации токена: {token}")
        try:
            record = db_session.query(cls).filter_by(token=token, is_active=True).first()
            if not record:
                logger.warning(f"Запись с токеном {token} не найдена или уже деактивирована.")
                raise ValueError("Invalid or inactive token")

            logger.debug(f"Текущая запись перед деактивацией: {record}")

            # Деактивация токена
            record.is_active = False
            db_session.commit()

            logger.info(f"Токен успешно деактивирован: {record}")
            return record
        except Exception as e:
            logger.error(f"Ошибка при деактивации токена: {e}")
            db_session.rollback()
            raise