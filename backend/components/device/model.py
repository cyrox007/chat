from sqlalchemy import UUID, Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Session, relationship
from datetime import datetime, timedelta
import uuid

from database import Database

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
        return new_record

    @classmethod
    def update_token(cls, db_session: Session, old_token, new_token, ip_address, user_agent, expires_in_days=30):
        """
        Обновляет существующий токен устройства.
        """
        record = db_session.query(cls).filter_by(token=old_token, is_active=True).first()
        if not record:
            raise ValueError("Invalid or inactive token")

        record.token = new_token
        record.ip_address = ip_address
        record.user_agent = user_agent
        record.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        db_session.commit()
        return record

    @classmethod
    def deactivate_token(cls, db_session: Session, token):
        """
        Деактивирует токен (например, при выходе пользователя).
        """
        record = db_session.query(cls).filter_by(token=token, is_active=True).first()
        if not record:
            raise ValueError("Invalid or inactive token")

        record.is_active = False
        db_session.commit()
        return record
    