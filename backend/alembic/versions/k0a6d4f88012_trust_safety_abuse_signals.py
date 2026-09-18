"""add durable Trust & Safety abuse signals

Revision ID: k0a6d4f88012
Revises: k0a6d4f88011
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88012"
down_revision: Union[str, None] = "k0a6d4f88011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trust_safety_abuse_signals",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("surface", sa.String(length=32), nullable=False),
        sa.Column("scope_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("observed_count", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=96), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("dedupe_key", name="uq_trust_safety_abuse_signal_dedupe"),
    )
    op.create_index(
        "ix_trust_safety_abuse_signal_queue",
        "trust_safety_abuse_signals",
        ["status", "severity", "last_seen_at"],
        unique=False,
    )
    op.create_index(
        "ix_trust_safety_abuse_signal_account",
        "trust_safety_abuse_signals",
        ["account_uid", "last_seen_at"],
        unique=False,
    )
    op.create_index(
        "ix_trust_safety_abuse_signal_type",
        "trust_safety_abuse_signals",
        ["signal_type", "last_seen_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_trust_safety_abuse_signal_type", table_name="trust_safety_abuse_signals")
    op.drop_index("ix_trust_safety_abuse_signal_account", table_name="trust_safety_abuse_signals")
    op.drop_index("ix_trust_safety_abuse_signal_queue", table_name="trust_safety_abuse_signals")
    op.drop_table("trust_safety_abuse_signals")
