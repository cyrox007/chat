from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Database


class ModerationAIRecommendation(Database.Base):
    """Advisory AI assessment attached to one Trust & Safety report.

    This table deliberately stores structured recommendation fields only. It does
    not store provider prompts, raw provider responses, chain-of-thought, private
    conversation history or attachment URLs.
    """

    __tablename__ = "moderation_ai_recommendations"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    report_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("trust_safety_reports.uid", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="SET NULL"),
        nullable=True,
    )
    provider_key = Column(String(32), nullable=False)
    model_name = Column(String(128), nullable=True)
    schema_version = Column(String(16), nullable=False, default="v1")

    category = Column(String(32), nullable=False)
    severity = Column(String(16), nullable=False)
    confidence_percent = Column(Integer, nullable=False)
    summary = Column(Text, nullable=False)
    recommended_action = Column(String(32), nullable=False)
    suggested_capability = Column(String(64), nullable=True)
    suggested_scope_type = Column(String(16), nullable=False, default="platform")
    suggested_duration_minutes = Column(Integer, nullable=True)
    rationale = Column(Text, nullable=False)

    outcome = Column(String(24), nullable=False, default="not_used")
    outcome_note = Column(Text, nullable=True)
    outcome_by_account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="SET NULL"),
        nullable=True,
    )
    outcome_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_moderation_ai_report_created", "report_uid", "created_at"),
        Index("ix_moderation_ai_outcome_created", "outcome", "created_at"),
        Index("ix_moderation_ai_requester_created", "requested_by_account_uid", "created_at"),
    )
