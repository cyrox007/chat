"""add bounded activity occurrences and private notifications

Revision ID: j9f5c3e77001
Revises: i8e4b2d66001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "j9f5c3e77001"
down_revision: Union[str, None] = "i8e4b2d66001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_occurrences",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["activity_uid"], ["space_activities.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("activity_uid", "starts_at", name="uq_activity_occurrence_start"),
    )
    op.create_index(
        "ix_activity_occurrences_start_status",
        "activity_occurrences",
        ["starts_at", "status"],
    )
    op.create_index(
        "ix_activity_occurrences_activity_start",
        "activity_occurrences",
        ["activity_uid", "starts_at"],
    )

    op.create_table(
        "activity_reminder_preferences",
        sa.Column("activity_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["activity_uid"], ["space_activities.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("activity_uid", "account_uid"),
    )
    op.create_index(
        "ix_activity_reminders_account_enabled",
        "activity_reminder_preferences",
        ["account_uid", "enabled"],
    )

    op.create_table(
        "user_notifications",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("dedupe_key", sa.String(length=180), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=False),
        sa.Column("context_room_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activity_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("occurrence_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["context_room_uid"], ["rooms.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["activity_uid"], ["space_activities.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["occurrence_uid"], ["activity_occurrences.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("account_uid", "kind", "dedupe_key", name="uq_user_notification_dedupe"),
    )
    op.create_index(
        "ix_user_notifications_account_created",
        "user_notifications",
        ["account_uid", "created_at"],
    )
    op.create_index(
        "ix_user_notifications_account_unread",
        "user_notifications",
        ["account_uid", "read_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_notifications_account_unread", table_name="user_notifications")
    op.drop_index("ix_user_notifications_account_created", table_name="user_notifications")
    op.drop_table("user_notifications")
    op.drop_index("ix_activity_reminders_account_enabled", table_name="activity_reminder_preferences")
    op.drop_table("activity_reminder_preferences")
    op.drop_index("ix_activity_occurrences_activity_start", table_name="activity_occurrences")
    op.drop_index("ix_activity_occurrences_start_status", table_name="activity_occurrences")
    op.drop_table("activity_occurrences")
