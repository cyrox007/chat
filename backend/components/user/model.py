from enum import Enum

from sqlalchemy import Column, Index, Integer, String, DateTime, Boolean, ForeignKey, Interval, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, relationship
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from uuid import uuid4

from database import Database

from components.room.model import Room
from components.message.model import Message

from components.user.exceptions import UserValidationError

import re

class PenaltyType(str, Enum):
    BAN = "ban"
    MUTE = "mute"
    WARNING = "warning"

class RelationshipType(str, Enum):
    SPOUSE = "spouse" 
    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    FRIEND = "friend"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class User(Database.Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    uid = Column(UUID(as_uuid=True), default=uuid4, unique=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20), unique=True, index=True)  # Добавлен номер телефона
    first_name = Column(String(50))  # Добавлено имя
    last_name = Column(String(50))  # Добавлена фамилия
    hashed_password = Column(String(255))
    avatar = Column(String(255))
    global_role = Column(String(50), default="user")  # admin, moderator, user
    rating = Column(Integer, default=0)  # Добавлен рейтинг
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Подтверждение email
    deleted_at = Column(DateTime, nullable=True)  # Мягкое удаление

    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    bio = Column(String(500), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(
        SQLEnum('male', 'female', 'other', name='gender'), 
        nullable=True
    )
    career = Column(String(100), nullable=True)
    education = Column(String(100), nullable=True)
    marital_status = Column(String(50), nullable=True)
    #total_online_time = Column(Interval, default=datetime.timedelta())  # Время в сети
    last_online = Column(DateTime)

    __table_args__ = (
        Index("ix_user_username", username),
        Index("ix_user_email", email),
        Index("ix_user_phone", phone),
        Index("ix_user_gender", gender),
    )

    # Отношения
    owned_rooms = relationship("Room", back_populates="owner")
    memberships = relationship("RoomMember", back_populates="user")
    messages = relationship("Message", foreign_keys="[Message.author_uid]", back_populates="author")
    sent_private_messages = relationship("PrivateMessage", foreign_keys="[PrivateMessage.sender_uid]", back_populates="sender")
    received_private_messages = relationship("PrivateMessage", foreign_keys="[PrivateMessage.receiver_uid]", back_populates="receiver")
    penalties = relationship(
        "Penalty",
        back_populates="user",
        foreign_keys="[Penalty.user_uid]"  # Указываем FK явно
    )
    issued_penalties = relationship(
        "Penalty",
        back_populates="issuer",
        foreign_keys="[Penalty.issuer_uid]"  # Указываем FK явно
    )
    relationships = relationship(
        "UserRelationship",
        foreign_keys="[UserRelationship.from_user_uid]",
        back_populates="from_user"
    )
    related_to = relationship(
        "UserRelationship",
        foreign_keys="[UserRelationship.to_user_uid]",
        back_populates="to_user"
    )
    refresh_tokens = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"User {self.uid}"
    

    @classmethod
    def create_user(
        cls,
        db_session: Session,
        username: str,
        email: str,
        phone: str,
        password: str,
        gender: Gender = None,
        first_name: str = None,  # Добавлено
        last_name: str = None    # Добавлено
    ):
        """
        Создает нового пользователя в БД.
        :param db_session: Сессия БД
        :param username: Логин пользователя
        :param email: Почта пользователя
        :param phone: Номер телефона
        :param password: Хэшированный пароль
        :return: Созданный пользователь или None при ошибке
        """
        # 1. Валидация email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise UserValidationError("Invalid email format")
        
        # 2. Валидация телефона (пример для Беларуси/России)
        phone_pattern = r'^\+?(375\d{9}|7\d{10})$'
        cleaned_phone = re.sub(r'[^\d+]', '', phone)  # Очистка от лишних символов
        
        if not re.fullmatch(phone_pattern, cleaned_phone):
            raise UserValidationError("Invalid phone number format")
        
        # 3. Проверка уникальности
        existing_user = db_session.query(User).filter(
            (User.username == username) |
            (User.email == email) |
            (User.phone == phone)
        ).first()

        if existing_user:
            if existing_user.username == username:
                raise UserValidationError("Username already exists")
            if existing_user.email == email:
                raise UserValidationError("Email already exists")
            if existing_user.phone == phone:
                raise UserValidationError("Phone already exists")
            
        # 4. Определение аватара
        avatar = "default_female.webp" if gender == Gender.FEMALE else "default_male.webp"

        try:
            new_user = User(
                username=username,
                email=email,
                phone=phone,
                hashed_password=password,
                avatar=avatar,
                gender=gender,
                first_name=first_name,
                last_name=last_name
            )
            db_session.add(new_user)
            db_session.commit()
            return new_user
        except IntegrityError:
            db_session.rollback()
            return None

    @classmethod
    def get_user_by_credentials(cls, db_session: Session, identifier: str):
        normalized = identifier.strip()
        
        # 1. Проверка email
        if re.fullmatch(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", normalized):
            return db_session.query(cls).filter(
                cls.email.ilike(normalized)
            ).first()

        # 2. Проверка телефона
        # Очистка от всех символов кроме цифр
        phone_digits = re.sub(r'[^\d]', '', normalized)
        
        # Генерация возможных вариантов
        possible_phones = []
        if len(phone_digits) == 11 and phone_digits.startswith('7'):
            possible_phones.append(f"+{phone_digits}")  # +79191234567
            possible_phones.append(phone_digits)        # 79191234567
        elif len(phone_digits) == 12 and phone_digits.startswith('375'):
            possible_phones.append(f"+{phone_digits}")  # +375291234567
            possible_phones.append(phone_digits)        # 375291234567

        if possible_phones:
            return db_session.query(cls).filter(
                cls.phone.in_(possible_phones)
            ).first()

        # 3. Поиск по username
        return db_session.query(cls).filter(
            cls.username.ilike(normalized)
        ).first()
        
class Penalty(Database.Base):
    __tablename__ = "penalties"
    
    id = Column(Integer, primary_key=True)
    user_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    penalty_type = Column(SQLEnum(PenaltyType))
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    issuer_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    reason = Column(String(255))
    
    user = relationship(
        "User",
        back_populates="penalties",
        foreign_keys=[user_uid]  # Для user_uid
    )
    issuer = relationship(
        "User",
        back_populates="issued_penalties",
        foreign_keys=[issuer_uid]  # Для issuer_uid
    )

class UserRelationship(Database.Base):
    __tablename__ = "user_relationships"
    __table_args__ = (
        UniqueConstraint('from_user_uid', 'to_user_uid', name='unique_relationship'),
    )
    
    id = Column(Integer, primary_key=True)
    from_user_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    to_user_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    relation_type = Column(SQLEnum(RelationshipType))
    since = Column(DateTime, default=datetime.utcnow)
    
    from_user = relationship("User", back_populates="relationships", foreign_keys=[from_user_uid])
    to_user = relationship("User", back_populates="related_to", foreign_keys=[to_user_uid])