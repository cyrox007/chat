from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Database


class AchievementDefinition(Database.Base):
    __tablename__ = "achievement_definitions"

    code = Column(String(64), primary_key=True)
    title = Column(String(120), nullable=False)
    description = Column(String(320), nullable=False)
    icon_preset = Column(String(32), nullable=False, default="spark")
    category = Column(String(32), nullable=False, default="participation")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AccountAchievement(Database.Base):
    __tablename__ = "account_achievements"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="CASCADE"), nullable=False)
    achievement_code = Column(
        String(64),
        ForeignKey("achievement_definitions.code", ondelete="RESTRICT"),
        nullable=False,
    )
    context_room_uid = Column(UUID(as_uuid=True), ForeignKey("rooms.uid", ondelete="SET NULL"), nullable=True)
    source_kind = Column(String(64), nullable=False)
    source_uid = Column(UUID(as_uuid=True), nullable=True)
    earned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("account_uid", "achievement_code", name="uq_account_achievement_code"),
        Index("ix_account_achievements_account_earned", "account_uid", "earned_at"),
        Index("ix_account_achievements_context_room", "context_room_uid", "earned_at"),
    )
