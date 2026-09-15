"""add earned achievements and conversation rounds

Revision ID: i8e4b2d66001
Revises: h7d3a1c55001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "i8e4b2d66001"
down_revision: Union[str, None] = "h7d3a1c55001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACHIEVEMENTS = (
    (
        "first_host",
        "Первый повод встретиться",
        "Создана первая активность в пространстве.",
        "calendar-star",
        "participation",
    ),
    (
        "conversation_starter",
        "Начал разговор",
        "Открыт первый совместный разговорный раунд.",
        "spark",
        "conversation",
    ),
    (
        "first_round_response",
        "Поддержал разговор",
        "Дан первый ответ в совместном разговорном раунде.",
        "chat-heart",
        "conversation",
    ),
)


def upgrade() -> None:
    op.create_table(
        "achievement_definitions",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=320), nullable=False),
        sa.Column("icon_preset", sa.String(length=32), nullable=False, server_default="spark"),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="participation"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("code"),
    )

    op.create_table(
        "account_achievements",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("achievement_code", sa.String(length=64), nullable=False),
        sa.Column("context_room_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_kind", sa.String(length=64), nullable=False),
        sa.Column("source_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("earned_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["achievement_code"], ["achievement_definitions.code"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["context_room_uid"], ["rooms.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("account_uid", "achievement_code", name="uq_account_achievement_code"),
    )
    op.create_index(
        "ix_account_achievements_account_earned",
        "account_achievements",
        ["account_uid", "earned_at"],
    )
    op.create_index(
        "ix_account_achievements_context_room",
        "account_achievements",
        ["context_room_uid", "earned_at"],
    )

    achievement_table = sa.table(
        "achievement_definitions",
        sa.column("code", sa.String),
        sa.column("title", sa.String),
        sa.column("description", sa.String),
        sa.column("icon_preset", sa.String),
        sa.column("category", sa.String),
    )
    op.bulk_insert(
        achievement_table,
        [
            {
                "code": code,
                "title": title,
                "description": description,
                "icon_preset": icon,
                "category": category,
            }
            for code, title, description, icon, category in ACHIEVEMENTS
        ],
    )

    op.create_table(
        "conversation_rounds",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("round_type", sa.String(length=24), nullable=False),
        sa.Column("prompt", sa.String(length=500), nullable=False),
        sa.Column("option_a", sa.String(length=120), nullable=True),
        sa.Column("option_b", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["activity_uid"], ["space_activities.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "ix_conversation_rounds_activity_created",
        "conversation_rounds",
        ["activity_uid", "created_at"],
    )
    op.create_index(
        "uq_conversation_rounds_one_open_per_activity",
        "conversation_rounds",
        ["activity_uid"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    op.create_table(
        "conversation_round_responses",
        sa.Column("round_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("choice", sa.String(length=1), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["round_uid"], ["conversation_rounds.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("round_uid", "account_uid"),
    )
    op.create_index(
        "ix_conversation_round_responses_account",
        "conversation_round_responses",
        ["account_uid", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_round_responses_account", table_name="conversation_round_responses")
    op.drop_table("conversation_round_responses")
    op.drop_index("uq_conversation_rounds_one_open_per_activity", table_name="conversation_rounds")
    op.drop_index("ix_conversation_rounds_activity_created", table_name="conversation_rounds")
    op.drop_table("conversation_rounds")
    op.drop_index("ix_account_achievements_context_room", table_name="account_achievements")
    op.drop_index("ix_account_achievements_account_earned", table_name="account_achievements")
    op.drop_table("account_achievements")
    op.drop_table("achievement_definitions")
