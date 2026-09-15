"""add consent-first creator support and cosmetic gifts

Revision ID: k0a6d4f88001
Revises: j9f5c3e77001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88001"
down_revision: Union[str, None] = "j9f5c3e77001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GIFT_ROWS = [
    {"code": "applause", "name": "Аплодисменты", "description": "Тёплая поддержка идеи или встречи", "icon": "👏", "target_scope": "both"},
    {"code": "bouquet", "name": "Букет", "description": "Добрый знак внимания для Persona", "icon": "💐", "target_scope": "persona"},
    {"code": "lantern", "name": "Фонарик", "description": "Спасибо пространству за атмосферу", "icon": "🏮", "target_scope": "space"},
    {"code": "spark", "name": "Искра", "description": "За хороший разговор или идею", "icon": "✨", "target_scope": "both"},
    {"code": "warm_cup", "name": "Тёплая кружка", "description": "Спокойный знак благодарности", "icon": "☕", "target_scope": "both"},
]


def upgrade() -> None:
    op.create_table(
        "creator_support_profiles",
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("note", sa.String(length=280), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_uid"),
    )

    op.create_table(
        "space_support_settings",
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("note", sa.String(length=280), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("room_uid"),
    )

    gift_definitions = op.create_table(
        "gift_definitions",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=220), nullable=True),
        sa.Column("icon", sa.String(length=16), nullable=False),
        sa.Column("target_scope", sa.String(length=16), nullable=False, server_default="both"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("target_scope IN ('persona', 'space', 'both')", name="ck_gift_definition_target_scope"),
        sa.PrimaryKeyConstraint("code"),
    )
    op.bulk_insert(gift_definitions, GIFT_ROWS)

    op.create_table(
        "support_ledger_entries",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_kind", sa.String(length=16), nullable=False),
        sa.Column("target_persona_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_room_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_label", sa.String(length=120), nullable=False),
        sa.Column("sender_label", sa.String(length=80), nullable=True),
        sa.Column("gift_code", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=280), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("target_kind IN ('persona', 'space')", name="ck_support_ledger_target_kind"),
        sa.ForeignKeyConstraint(["sender_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_persona_uid"], ["personas.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_room_uid"], ["rooms.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gift_code"], ["gift_definitions.code"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_support_ledger_sender_created", "support_ledger_entries", ["sender_account_uid", "created_at"])
    op.create_index("ix_support_ledger_persona_created", "support_ledger_entries", ["target_persona_uid", "created_at"])
    op.create_index("ix_support_ledger_space_created", "support_ledger_entries", ["target_room_uid", "created_at"])

    op.create_table(
        "cosmetic_entitlements",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_ledger_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("persona_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("gift_code", sa.String(length=32), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "(persona_uid IS NOT NULL AND room_uid IS NULL) OR (persona_uid IS NULL AND room_uid IS NOT NULL)",
            name="ck_cosmetic_entitlement_exact_target",
        ),
        sa.ForeignKeyConstraint(["source_ledger_uid"], ["support_ledger_entries.uid"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["persona_uid"], ["personas.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["gift_code"], ["gift_definitions.code"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("source_ledger_uid"),
    )
    op.create_index("ix_cosmetic_entitlements_persona", "cosmetic_entitlements", ["persona_uid", "granted_at"])
    op.create_index("ix_cosmetic_entitlements_space", "cosmetic_entitlements", ["room_uid", "granted_at"])


def downgrade() -> None:
    op.drop_index("ix_cosmetic_entitlements_space", table_name="cosmetic_entitlements")
    op.drop_index("ix_cosmetic_entitlements_persona", table_name="cosmetic_entitlements")
    op.drop_table("cosmetic_entitlements")
    op.drop_index("ix_support_ledger_space_created", table_name="support_ledger_entries")
    op.drop_index("ix_support_ledger_persona_created", table_name="support_ledger_entries")
    op.drop_index("ix_support_ledger_sender_created", table_name="support_ledger_entries")
    op.drop_table("support_ledger_entries")
    op.drop_table("gift_definitions")
    op.drop_table("space_support_settings")
    op.drop_table("creator_support_profiles")
