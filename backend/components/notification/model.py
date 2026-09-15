from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Database


class ActivityReminderPreference(Database.Base):
    __tablename__ = "activity_reminder_preferences"

    activity_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("space_activities.uid", ondelete="CASCADE"),
        primary_key=True,
    )
    account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="CASCADE"),
        primary_key=True,
    )
    lead_minutes = Column(Integer, nullable=False, default=60)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_activity_reminders_account_enabled", "account_uid", "enabled"),
    )


class UserNotification(Database.Base):
    __tablename__ = "user_notifications"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="CASCADE"),
        nullable=False,
    )
    kind = Column(String(48), nullable=False)
    dedupe_key = Column(String(180), nullable=False)
    title = Column(String(180), nullable=False)
    body = Column(String(500), nullable=False)
    context_room_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("rooms.uid", ondelete="SET NULL"),
        nullable=True,
    )
    activity_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("space_activities.uid", ondelete="SET NULL"),
        nullable=True,
    )
    occurrence_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("activity_occurrences.uid", ondelete="SET NULL"),
        nullable=True,
    )
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "account_uid",
            "kind",
            "dedupe_key",
            name="uq_user_notification_dedupe",
        ),
        Index("ix_user_notifications_account_created", "account_uid", "created_at"),
        Index("ix_user_notifications_account_unread", "account_uid", "read_at"),
    )
