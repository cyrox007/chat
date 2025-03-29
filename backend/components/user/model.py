# Стандартные библиотеки Python
from enum import Enum
import re
from typing import List
from uuid import uuid4

# Внешние зависимости
from sqlalchemy import Column, Index, Integer, String, DateTime, Boolean, ForeignKey, Interval, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, relationship
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# Локальные модули
from database import Database
from components.room.model import Room
from components.message.model import Message
from components.user.exceptions import UserValidationError
from utils.logger import setup_logger  # Централизованная утилита логирования

# Создаем логгер
logger = setup_logger(__name__)


# Enums
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


# Модель User
class User(Database.Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    uid = Column(UUID(as_uuid=True), default=uuid4, unique=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20), unique=True, index=True)  # Номер телефона
    first_name = Column(String(50))  # Имя
    last_name = Column(String(50))  # Фамилия
    hashed_password = Column(String(255))
    avatar = Column(String(255))
    global_role = Column(String(50), default="user")  # Роль (admin, moderator, user)
    rating = Column(Integer, default=0)  # Рейтинг
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Подтверждение email
    deleted_at = Column(DateTime, nullable=True)  # Мягкое удаление
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    bio = Column(String(500), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(SQLEnum('male', 'female', 'other', name='gender'), nullable=True)
    career = Column(String(100), nullable=True)
    education = Column(String(100), nullable=True)
    marital_status = Column(String(50), nullable=True)
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
        foreign_keys="[Penalty.user_uid]"
    )
    issued_penalties = relationship(
        "Penalty",
        back_populates="issuer",
        foreign_keys="[Penalty.issuer_uid]"
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
        first_name: str = None,
        last_name: str = None,
        avatar: str = None  
    ):
        """
        Создает нового пользователя в БД.
        :param db_session: Сессия БД
        :param username: Логин пользователя
        :param email: Почта пользователя
        :param phone: Номер телефона
        :param password: Хэшированный пароль
        :param gender: Пол пользователя
        :param first_name: Имя пользователя
        :param last_name: Фамилия пользователя
        :param avatar: Ссылка на аватар (необязательно)
        :return: Созданный пользователь или None при ошибке
        """
        logger.info(f"Начало создания пользователя: {username}")
        try:
            # Валидация email
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                logger.error(f"Неверный формат email: {email}")
                raise UserValidationError("Invalid email format")

            # Валидация телефона
            phone_pattern = r'^\+?(375\d{9}|7\d{10})$'
            cleaned_phone = re.sub(r'[^\d+]', '', phone)  # Очистка от лишних символов
            if not re.fullmatch(phone_pattern, cleaned_phone):
                logger.error(f"Неверный формат номера телефона: {phone}")
                raise UserValidationError("Invalid phone number format")

            # Проверка уникальности
            existing_user = db_session.query(cls).filter(
                (cls.username == username) |
                (cls.email == email) |
                (cls.phone == phone)
            ).first()
            if existing_user:
                if existing_user.username == username:
                    logger.warning(f"Пользователь с таким username уже существует: {username}")
                    raise UserValidationError("Username already exists")
                if existing_user.email == email:
                    logger.warning(f"Пользователь с такой почтой уже существует: {email}")
                    raise UserValidationError("Email already exists")
                if existing_user.phone == phone:
                    logger.warning(f"Пользователь с таким телефоном уже существует: {phone}")
                    raise UserValidationError("Phone already exists")

            # Выбор аватара по умолчанию
            if not avatar:
                if gender == Gender.FEMALE:
                    avatar = "/static/default_female.webp"
                else:
                    avatar = "/static/default_male.webp"

            # Создание пользователя
            new_user = cls(
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
            logger.info(f"Пользователь успешно создан: {username}")
            return new_user

        except IntegrityError:
            logger.exception(f"Ошибка целостности данных при создании пользователя: {username}")
            db_session.rollback()
            return None

    @classmethod
    def get_user_by_credentials(cls, db_session: Session, identifier: str):
        """
        Получает пользователя по логину, email или телефону.
        :param db_session: Сессия БД
        :param identifier: Логин, email или телефон
        :return: Объект пользователя или None
        """
        logger.info(f"Поиск пользователя по идентификатору: {identifier}")
        normalized = identifier.strip()

        # Поиск по email
        if re.fullmatch(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", normalized):
            user = db_session.query(cls).filter(cls.email.ilike(normalized)).first()
            if user:
                logger.info(f"Пользователь найден по email: {normalized}")
            return user

        # Поиск по телефону
        phone_digits = re.sub(r'[^\d]', '', normalized)
        possible_phones = []
        if len(phone_digits) == 11 and phone_digits.startswith('7'):
            possible_phones.append(f"+{phone_digits}")  # +79191234567
            possible_phones.append(phone_digits)        # 79191234567
        elif len(phone_digits) == 12 and phone_digits.startswith('375'):
            possible_phones.append(f"+{phone_digits}")  # +375291234567
            possible_phones.append(phone_digits)        # 375291234567

        if possible_phones:
            user = db_session.query(cls).filter(cls.phone.in_(possible_phones)).first()
            if user:
                logger.info(f"Пользователь найден по телефону: {normalized}")
            return user

        # Поиск по username
        user = db_session.query(cls).filter(cls.username.ilike(normalized)).first()
        if user:
            logger.info(f"Пользователь найден по username: {normalized}")
        return user

    @classmethod
    def get_users_by_uids(cls, db_session: Session, user_uids: List[str]):
        """
        Получение данных о пользователях по их user_uid.
        :param db_session: SQLAlchemy сессия
        :param user_uids: Список UUID пользователей
        :return: Список словарей с данными пользователей
        """
        logger.info(f"Получение данных о пользователях по UID: {user_uids}")
        if not user_uids:
            logger.warning("Получен пустой список user_uids")
            return []

        users = db_session.query(cls).filter(cls.uid.in_(user_uids)).all()
        users_data = [
            {
                "uid": str(user.uid),
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "avatar": user.avatar,
                "global_role": user.global_role,
                "rating": user.rating,
                "city": user.city,
                "country": user.country,
                "bio": user.bio,
                "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
                "gender": user.gender,
                "career": user.career,
                "education": user.education,
                "marital_status": user.marital_status,
                "last_online": user.last_online.isoformat() if user.last_online else None,
            }
            for user in users
        ]
        logger.info(f"Данные о пользователях успешно получены: {len(users_data)} пользователей")
        return users_data

    @classmethod
    def get_user_by_uid(cls, db_session: Session, uid: str):
        """
        Получает пользователя по его UID.
        :param db_session: Сессия БД
        :param uid: UID пользователя
        :return: Объект пользователя или None
        """
        logger.info(f"Поиск пользователя по UID: {uid}")
        user = db_session.query(cls).filter(cls.uid == uid).first()
        if user:
            logger.info(f"Пользователь найден: {user.username}")
        else:
            logger.warning(f"Пользователь с UID {uid} не найден")
        return user


# Модель Penalty
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
        foreign_keys=[user_uid]
    )
    issuer = relationship(
        "User",
        back_populates="issued_penalties",
        foreign_keys=[issuer_uid]
    )


# Модель UserRelationship
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