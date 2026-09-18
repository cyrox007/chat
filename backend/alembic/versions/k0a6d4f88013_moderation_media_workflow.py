"""add moderation media workflow

Revision ID: k0a6d4f88013
Revises: k0a6d4f88012
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88013"
down_revision: Union[str, None] = "k0a6d4f88012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PERMISSION = "moderation.platform.media.manage"


def upgrade() -> None:
    op.create_table(
        "moderation_media_records",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attachment_index", sa.Integer(), nullable=False),
        sa.Column("target_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_url", sa.String(length=512), nullable=False),
        sa.Column("original_relative_path", sa.String(length=512), nullable=False),
        sa.Column("private_relative_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("original_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("restored_at", sa.DateTime(), nullable=True),
        sa.Column("removed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["report_uid"], ["trust_safety_reports.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint(
            "report_uid",
            "source_uid",
            "attachment_index",
            name="uq_moderation_media_report_attachment",
        ),
    )
    op.create_index(
        "ix_moderation_media_report_status",
        "moderation_media_records",
        ["report_uid", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_moderation_media_target_created",
        "moderation_media_records",
        ["target_account_uid", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_moderation_media_actor_created",
        "moderation_media_records",
        ["actor_account_uid", "created_at"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO platform_permissions (name, description)
        VALUES ('moderation.platform.media.manage', 'Quarantine, restore and remove reported media')
        ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT role_id, permission_id
        FROM (
            SELECT 2 AS role_id, id AS permission_id
            FROM platform_permissions WHERE name = 'moderation.platform.media.manage'
            UNION ALL
            SELECT 3 AS role_id, id AS permission_id
            FROM platform_permissions WHERE name = 'moderation.platform.media.manage'
        ) grants
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM platform_permissions WHERE name = 'moderation.platform.media.manage'
        )
        """
    )
    op.execute(
        "DELETE FROM platform_permissions WHERE name = 'moderation.platform.media.manage'"
    )
    op.drop_index("ix_moderation_media_actor_created", table_name="moderation_media_records")
    op.drop_index("ix_moderation_media_target_created", table_name="moderation_media_records")
    op.drop_index("ix_moderation_media_report_status", table_name="moderation_media_records")
    op.drop_table("moderation_media_records")
