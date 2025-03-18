from typing import List, Optional
from uuid import uuid4
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Session

from database import Database

class Room(Database.Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    uid = Column(UUID(as_uuid=True), default=uuid4, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    region = Column(String(100))
    country = Column(String(100))
    tags = Column(String(200))
    rating = Column(Integer, default=0)
    owner_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Используйте строковые литералы для отношений
    owner = relationship("User", back_populates="owned_rooms")  # Здесь оставляем "User" строкой
    members = relationship("RoomMember", back_populates="room")
    messages = relationship("Message", back_populates="room")

    @staticmethod
    def get_all_active_rooms(db: Session) -> List["Room"]:
        """Получить все активные комнаты."""
        return db.query(Room).filter(Room.is_active == True).all()
    
    @staticmethod
    def get_room_by_uid(db: Session, room_uid: UUID) -> Optional["Room"]:
        """Получить комнату по UID."""
        return db.query(Room).filter(Room.uid == room_uid, Room.is_active == True).first()
    
    @staticmethod
    def create_room(db: Session, room_data: dict, owner_uid: UUID) -> "Room":
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
        db.commit()
        db.refresh(new_room)
        return new_room
    
    @staticmethod
    def update_room(db: Session, room_uid: UUID, update_data: dict) -> Optional["Room"]:
        """Обновить данные комнаты."""
        room = db.query(Room).filter(Room.uid == room_uid, Room.is_active == True).first()
        if not room:
            return None

        for key, value in update_data.items():
            setattr(room, key, value)

        db.commit()
        db.refresh(room)
        return room
    
    @staticmethod
    def delete_room(db: Session, room_uid: UUID) -> bool:
        """Мягкое удаление комнаты."""
        room = db.query(Room).filter(Room.uid == room_uid, Room.is_active == True).first()
        if not room:
            return False

        room.is_active = False
        db.commit()
        return True

class RoomMember(Database.Base):
    __tablename__ = "room_members"

    id = Column(Integer, primary_key=True)
    room_uid = Column(UUID(as_uuid=True), ForeignKey("rooms.uid"))
    user_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"))
    role = Column(String(50), default="member")
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_banned = Column(Boolean, default=False)

    room = relationship("Room", back_populates="members")
    user = relationship("User", back_populates="memberships")

    @staticmethod
    def add_member(db: Session, room_uid: str, user_uid: str, role: str = "member") -> "RoomMember":
        """Добавить пользователя в комнату."""
        member = RoomMember(room_uid=room_uid, user_uid=user_uid, role=role)
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def remove_member(db: Session, room_uid: str, user_uid: str) -> bool:
        """Удалить пользователя из комнаты."""
        member = (
            db.query(RoomMember)
            .filter(RoomMember.room_uid == room_uid, RoomMember.user_uid == user_uid)
            .first()
        )
        if not member:
            return False

        db.delete(member)
        db.commit()
        return True