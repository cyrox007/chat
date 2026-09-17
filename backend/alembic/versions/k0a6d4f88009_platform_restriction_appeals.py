"""add appeals for platform capability restrictions

Revision ID: k0a6d4f88009
Revises: k0a6d4f88008
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88009"
down_revision: Union[str, None] = "k0a6d4f88008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_restriction_appeals",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restriction_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appellant_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["restriction_uid"], ["platform_restrictions.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["appellant_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint(
            "restriction_uid",
            "appellant_account_uid",
            name="uq_platform_restriction_appeal_appellant",
        ),
    )
    op.create_index(
        "ix_platform_restriction_appeals_status_created",
        "platform_restriction_appeals",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_restriction_appeals_appellant_created",
        "platform_restriction_appeals",
        ["appellant_account_uid", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_platform_restriction_appeals_appellant_created",
        table_name="platform_restriction_appeals",
    )
    op.drop_index(
        "ix_platform_restriction_appeals_status_created",
        table_name="platform_restriction_appeals",
    )
    op.drop_table("platform_restriction_appeals")
