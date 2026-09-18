from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Database


class TrustSafetyAbuseSignal(Database.Base):
    """Durable privacy-minimal behavioral signal for moderator review.

    Signals are advisory evidence, never moderation actions. They intentionally
    store counters/thresholds rather than message bodies or private-dialog history.
    """

    __tablename__ = "trust_safety_abuse_signals"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="CASCADE"),
        nullable=False,
    )
    signal_type = Column(String(64), nullable=False)
    surface = Column(String(32), nullable=False)
    scope_uid = Column(UUID(as_uuid=True), nullable=True)
    severity = Column(String(16), nullable=False, default="medium")
    observed_count = Column(Integer, nullable=False, default=1)
    window_seconds = Column(Integer, nullable=False)
    dedupe_key = Column(String(96), nullable=False)
    details = Column(JSON, nullable=True)
    status = Column(String(24), nullable=False, default="open")
    review_note = Column(Text, nullable=True)
    reviewed_by_account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = Column(DateTime, nullable=True)
    first_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_trust_safety_abuse_signal_dedupe"),
        Index("ix_trust_safety_abuse_signal_queue", "status", "severity", "last_seen_at"),
        Index("ix_trust_safety_abuse_signal_account", "account_uid", "last_seen_at"),
        Index("ix_trust_safety_abuse_signal_type", "signal_type", "last_seen_at"),
    )
