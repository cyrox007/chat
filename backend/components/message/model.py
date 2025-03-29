from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from database import Database
from components.room.model import Room

# Configure the logger
import logging
logger = logging.getLogger(__name__)

class Message(Database.Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(UUID(as_uuid=True), default=uuid4, unique=True, index=True)
    content_type = Column(String(50), nullable=False)  # text, image, video, audio, document, voice, sticker
    text = Column(String(1000))  # Текст (опционально)
    media_metadata = Column(JSON)  # Метаданные для медиа
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь с комнатой
    room_uid = Column(UUID(as_uuid=True), ForeignKey("rooms.uid"))
    room = relationship("Room", back_populates="messages")

    # Связь с автором
    author_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    author = relationship("User", foreign_keys=[author_uid], back_populates="messages")

    # Упоминание пользователя (опционально)
    mention_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    mention = relationship("User", foreign_keys=[mention_uid])

    def __repr__(self):
        return f"<Message(uid={self.uid}, type={self.content_type}, room={self.room_uid})>"
    
    @staticmethod
    def create_message(db_session, message_data: dict):
        """
        Создает новое сообщение и сохраняет его в базу данных.

        :param db_session: SQLAlchemy сессия
        :param message_data: Словарь с данными сообщения
        :return: Созданный объект Message
        """
        try:
            # Создаем новый объект Message
            new_message = Message(
                content_type=message_data.get("content_type", "text"),
                text=message_data.get("content"),
                room_uid=message_data.get("room_uid"),
                author_uid=message_data.get("sender_uid"),
                created_at=datetime.utcnow()
            )

            # Добавляем сообщение в сессию и фиксируем изменения
            db_session.add(new_message)
            db_session.commit()
            db_session.refresh(new_message)

            return new_message
        except Exception as e:
            # Логируем ошибку и откатываем транзакцию
            logger.error(f"Error creating message: {e}")
            db_session.rollback()
            raise

class PrivateMessage(Database.Base):
    __tablename__ = "private_messages"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(UUID(as_uuid=True), default=uuid4, unique=True, index=True)
    content_type = Column(String(50), nullable=False)  # text, image, video, audio, document, voice, sticker
    text = Column(String(1000))  # Текст (опционально)
    media_metadata = Column(JSON)  # Метаданные для медиа
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)  # Флаг прочтения

    # Связь с отправителем
    sender_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    sender = relationship("User", foreign_keys=[sender_uid], back_populates="sent_private_messages")

    # Связь с получателем
    receiver_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    receiver = relationship("User", foreign_keys=[receiver_uid], back_populates="received_private_messages")

    def __repr__(self):
        return f"<PrivateMessage(uid={self.uid}, sender={self.sender_uid}, receiver={self.receiver_uid})>"