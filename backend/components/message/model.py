from typing import List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, desc, asc
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, relationship, joinedload
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
    def format_message(msg):
        """
        Форматирует объект Message в словарь для отправки клиенту.

        :param msg: Объект Message
        :return: Словарь с данными сообщения
        """
        return {
            "type": "message",
            "uid": str(msg.uid),
            "content": msg.text,
            "content_type": msg.content_type,
            "sender": {
                "uid": str(msg.author_uid),
                "name": msg.author.username if msg.author else "Unknown",  # Имя пользователя
                "avatar": msg.author.avatar if msg.author else None  # Аватар пользователя
            },
            "room_uid": str(msg.room_uid),
            "created_at": msg.created_at.isoformat()
        }

    @staticmethod
    def create_message(db_session: Session, message_data: dict):
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

            # Возвращаем сообщение в нужном формате
            return Message.format_message(new_message)
        except Exception as e:
            # Логируем ошибку и откатываем транзакцию
            logger.error(f"Error creating message: {e}")
            db_session.rollback()
            raise

    @staticmethod
    def get_last_messages(db_session: Session, room_uid: UUID, limit: int = 5) -> List["Message"]:
        """
        Возвращает последние сообщения для указанной комнаты.

        :param db_session: SQLAlchemy сессия
        :param room_uid: UUID комнаты
        :param limit: Количество сообщений для возврата
        :return: Список объектов Message
        """
        try:
            # Выполняем запрос к базе данных
            last_messages = (
                db_session.query(Message)
                .options(joinedload(Message.author))  # Загружаем связанные данные о пользователе
                .filter(Message.room_uid == str(room_uid))
                .order_by(desc(Message.created_at))  # Сортировка по времени создания (по убыванию)
                .limit(limit)
                .all()
            )
            return last_messages
        except Exception as e:
            # Логируем ошибку
            logger.error(f"Error fetching last messages: {e}")
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