from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID

from database import Database


class CreatorSupportProfile(Database.Base):
    __tablename__ = "creator_support_profiles"

    account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="CASCADE"), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=False)
    note = Column(String(280), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpaceSupportSettings(Database.Base):
    __tablename__ = "space_support_settings"

    room_uid = Column(UUID(as_uuid=True), ForeignKey("rooms.uid", ondelete="CASCADE"), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=False)
    note = Column(String(280), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class GiftDefinition(Database.Base):
    __tablename__ = "gift_definitions"

    code = Column(String(32), primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(220), nullable=True)
    icon = Column(String(16), nullable=False)
    target_scope = Column(String(16), nullable=False, default="both")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("target_scope IN ('persona', 'space', 'both')", name="ck_gift_definition_target_scope"),
    )


class SupportLedgerEntry(Database.Base):
    """Append-only support history; target/sender labels preserve historical meaning."""

    __tablename__ = "support_ledger_entries"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    sender_account_uid = Column(UUID(as_uuid=True), ForeignKey("accounts.uid", ondelete="SET NULL"), nullable=True)
    target_kind = Column(String(16), nullable=False)
    target_persona_uid = Column(UUID(as_uuid=True), ForeignKey("personas.uid", ondelete="SET NULL"), nullable=True)
    target_room_uid = Column(UUID(as_uuid=True), ForeignKey("rooms.uid", ondelete="SET NULL"), nullable=True)
    target_label = Column(String(120), nullable=False)
    sender_label = Column(String(80), nullable=True)
    gift_code = Column(String(32), ForeignKey("gift_definitions.code", ondelete="RESTRICT"), nullable=False)
    message = Column(String(280), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("target_kind IN ('persona', 'space')", name="ck_support_ledger_target_kind"),
        CheckConstraint(
            "(target_kind = 'persona' AND target_persona_uid IS NOT NULL AND target_room_uid IS NULL) OR "
            "(target_kind = 'space' AND target_persona_uid IS NULL AND target_room_uid IS NOT NULL)",
            name="ck_support_ledger_exact_target",
        ),
        Index("ix_support_ledger_sender_created", "sender_account_uid", "created_at"),
        Index("ix_support_ledger_persona_created", "target_persona_uid", "created_at"),
        Index("ix_support_ledger_space_created", "target_room_uid", "created_at"),
    )


class CosmeticEntitlement(Database.Base):
    __tablename__ = "cosmetic_entitlements"

    uid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_ledger_uid = Column(UUID(as_uuid=True), ForeignKey("support_ledger_entries.uid", ondelete="RESTRICT"), nullable=False, unique=True)
    persona_uid = Column(UUID(as_uuid=True), ForeignKey("personas.uid", ondelete="CASCADE"), nullable=True)
    room_uid = Column(UUID(as_uuid=True), ForeignKey("rooms.uid", ondelete="CASCADE"), nullable=True)
    gift_code = Column(String(32), ForeignKey("gift_definitions.code", ondelete="RESTRICT"), nullable=False)
    granted_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "(persona_uid IS NOT NULL AND room_uid IS NULL) OR (persona_uid IS NULL AND room_uid IS NOT NULL)",
            name="ck_cosmetic_entitlement_exact_target",
        ),
        Index("ix_cosmetic_entitlements_persona", "persona_uid", "granted_at"),
        Index("ix_cosmetic_entitlements_space", "room_uid", "granted_at"),
    )
