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


class MessageNotificationPreference(Database.Base):
    """Account-level alert preferences for message delivery surfaces.

    These settings control notification UX only. They never grant or remove the
    right to receive/read a message and they do not replace block/privacy checks.
    External re-engagement channels default to disabled until explicitly enabled.
    """

    __tablename__ = "message_notification_preferences"

    account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="CASCADE"),
        primary_key=True,
    )
    messenger_in_app = Column(Boolean, nullable=False, default=True)
    space_in_app = Column(Boolean, nullable=False, default=True)
    messenger_sound = Column(Boolean, nullable=False, default=True)
    space_sound = Column(Boolean, nullable=False, default=True)
    email_unread_dm_nudge = Column(Boolean, nullable=False, default=False)
    web_push_messenger = Column(Boolean, nullable=False, default=False)
    web_push_space = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExternalDeliveryLedger(Database.Base):
    """Durable, privacy-minimal state for external notification delivery.

    Message contents and destination addresses are deliberately not persisted in
    this ledger. Delivery adapters resolve the current verified destination when
    they execute and only store provider ids/failure classes required for retry
    and auditability.
    """

    __tablename__ = "external_delivery_ledger"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="CASCADE"),
        nullable=False,
    )
    channel = Column(String(24), nullable=False)
    aggregate_key = Column(String(180), nullable=False)
    dedupe_key = Column(String(220), nullable=False)
    status = Column(String(24), nullable=False, default="pending")
    unread_count = Column(Integer, nullable=False, default=0)
    dialog_count = Column(Integer, nullable=False, default=0)
    attempt_count = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=True)
    attempted_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    provider_message_id = Column(String(180), nullable=True)
    failure_class = Column(String(80), nullable=True)
    claim_token = Column(String(64), nullable=True)
    claim_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "account_uid",
            "channel",
            "dedupe_key",
            name="uq_external_delivery_dedupe",
        ),
        Index("ix_external_delivery_pending", "channel", "status", "next_attempt_at", "created_at"),
        Index("ix_external_delivery_claim", "channel", "status", "claim_expires_at"),
        Index("ix_external_delivery_account_created", "account_uid", "created_at"),
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


class NotificationWorkerState(Database.Base):
    """Durable cursor for bounded externally-scheduled notification workers."""

    __tablename__ = "notification_worker_state"

    worker_name = Column(String(64), primary_key=True)
    cursor_account_uid = Column(UUID(as_uuid=True), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
