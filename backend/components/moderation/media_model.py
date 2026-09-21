from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Database


class ModerationMediaRecord(Database.Base):
    """Reversible platform moderation state for one reported attachment.

    Public files may be moved out of the mounted uploads tree while a moderator
    reviews them. The private path is an implementation detail and is never
    exposed through the public API.
    """

    __tablename__ = "moderation_media_records"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    report_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("trust_safety_reports.uid", ondelete="CASCADE"),
        nullable=False,
    )
    source_type = Column(String(32), nullable=False)
    source_uid = Column(UUID(as_uuid=True), nullable=False)
    attachment_index = Column(Integer, nullable=False)
    target_account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="SET NULL"),
        nullable=True,
    )
    actor_account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="SET NULL"),
        nullable=True,
    )
    original_url = Column(String(512), nullable=True)
    original_relative_path = Column(String(512), nullable=True)
    private_relative_path = Column(String(512), nullable=True)
    mime_type = Column(String(128), nullable=True)
    original_name = Column(String(255), nullable=True)
    status = Column(String(24), nullable=False, default="quarantined")
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    restored_at = Column(DateTime, nullable=True)
    removed_at = Column(DateTime, nullable=True)
    retention_due_at = Column(DateTime, nullable=True)
    purged_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "report_uid",
            "source_uid",
            "attachment_index",
            name="uq_moderation_media_report_attachment",
        ),
        Index("ix_moderation_media_report_status", "report_uid", "status", "created_at"),
        Index("ix_moderation_media_target_created", "target_account_uid", "created_at"),
        Index("ix_moderation_media_actor_created", "actor_account_uid", "created_at"),
        Index(
            "ix_moderation_media_retention_due",
            "status",
            "purged_at",
            "retention_due_at",
        ),
    )
