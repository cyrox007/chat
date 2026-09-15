from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Database


class PersonaAppearance(Database.Base):
    __tablename__ = "persona_appearance"

    persona_uid = Column(UUID(as_uuid=True), ForeignKey("personas.uid", ondelete="CASCADE"), primary_key=True)
    accent_preset = Column(String(32), nullable=False, default="plum")
    background_preset = Column(String(32), nullable=False, default="soft")
    avatar_frame_preset = Column(String(32), nullable=False, default="none")
    status_line = Column(String(120), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpaceAppearance(Database.Base):
    __tablename__ = "space_appearance"

    room_uid = Column(UUID(as_uuid=True), ForeignKey("rooms.uid", ondelete="CASCADE"), primary_key=True)
    theme_preset = Column(String(32), nullable=False, default="lounge")
    cover_preset = Column(String(32), nullable=False, default="soft-gradient")
    ambient_icon = Column(String(16), nullable=True)
    welcome_line = Column(String(160), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpaceActivity(Database.Base):
    __tablename__ = "space_activities"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    room_uid = Column(UUID(as_uuid=True), ForeignKey("rooms.uid", ondelete="CASCADE"), nullable=False)
    created_by_account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="SET NULL"), nullable=True)
    title = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    activity_type = Column(String(32), nullable=False, default="hangout")
    starts_at = Column(DateTime, nullable=False)
    recurrence = Column(String(24), nullable=False, default="none")
    status = Column(String(24), nullable=False, default="scheduled")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_space_activities_room_start", "room_uid", "starts_at"),
        Index("ix_space_activities_room_status", "room_uid", "status"),
    )


class ActivityRSVP(Database.Base):
    __tablename__ = "activity_rsvps"

    activity_uid = Column(UUID(as_uuid=True), ForeignKey("space_activities.uid", ondelete="CASCADE"), primary_key=True)
    account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="CASCADE"), primary_key=True)
    status = Column(String(24), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("activity_uid", "account_uid", name="uq_activity_rsvp"),
        Index("ix_activity_rsvps_account", "account_uid", "status"),
    )
