"""add message notification preferences

Revision ID: k0a6d4f88004
Revises: k0a6d4f88003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88004"
down_revision: Union[str, None] = "k0a6d4f88003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_notification_preferences",
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("messenger_in_app", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("space_in_app", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("messenger_sound", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("space_sound", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email_unread_dm_nudge", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("web_push_messenger", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("web_push_space", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_uid"),
    )


def downgrade() -> None:
    op.drop_table("message_notification_preferences")
