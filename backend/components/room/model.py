from typing import List, Optional
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, exists, or_, select, update
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession

from database import Database

class Room(Database.Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    uid = Column(PG_UUID(as_uuid=True), default=uuid4, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    region = Column(String(100))
    country = Column(String(100))
    tags = Column(String(200))
    rating = Column(Integer, default=0)
    owner_uid = Column(PG_UUID(as_uuid=True), ForeignKey("users.uid"))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    owner = relationship("User", back_populates="owned_rooms")
    members = relationship("RoomMember", back_populates="room")
    messages = relationship("Message", back_populates="room")
    bans = relationship("RoomBan", back_populates="room")

    @staticmethod
    async def get_room_with_details(db: AsyncSession, room_uid: UUID) -> Optional[dict]:
        """Получить полную информацию о комнате с модераторами и активными банами"""
        room = await Room.get_room_by_uid(db, room_uid)
        if not room:
            return None
        
        moderators = await RoomMember.get_moderators(db, room_uid)
        active_bans = await RoomBan.get_active_bans(db, room_uid)

        return {
            "uid": str(room.uid),
            "name": room.name,
            "description": room.description,
            "region": room.region,
            "country": room.country,
            "tags": room.tags,
            "rating": room.rating,
            "owner_uid": str(room.owner_uid),
            "created_at": room.created_at.isoformat(),
            "moderators": [str(m) for m in moderators],
            "active_bans": [
                {
                    "user_uid": str(ban.user_uid),
                    "reason": ban.reason,
                    "banned_by": str(ban.banned_by_uid),
                    "expires_at": ban.expires_at.isoformat() if ban.expires_at else None
                }
                for ban in active_bans
            ]
        }

    @staticmethod
    async def add_moderator(db: AsyncSession, room_uid: UUID, user_uid: UUID) -> bool:
        """Назначить пользователя модератором комнаты"""
        # Проверяем, что пользователь уже участник комнаты
        member = await RoomMember.add_member(db, room_uid, user_uid)
        if not member:
            return False

        member.role = "moderator"
        await db.commit()
        return True

    @staticmethod
    async def remove_moderator(db: AsyncSession, room_uid: UUID, user_uid: UUID) -> bool:
        """Снять пользователя с роли модератора"""
        member = await RoomMember.get_member(db, room_uid, user_uid)
        if not member or member.role != "moderator":
            return False

        member.role = "member"
        await db.commit()
        return True

    @staticmethod
    async def get_all_active_rooms(db: AsyncSession) -> List["Room"]:
        """Получить все активные комнаты."""
        result = await db.execute(
            select(Room).where(Room.is_active == True)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_room_by_uid(db: AsyncSession, room_uid: UUID) -> Optional["Room"]:
        """Получить комнату по UID."""
        result = await db.execute(
            select(Room).where(
                Room.uid == room_uid,
                Room.is_active == True
            )
        )
        return result.scalars().first()
    
    @staticmethod
    async def create_room(db: AsyncSession, room_data: dict, owner_uid: UUID) -> "Room":
        """Создать новую комнату."""
        new_room = Room(
            name=room_data.get("name"),
            description=room_data.get("description"),
            region=room_data.get("region"),
            country=room_data.get("country"),
            tags=room_data.get("tags"),
            owner_uid=owner_uid
        )
        db.add(new_room)
        await db.commit()
        await db.refresh(new_room)
        return new_room
    
    @staticmethod
    async def update_room(db: AsyncSession, room_uid: UUID, update_data: dict) -> Optional["Room"]:
        """Обновить данные комнаты."""
        result = await db.execute(
            select(Room).where(
                Room.uid == room_uid,
                Room.is_active == True
            )
        )
        room = result.scalars().first()
        if not room:
            return None

        for key, value in update_data.items():
            setattr(room, key, value)

        await db.commit()
        await db.refresh(room)
        return room
    
    @staticmethod
    async def delete_room(db: AsyncSession, room_uid: UUID) -> bool:
        """Мягкое удаление комнаты."""
        result = await db.execute(
            select(Room).where(
                Room.uid == room_uid,
                Room.is_active == True
            )
        )
        room = result.scalars().first()
        if not room:
            return False

        room.is_active = False
        await db.commit()
        return True
    
    @staticmethod
    async def get_rooms_by_owner(db: AsyncSession, owner_uid: UUID) -> List["Room"]:
        """Получить комнаты владельца."""
        result = await db.execute(
            select(Room).where(
                Room.owner_uid == owner_uid,
                Room.is_active == True
            )
        )
        return result.scalars().all()

class RoomMember(Database.Base):
    __tablename__ = "room_members"

    id = Column(Integer, primary_key=True)
    room_uid = Column(PG_UUID(as_uuid=True), ForeignKey("rooms.uid"))
    user_uid = Column(PG_UUID(as_uuid=True), ForeignKey("users.uid"))
    role = Column(String(50), default="member")
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_banned = Column(Boolean, default=False)

    room = relationship("Room", back_populates="members")
    user = relationship("User", back_populates="memberships")

    @staticmethod
    async def add_member(db: AsyncSession, room_uid: str, user_uid: str, role: str = "member") -> "RoomMember":
        """Добавить пользователя в комнату."""
        member = RoomMember(
            room_uid=room_uid,
            user_uid=user_uid,
            role=role
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return member

    @staticmethod
    async def remove_member(db: AsyncSession, room_uid: str, user_uid: str) -> bool:
        """Удалить пользователя из комнаты."""
        result = await db.execute(
            select(RoomMember).where(
                RoomMember.room_uid == room_uid,
                RoomMember.user_uid == user_uid
            )
        )
        member = result.scalars().first()
        if not member:
            return False

        await db.delete(member)
        await db.commit()
        return True
    
    @staticmethod
    async def get_moderators(db: AsyncSession, room_uid: UUID) -> List[UUID]:
        """Получить список модераторов комнаты"""
        result = await db.execute(
            select(RoomMember.user_uid).where(
                RoomMember.room_uid == room_uid,
                RoomMember.role == "moderator"
            )
        )
        return [uid for (uid,) in result.all()]

    @staticmethod
    async def get_member(db: AsyncSession, room_uid: UUID, user_uid: UUID) -> Optional["RoomMember"]:
        """Получить участника комнаты"""
        result = await db.execute(
            select(RoomMember).where(
                RoomMember.room_uid == room_uid,
                RoomMember.user_uid == user_uid
            )
        )
        return result.scalars().first()

    @staticmethod
    async def is_moderator(db: AsyncSession, room_uid: UUID, user_uid: UUID) -> bool:
        """Проверить, является ли пользователь модератором комнаты"""
        result = await db.execute(
            select(exists().where(
                RoomMember.room_uid == room_uid,
                RoomMember.user_uid == user_uid,
                RoomMember.role == "moderator"
            ))
        )
        return result.scalar()


class RoomBan(Database.Base):
    __tablename__ = "room_bans"
    
    id = Column(Integer, primary_key=True)
    room_uid = Column(PG_UUID(as_uuid=True), ForeignKey("rooms.uid"))
    user_uid = Column(PG_UUID(as_uuid=True), ForeignKey("users.uid"))
    banned_by_uid = Column(PG_UUID(as_uuid=True), ForeignKey("users.uid"))  # Кто забанил
    reason = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # NULL означает перманентный бан
    is_active = Column(Boolean, default=True)  # Для возможности досрочной разблокировки

    # Отношения
    room = relationship("Room")
    user = relationship("User", foreign_keys=[user_uid])
    banned_by = relationship("User", foreign_keys=[banned_by_uid])

    @staticmethod
    async def ban_user(
        db: AsyncSession,
        room_uid: UUID,
        user_uid: UUID,
        banned_by_uid: UUID,
        reason: str = None,
        ban_duration: timedelta = None
    ) -> "RoomBan":
        """Добавить бан пользователю"""
        # Деактивируем предыдущие баны если есть
        await db.execute(
            update(RoomBan)
            .where(
                RoomBan.room_uid == room_uid,
                RoomBan.user_uid == user_uid,
                RoomBan.is_active == True
            )
            .values(is_active=False)
        )
        
        expires_at = datetime.utcnow() + ban_duration if ban_duration else None
        
        new_ban = RoomBan(
            room_uid=room_uid,
            user_uid=user_uid,
            banned_by_uid=banned_by_uid,
            reason=reason,
            expires_at=expires_at
        )
        
        db.add(new_ban)
        await db.commit()
        await db.refresh(new_ban)
        return new_ban

    @staticmethod
    async def unban_user(db: AsyncSession, room_uid: UUID, user_uid: UUID) -> bool:
        """Снять бан с пользователя"""
        result = await db.execute(
            update(RoomBan)
            .where(
                RoomBan.room_uid == room_uid,
                RoomBan.user_uid == user_uid,
                RoomBan.is_active == True
            )
            .values(is_active=False)
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_active_bans(db: AsyncSession, room_uid: UUID) -> List["RoomBan"]:
        """Получить активные баны в комнате"""
        result = await db.execute(
            select(RoomBan).where(
                RoomBan.room_uid == room_uid,
                RoomBan.is_active == True,
                or_(
                    RoomBan.expires_at == None,
                    RoomBan.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalars().all()

    @staticmethod
    async def is_user_banned(db: AsyncSession, room_uid: UUID, user_uid: UUID) -> bool:
        """Проверить, забанен ли пользователь"""
        result = await db.execute(
            select(exists().where(
                RoomBan.room_uid == room_uid,
                RoomBan.user_uid == user_uid,
                RoomBan.is_active == True,
                or_(
                    RoomBan.expires_at == None,
                    RoomBan.expires_at > datetime.utcnow()
                )
            ))
        )
        return result.scalar()