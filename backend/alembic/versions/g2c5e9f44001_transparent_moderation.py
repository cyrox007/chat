"""add transparent moderation reports actions and appeals

Revision ID: g2c5e9f44001
Revises: f4b1d8e33001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "g2c5e9f44001"
down_revision: Union[str, None] = "f4b1d8e33001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "moderation_reports",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_uid"], ["messages.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_moderation_reports_room_status", "moderation_reports", ["room_uid", "status", "created_at"])
    op.create_index("ix_moderation_reports_reporter", "moderation_reports", ["reporter_account_uid", "created_at"])
    op.create_index("ix_moderation_reports_target", "moderation_reports", ["target_account_uid", "created_at"])

    op.create_table(
        "moderation_actions",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("moderator_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("legacy_room_ban_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_uid"], ["moderation_reports.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["moderator_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["legacy_room_ban_id"], ["room_bans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_moderation_actions_room_target", "moderation_actions", ["room_uid", "target_account_uid", "created_at"])
    op.create_index("ix_moderation_actions_target_status", "moderation_actions", ["target_account_uid", "status", "created_at"])
    op.create_index("ix_moderation_actions_report", "moderation_actions", ["report_uid"])

    op.create_table(
        "moderation_appeals",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appellant_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["action_uid"], ["moderation_actions.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["appellant_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("action_uid", "appellant_account_uid", name="uq_moderation_appeal_action_appellant"),
    )
    op.create_index("ix_moderation_appeals_action_status", "moderation_appeals", ["action_uid", "status"])
    op.create_index("ix_moderation_appeals_appellant", "moderation_appeals", ["appellant_account_uid", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_moderation_appeals_appellant", table_name="moderation_appeals")
    op.drop_index("ix_moderation_appeals_action_status", table_name="moderation_appeals")
    op.drop_table("moderation_appeals")
    op.drop_index("ix_moderation_actions_report", table_name="moderation_actions")
    op.drop_index("ix_moderation_actions_target_status", table_name="moderation_actions")
    op.drop_index("ix_moderation_actions_room_target", table_name="moderation_actions")
    op.drop_table("moderation_actions")
    op.drop_index("ix_moderation_reports_target", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_reporter", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_room_status", table_name="moderation_reports")
    op.drop_table("moderation_reports")
