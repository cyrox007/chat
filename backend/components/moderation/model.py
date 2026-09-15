from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Database


class ModerationReport(Database.Base):
    __tablename__ = "moderation_reports"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    room_uid = Column(UUID(as_uuid=True), ForeignKey("rooms.uid", ondelete="CASCADE"), nullable=False)
    reporter_account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="SET NULL"), nullable=True)
    target_account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="SET NULL"), nullable=True)
    message_uid = Column(UUID(as_uuid=True), ForeignKey("messages.uid", ondelete="SET NULL"), nullable=True)
    category = Column(String(32), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(24), nullable=False, default="open")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_moderation_reports_room_status", "room_uid", "status", "created_at"),
        Index("ix_moderation_reports_reporter", "reporter_account_uid", "created_at"),
        Index("ix_moderation_reports_target", "target_account_uid", "created_at"),
    )


class ModerationAction(Database.Base):
    __tablename__ = "moderation_actions"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    room_uid = Column(UUID(as_uuid=True), ForeignKey("rooms.uid", ondelete="CASCADE"), nullable=False)
    report_uid = Column(UUID(as_uuid=True), ForeignKey("moderation_reports.uid", ondelete="SET NULL"), nullable=True)
    moderator_account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="SET NULL"), nullable=True)
    target_account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="SET NULL"), nullable=True)
    action_type = Column(String(24), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(24), nullable=False, default="active")
    starts_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    legacy_room_ban_id = Column(Integer, ForeignKey("room_bans.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("report_uid", name="uq_moderation_action_report"),
        Index("ix_moderation_actions_room_target", "room_uid", "target_account_uid", "created_at"),
        Index("ix_moderation_actions_target_status", "target_account_uid", "status", "created_at"),
        Index("ix_moderation_actions_report", "report_uid"),
    )


class ModerationAppeal(Database.Base):
    __tablename__ = "moderation_appeals"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    action_uid = Column(UUID(as_uuid=True), ForeignKey("moderation_actions.uid", ondelete="CASCADE"), nullable=False)
    appellant_account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="SET NULL"), nullable=True)
    reviewer_account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="SET NULL"), nullable=True)
    body = Column(Text, nullable=False)
    status = Column(String(24), nullable=False, default="pending")
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("action_uid", "appellant_account_uid", name="uq_moderation_appeal_action_appellant"),
        Index("ix_moderation_appeals_action_status", "action_uid", "status"),
        Index("ix_moderation_appeals_appellant", "appellant_account_uid", "created_at"),
    )
