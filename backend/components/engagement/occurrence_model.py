from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Database


class ActivityOccurrence(Database.Base):
    __tablename__ = "activity_occurrences"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    activity_uid = Column(
        UUID(as_uuid=True),
        ForeignKey("space_activities.uid", ondelete="CASCADE"),
        nullable=False,
    )
    starts_at = Column(DateTime, nullable=False)
    status = Column(String(24), nullable=False, default="scheduled")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("activity_uid", "starts_at", name="uq_activity_occurrence_start"),
        Index("ix_activity_occurrences_start_status", "starts_at", "status"),
        Index("ix_activity_occurrences_activity_start", "activity_uid", "starts_at"),
    )
