from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID

from database import Database


class ConversationRound(Database.Base):
    __tablename__ = "conversation_rounds"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    activity_uid = Column(UUID(as_uuid=True), ForeignKey("space_activities.uid", ondelete="CASCADE"), nullable=False)
    created_by_account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="SET NULL"), nullable=True)
    round_type = Column(String(24), nullable=False)
    prompt = Column(String(500), nullable=False)
    option_a = Column(String(120), nullable=True)
    option_b = Column(String(120), nullable=True)
    status = Column(String(24), nullable=False, default="open")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_conversation_rounds_activity_created", "activity_uid", "created_at"),
        Index(
            "uq_conversation_rounds_one_open_per_activity",
            "activity_uid",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )


class ConversationRoundResponse(Database.Base):
    __tablename__ = "conversation_round_responses"

    round_uid = Column(UUID(as_uuid=True), ForeignKey("conversation_rounds.uid", ondelete="CASCADE"), primary_key=True)
    account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="CASCADE"), primary_key=True)
    choice = Column(String(1), nullable=True)
    body = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_conversation_round_responses_account", "account_uid", "created_at"),
    )
