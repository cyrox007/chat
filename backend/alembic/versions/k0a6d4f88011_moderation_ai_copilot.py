"""add durable moderation AI recommendations

Revision ID: k0a6d4f88011
Revises: k0a6d4f88010
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88011"
down_revision: Union[str, None] = "k0a6d4f88010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "moderation_ai_recommendations",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_key", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("confidence_percent", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.String(length=32), nullable=False),
        sa.Column("suggested_capability", sa.String(length=64), nullable=True),
        sa.Column("suggested_scope_type", sa.String(length=16), nullable=False),
        sa.Column("suggested_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("outcome_note", sa.Text(), nullable=True),
        sa.Column("outcome_by_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_uid"],
            ["trust_safety_reports.uid"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_account_uid"],
            ["accounts.uid"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["outcome_by_account_uid"],
            ["accounts.uid"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "ix_moderation_ai_report_created",
        "moderation_ai_recommendations",
        ["report_uid", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_moderation_ai_outcome_created",
        "moderation_ai_recommendations",
        ["outcome", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_moderation_ai_requester_created",
        "moderation_ai_recommendations",
        ["requested_by_account_uid", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_moderation_ai_requester_created",
        table_name="moderation_ai_recommendations",
    )
    op.drop_index(
        "ix_moderation_ai_outcome_created",
        table_name="moderation_ai_recommendations",
    )
    op.drop_index(
        "ix_moderation_ai_report_created",
        table_name="moderation_ai_recommendations",
    )
    op.drop_table("moderation_ai_recommendations")
