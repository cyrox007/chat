"""add moderation media retention lifecycle

Revision ID: k0a6d4f88014
Revises: k0a6d4f88013
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k0a6d4f88014"
down_revision: Union[str, None] = "k0a6d4f88013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "moderation_media_records",
        "original_url",
        existing_type=sa.String(length=512),
        nullable=True,
    )
    op.alter_column(
        "moderation_media_records",
        "original_relative_path",
        existing_type=sa.String(length=512),
        nullable=True,
    )
    op.alter_column(
        "moderation_media_records",
        "private_relative_path",
        existing_type=sa.String(length=512),
        nullable=True,
    )
    op.add_column(
        "moderation_media_records",
        sa.Column("retention_due_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "moderation_media_records",
        sa.Column("purged_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_moderation_media_retention_due",
        "moderation_media_records",
        ["status", "purged_at", "retention_due_at"],
        unique=False,
    )

    # Existing removed evidence receives the same baseline used by the new code.
    # Active/quarantined records intentionally remain without a due date.
    op.execute(
        """
        UPDATE moderation_media_records
        SET retention_due_at = removed_at + INTERVAL '90 days'
        WHERE status = 'removed'
          AND removed_at IS NOT NULL
          AND retention_due_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_moderation_media_retention_due",
        table_name="moderation_media_records",
    )
    op.drop_column("moderation_media_records", "purged_at")
    op.drop_column("moderation_media_records", "retention_due_at")

    # A downgrade cannot reconstruct expired bytes/paths. Preserve row shape for
    # the previous schema using explicit non-sensitive placeholders.
    op.execute(
        """
        UPDATE moderation_media_records
        SET original_url = COALESCE(original_url, '/uploads/[expired]'),
            original_relative_path = COALESCE(original_relative_path, '[expired]'),
            private_relative_path = COALESCE(private_relative_path, '[expired]')
        """
    )
    op.alter_column(
        "moderation_media_records",
        "private_relative_path",
        existing_type=sa.String(length=512),
        nullable=False,
    )
    op.alter_column(
        "moderation_media_records",
        "original_relative_path",
        existing_type=sa.String(length=512),
        nullable=False,
    )
    op.alter_column(
        "moderation_media_records",
        "original_url",
        existing_type=sa.String(length=512),
        nullable=False,
    )
