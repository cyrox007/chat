from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
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
    calibration_label = Column(String(24), nullable=True)
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


class ProtectiveHoldEvaluation(Database.Base):
    """Durable privacy-minimal shadow/enforcement decision for calibration.

    The row stores only policy inputs/outcome needed to compare automation with
    later human labels. It intentionally contains no message body, attachment
    metadata, handle, recipient list or free-form evidence.
    """

    __tablename__ = "protective_hold_evaluations"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    signal_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("trust_safety_abuse_signals.uid", ondelete="CASCADE"),
        nullable=False,
    )
    account_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.uid", ondelete="CASCADE"),
        nullable=False,
    )
    signal_type = Column(String(64), nullable=False)
    capability = Column(String(64), nullable=True)
    mode = Column(String(16), nullable=False)
    decision = Column(String(48), nullable=False)
    would_hold = Column(Boolean, nullable=False, default=False)
    corroboration_count = Column(Integer, nullable=False, default=0)
    min_high_signals = Column(Integer, nullable=False)
    lookback_seconds = Column(Integer, nullable=False)
    hold_minutes = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "signal_uid",
            name="uq_protective_hold_evaluation_signal",
        ),
        Index(
            "ix_protective_hold_evaluation_calibration",
            "signal_type",
            "would_hold",
            "created_at",
        ),
        Index(
            "ix_protective_hold_evaluation_account",
            "account_uid",
            "created_at",
        ),
    )
