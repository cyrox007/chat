from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Database


class SpaceSettings(Database.Base):
    __tablename__ = "space_settings"

    room_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("rooms.uid", ondelete="CASCADE"),
        primary_key=True,
    )
    purpose = Column(String(32), nullable=False, default="community")
    visibility = Column(String(24), nullable=False, default="public")
    join_policy = Column(String(24), nullable=False, default="open")
    language = Column(String(16), nullable=True)
    member_limit = Column(Integer, nullable=False, default=250)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    room = relationship("Room")


class SpaceMembership(Database.Base):
    __tablename__ = "space_memberships"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    room_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("rooms.uid", ondelete="CASCADE"),
        nullable=False,
    )
    account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(24), nullable=False, default="member")
    status = Column(String(24), nullable=False, default="active")
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    room = relationship("Room")
    account = relationship("Account")

    __table_args__ = (
        UniqueConstraint("room_uid", "account_uid", name="uq_space_membership"),
        Index("ix_space_memberships_account_status", "account_uid", "status"),
        Index("ix_space_memberships_room_role", "room_uid", "role", "status"),
    )


class SpaceTag(Database.Base):
    __tablename__ = "space_tags"

    room_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("rooms.uid", ondelete="CASCADE"),
        primary_key=True,
    )
    slug = Column(String(64), primary_key=True)
    label = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    room = relationship("Room")

    __table_args__ = (
        Index("ix_space_tags_slug", "slug"),
    )
