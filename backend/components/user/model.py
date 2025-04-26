# Стандартные библиотеки Python
from enum import Enum
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Внешние зависимости
from fastapi import HTTPException, status
from sqlalchemy import Column, Index, Integer, String, DateTime, Boolean, ForeignKey, UniqueConstraint, and_, func, or_, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta, timezone

# Локальные модули
from database import Database
from components.user.exceptions import UserValidationError
from utils.logger import setup_logger

# Создаем логгер
logger = setup_logger(__name__)


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
    gender = Column(String(50), nullable=True)
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
    async def create_user(
        cls,
        db_session: AsyncSession,
        username: str,
        email: str,
        phone: str,
        password: str,
        gender: str = None,
        first_name: str = None,
        last_name: str = None,
        bio: str = None,
        date_of_birth: date = None,  # Ожидаем уже готовый datetime.date
        avatar: str = None  
    ) -> Optional["User"]:
        """
        Только создает пользователя в БД. 
        Все валидации должны быть выполнены в хэндлере!
        """
        logger.info(f"Создание пользователя: {username}")
        try:
            new_user = cls(
                username=username,
                email=email,
                phone=phone,
                hashed_password=password,
                avatar=avatar,
                gender=gender,
                first_name=first_name,
                last_name=last_name,
                bio=bio,
                date_of_birth=date_of_birth
            )
            db_session.add(new_user)
            await db_session.commit()
            await db_session.refresh(new_user)
            return new_user

        except IntegrityError as e:
            logger.error(f"Ошибка целостности: {e}")
            await db_session.rollback()
            raise UserValidationError("Пользователь с такими данными уже существует") from e
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}")
            await db_session.rollback()
            raise

    @classmethod
    async def get_user_by_credentials(cls, db_session: AsyncSession, identifier: str):
        normalized = identifier.strip()
        
        # Подготовка условий для телефона
        phone_digits = re.sub(r'[^\d]', '', normalized)
        possible_phones = []
        if len(phone_digits) == 11 and phone_digits.startswith('7'):
            possible_phones.extend([f"+{phone_digits}", phone_digits])
        elif len(phone_digits) == 12 and phone_digits.startswith('375'):
            possible_phones.extend([f"+{phone_digits}", phone_digits])

        # Формируем условия запроса
        conditions = [
            cls.email.ilike(normalized),
            cls.username.ilike(normalized)
        ]
        
        # Добавляем условие для телефона, только если есть варианты
        if possible_phones:
            conditions.append(cls.phone.in_(possible_phones))
        
        # Единый запрос
        query = select(cls).where(or_(*conditions))
        
        result = await db_session.execute(query)
        user = result.scalars().first()
        
        if user:
            logger.info(f"Пользователь найден: {normalized}")
        return user

    @classmethod
    async def get_users_by_uids(cls, db_session: AsyncSession, user_uids: List[str]):
        """
        Получение данных о пользователях по их user_uid.
        :param db_session: Асинхронная сессия SQLAlchemy
        :param user_uids: Список UUID пользователей
        :return: Список словарей с данными пользователей
        """
        logger.info(f"Получение данных о пользователях по UID: {user_uids}")
        if not user_uids:
            logger.warning("Получен пустой список user_uids")
            return []

        result = await db_session.execute(
            select(cls).where(cls.uid.in_(user_uids))
        )
        users = result.scalars().all()
        
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
    async def get_user_by_uid(cls, db_session: AsyncSession, uid: str):
        """
        Получает пользователя по его UID.
        :param db_session: Асинхронная сессия БД
        :param uid: UID пользователя
        :return: Объект пользователя или None
        """
        logger.info(f"Поиск пользователя по UID: {uid}")
        
        result = await db_session.execute(
            select(cls).where(cls.uid == uid)
        )
        user = result.scalars().first()
        
        if user:
            logger.info(f"Пользователь найден: {user.username}")
        else:
            logger.warning(f"Пользователь с UID {uid} не найден")
        return user

    @classmethod
    async def update_last_online(cls, db_session: AsyncSession, current_user_uid):
        """
        Обновляет время последней активности пользователя.
        
        :param db_session: Асинхронная SQLAlchemy сессия
        :param current_user_uid: UID пользователя
        :return: Объект пользователя или None в случае ошибки
        """
        try:
            # Находим пользователя по UID
            result = await db_session.execute(
                select(cls).where(cls.uid == current_user_uid)
            )
            user = result.scalars().first()
            
            if not user:
                logger.warning(f"Пользователь с UID {current_user_uid} не найден")
                return None

            # Обновляем поле last_online
            user.last_online = datetime.utcnow()
            db_session.add(user)
            await db_session.commit()
            await db_session.refresh(user)

            logger.info(f"Время последней активности обновлено для пользователя {current_user_uid}")
            return user

        except IntegrityError as e:
            logger.exception(f"Ошибка целостности данных при обновлении last_online: {e}")
            await db_session.rollback()
            return None

    @classmethod
    async def soft_delete(cls, db_session: AsyncSession, user_uid: str):
        """
        Мягкое удаление пользователя (обновление поля deleted_at).

        :param db_session: Асинхронная сессия базы данных
        :param user_uid: UID пользователя
        :return: Объект пользователя или вызывает HTTPException
        """
        # Ищем пользователя в базе данных
        result = await db_session.execute(
            select(cls).where(cls.uid == user_uid)
        )
        user = result.scalars().first()

        if not user:
            logger.warning(f"Попытка удаления несуществующего пользователя с UID: {user_uid}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

        # Обновляем поле deleted_at
        user.deleted_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(user)

        logger.info(f"Пользователь с UID {user_uid} успешно удален (мягкое удаление)")
        return user
    
    @classmethod
    async def update_profile(cls, db_session: AsyncSession, user_uid: str, new_data: dict):
        """Обновление данных профиля пользователя."""
        user = await cls.get_user_by_uid(db_session, user_uid)
        if not user:
            logger.error(f"Пользователь с {user_uid} не найден")
            return None

        for key, value in new_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        return user
    
    @staticmethod
    async def get_users(
        db_session: AsyncSession,
        page: int = 1,
        per_page: int = 10,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        role_filter: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        include_relations: bool = False
    ) -> Dict[str, Any]:
        """
        Получение списка пользователей с пагинацией, фильтрацией и сортировкой
        
        :param db_session: Асинхронная сессия SQLAlchemy
        :param page: Номер страницы (начиная с 1)
        :param per_page: Количество записей на странице
        :param search: Строка для поиска по username, email, имени, фамилии
        :param sort_by: Поле для сортировки (поддерживаются поля модели User)
        :param sort_dir: Направление сортировки (asc/desc)
        :param role_filter: Фильтр по роли (global_role)
        :param is_active: Фильтр по активности
        :param is_verified: Фильтр по верификации
        :param include_relations: Включать ли связанные данные
        :return: Словарь с данными и метаданными пагинации
        """
        # Базовый запрос
        query = select(User).where(User.deleted_at == None)  # Исключаем удаленных
        
        # Добавляем загрузку отношений при необходимости
        if include_relations:
            query = query.options(
                selectinload(User.owned_rooms),
                selectinload(User.memberships),
                selectinload(User.penalties),
                selectinload(User.relationships)
            )
        
        # Применяем поиск
        if search:
            search = f"%{search.lower()}%"
            query = query.where(
                or_(
                    func.lower(User.username).ilike(search),
                    func.lower(User.email).ilike(search),
                    func.lower(User.first_name).ilike(search),
                    func.lower(User.last_name).ilike(search),
                    func.lower(User.phone).ilike(search),
                    func.cast(User.uid, String).ilike(search)
                )
            )
        
        # Применяем фильтры
        filters = []
        if role_filter:
            filters.append(User.global_role == role_filter)
        if is_active is not None:
            filters.append(User.is_active == is_active)
        if is_verified is not None:
            filters.append(User.is_verified == is_verified)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Применяем сортировку
        sort_field = getattr(User, sort_by, User.created_at)  # По умолчанию сортировка по дате создания
        if sort_dir.lower() == "desc":
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())
        
        # Получаем общее количество (для пагинации)
        count_query = query.with_only_columns(func.count()).order_by(None)
        total = (await db_session.execute(count_query)).scalar_one()
        
        # Применяем пагинацию
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        # Выполняем запрос
        result = await db_session.execute(query)
        users = result.scalars().unique().all()
        
        # Сериализация результатов
        users_data = []
        for user in users:
            user_data = {
                "uid": str(user.uid),
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "avatar": user.avatar,
                "global_role": user.global_role,
                "rating": user.rating,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "city": user.city,
                "country": user.country,
                "last_online": user.last_online.isoformat() if user.last_online else None,
                "stats": {
                    "rooms_owned": len(user.owned_rooms) if include_relations else None,
                    "penalties": len(user.penalties) if include_relations else None
                }
            }
            users_data.append(user_data)
        
        return {
            "data": users_data,
            "meta": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
                "sort_by": sort_by,
                "sort_dir": sort_dir
            }
        }

