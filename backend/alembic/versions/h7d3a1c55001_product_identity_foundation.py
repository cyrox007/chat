"""add persona/space appearance and recurring activities

Revision ID: h7d3a1c55001
Revises: g2c5e9f44001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "h7d3a1c55001"
down_revision: Union[str, None] = "g2c5e9f44001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "persona_appearance",
        sa.Column("persona_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accent_preset", sa.String(length=32), nullable=False, server_default="plum"),
        sa.Column("background_preset", sa.String(length=32), nullable=False, server_default="soft"),
        sa.Column("avatar_frame_preset", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column("status_line", sa.String(length=120), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["persona_uid"], ["personas.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("persona_uid"),
    )

    op.create_table(
        "space_appearance",
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("theme_preset", sa.String(length=32), nullable=False, server_default="lounge"),
        sa.Column("cover_preset", sa.String(length=32), nullable=False, server_default="soft-gradient"),
        sa.Column("ambient_icon", sa.String(length=16), nullable=True),
        sa.Column("welcome_line", sa.String(length=160), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("room_uid"),
    )

    op.create_table(
        "space_activities",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("activity_type", sa.String(length=32), nullable=False, server_default="hangout"),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("recurrence", sa.String(length=24), nullable=False, server_default="none"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_space_activities_room_start", "space_activities", ["room_uid", "starts_at"])
    op.create_index("ix_space_activities_room_status", "space_activities", ["room_uid", "status"])

    op.create_table(
        "activity_rsvps",
        sa.Column("activity_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["activity_uid"], ["space_activities.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("activity_uid", "account_uid"),
        sa.UniqueConstraint("activity_uid", "account_uid", name="uq_activity_rsvp"),
    )
    op.create_index("ix_activity_rsvps_account", "activity_rsvps", ["account_uid", "status"])


def downgrade() -> None:
    op.drop_index("ix_activity_rsvps_account", table_name="activity_rsvps")
    op.drop_table("activity_rsvps")
    op.drop_index("ix_space_activities_room_status", table_name="space_activities")
    op.drop_index("ix_space_activities_room_start", table_name="space_activities")
    op.drop_table("space_activities")
    op.drop_table("space_appearance")
    op.drop_table("persona_appearance")
