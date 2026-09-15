"""space invitations

Revision ID: e91c4a7d2201
Revises: d7a4c2b91001
Create Date: 2026-09-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e91c4a7d2201"
down_revision: Union[str, None] = "d7a4c2b91001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "space_invitations",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inviter_account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invitee_account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invitee_account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("room_uid", "invitee_account_uid", name="uq_space_invitation_invitee"),
    )
    op.create_index(
        "ix_space_invitations_invitee_status",
        "space_invitations",
        ["invitee_account_uid", "status"],
        unique=False,
    )
    op.create_index(
        "ix_space_invitations_room_status",
        "space_invitations",
        ["room_uid", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_space_invitations_room_status", table_name="space_invitations")
    op.drop_index("ix_space_invitations_invitee_status", table_name="space_invitations")
    op.drop_table("space_invitations")
