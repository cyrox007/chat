"""add protective hold calibration ledger

Revision ID: k0a6d4f88015
Revises: k0a6d4f88014
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88015"
down_revision: Union[str, None] = "k0a6d4f88014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trust_safety_abuse_signals",
        sa.Column("calibration_label", sa.String(length=24), nullable=True),
    )
    op.create_table(
        "protective_hold_evaluations",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("decision", sa.String(length=48), nullable=False),
        sa.Column("would_hold", sa.Boolean(), nullable=False),
        sa.Column("corroboration_count", sa.Integer(), nullable=False),
        sa.Column("min_high_signals", sa.Integer(), nullable=False),
        sa.Column("lookback_seconds", sa.Integer(), nullable=False),
        sa.Column("hold_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["signal_uid"],
            ["trust_safety_abuse_signals.uid"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["account_uid"],
            ["accounts.uid"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint(
            "signal_uid",
            name="uq_protective_hold_evaluation_signal",
        ),
    )
    op.create_index(
        "ix_protective_hold_evaluation_calibration",
        "protective_hold_evaluations",
        ["signal_type", "would_hold", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_protective_hold_evaluation_account",
        "protective_hold_evaluations",
        ["account_uid", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_protective_hold_evaluation_account",
        table_name="protective_hold_evaluations",
    )
    op.drop_index(
        "ix_protective_hold_evaluation_calibration",
        table_name="protective_hold_evaluations",
    )
    op.drop_table("protective_hold_evaluations")
    op.drop_column("trust_safety_abuse_signals", "calibration_label")
