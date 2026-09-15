"""add space rules events and history

Revision ID: f4b1d8e33001
Revises: e91c4a7d2201
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f4b1d8e33001"
down_revision: Union[str, None] = "e91c4a7d2201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "space_rules",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_space_rules_room_position", "space_rules", ["room_uid", "position", "created_at"])

    op.create_table(
        "space_events",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_space_events_room_start", "space_events", ["room_uid", "starts_at"])
    op.create_index("ix_space_events_room_status", "space_events", ["room_uid", "status"])

    op.create_table(
        "space_history",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_space_history_room_created", "space_history", ["room_uid", "created_at"])
    op.create_index("ix_space_history_room_type", "space_history", ["room_uid", "event_type"])


def downgrade() -> None:
    op.drop_index("ix_space_history_room_type", table_name="space_history")
    op.drop_index("ix_space_history_room_created", table_name="space_history")
    op.drop_table("space_history")
    op.drop_index("ix_space_events_room_status", table_name="space_events")
    op.drop_index("ix_space_events_room_start", table_name="space_events")
    op.drop_table("space_events")
    op.drop_index("ix_space_rules_room_position", table_name="space_rules")
    op.drop_table("space_rules")