# Модель Penalty
class Penalty(Database.Base):
    __tablename__ = "penalties"

    id = Column(Integer, primary_key=True)
    user_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    penalty_type = Column(String(50))
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

    @classmethod
    async def create_penalty(
        cls, 
        db_session: AsyncSession, 
        user_uid: UUID, 
        penalty_type: str, 
        expires_at: datetime, 
        issuer_uid: UUID, 
        reason: str
    ):
        """
        Создает новое наказание в базе данных.
        
        :param db_session: Асинхронная сессия базы данных
        :param user_uid: UID пользователя
        :param penalty_type: Тип наказания
        :param expires_at: Дата окончания (UTC)
        :param issuer_uid: UID администратора
        :param reason: Причина наказания
        :return: Созданный объект Penalty
        """
        try:
            # Нормализация времени
            if expires_at.tzinfo is None:
                expires_at_utc = expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at_utc = expires_at.astimezone(timezone.utc)
            
            expires_at_for_db = expires_at_utc.replace(tzinfo=None)
            
            logger.debug(f"Original expires_at: {expires_at}")
            logger.debug(f"UTC expires_at: {expires_at_utc}")
            logger.debug(f"DB expires_at: {expires_at_for_db}")

            # Создание наказания
            penalty = cls(
                user_uid=user_uid,
                penalty_type=str(penalty_type),
                expires_at=expires_at_for_db,
                issuer_uid=issuer_uid,
                reason=reason,
            )

            db_session.add(penalty)
            await db_session.commit()
            await db_session.refresh(penalty)

            return penalty

        except ValueError as e:
            await db_session.rollback()
            logger.error(f"Ошибка валидации: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Некорректные данные: {str(e)}"
            )
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"Ошибка при создании наказания: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при создании наказания"
            )
        
    @classmethod
    async def get_active_mute(cls, db_session: AsyncSession, user_uid: UUID):
        """
        Возвращает активное наказание типа mute для пользователя.
        :param db_session: Асинхронная сессия БД
        :param user_uid: UID пользователя
        :return: None или словарь с данными о наказании
        """
        current_time = datetime.utcnow()
        logger.debug(f"Текущее время (UTC): {current_time}")

        result = await db_session.execute(
            select(cls).where(
                cls.user_uid == user_uid,
                cls.penalty_type == 'mute',
                cls.expires_at > current_time + timedelta(seconds=1)
            )
        )
        active_penalty = result.scalars().first()

        if active_penalty:
            logger.debug(f"Активное наказание найдено: expires_at={active_penalty.expires_at}")
            return {
                "expires_at": active_penalty.expires_at.isoformat(),
                "reason": active_penalty.reason,
            }
        logger.debug("Активных наказаний нет")
        return None

    @classmethod
    async def get_user_penalties(cls, db_session: AsyncSession, user_uid: UUID):
        """
        Получает наказания пользователя за последний месяц.
        :param db_session: Асинхронная сессия БД
        :param user_uid: UID пользователя
        :return: Список словарей с данными о наказаниях
        """
        one_month_ago = datetime.utcnow() - timedelta(days=30)
        
        result = await db_session.execute(
            select(cls).where(
                cls.user_uid == user_uid,
                cls.issued_at >= one_month_ago
            )
        )
        penalties = result.scalars().all()
        
        return [
            {
                "id": penalty.id,
                "type": penalty.penalty_type,
                "reason": penalty.reason,
                "issued_at": penalty.issued_at.isoformat(),
                "expires_at": penalty.expires_at.isoformat(),
                "issuer_uid": penalty.issuer_uid,
                "issuer": {
                    "username": penalty.issuer.username,
                    "firstname": penalty.issuer.first_name,
                    "lastname": penalty.issuer.last_name
                },
            }
            for penalty in penalties
        ]
    
    @classmethod
    async def update_penalty(cls, db_session: AsyncSession, penalty_id: int, new_data: dict):
        """
        Обновляет данные наказания.
        :param db_session: Асинхронная сессия БД
        :param penalty_id: ID наказания
        :param new_data: Новые данные
        :return: Обновленный объект Penalty
        """
        result = await db_session.execute(
            select(cls).where(cls.id == penalty_id)
        )
        penalty = result.scalars().first()
        
        if not penalty:
            raise HTTPException(status_code=404, detail="Penalty not found")
        
        for key, value in new_data.items():
            setattr(penalty, key, value)
        
        await db_session.commit()
        await db_session.refresh(penalty)
        return penalty
    
    @classmethod
    async def delete_penalty(cls, db_session: AsyncSession, penalty_id: int):
        """
        Удаляет наказание.
        :param db_session: Асинхронная сессия БД
        :param penalty_id: ID наказания
        :return: Словарь с результатом операции
        """
        result = await db_session.execute(
            select(cls).where(cls.id == penalty_id)
        )
        penalty = result.scalars().first()
        
        if not penalty:
            raise HTTPException(status_code=404, detail="Penalty not found")
        
        await db_session.delete(penalty)
        await db_session.commit()
        
        return {"status": "ok", "message": "Penalty deleted"}


# Модель UserRelationship
class UserRelationship(Database.Base):
    __tablename__ = "user_relationships"

    __table_args__ = (
        UniqueConstraint('from_user_uid', 'to_user_uid', name='unique_relationship'),
    )

    id = Column(Integer, primary_key=True)
    from_user_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    to_user_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    relation_type = Column(String(50))
    since = Column(DateTime, default=datetime.utcnow)

    from_user = relationship("User", back_populates="relationships", foreign_keys=[from_user_uid])
    to_user = relationship("User", back_populates="related_to", foreign_keys=[to_user_uid])