"""add platform Trust & Safety intake queue and audit trail

Revision ID: k0a6d4f88007
Revises: k0a6d4f88006
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88007"
down_revision: Union[str, None] = "k0a6d4f88006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trust_safety_reports",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_room_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="triage"),
        sa.Column("assigned_to_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("duplicate_of_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_code", sa.String(length=48), nullable=True),
        sa.Column("public_explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["reporter_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_room_uid"], ["rooms.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["duplicate_of_uid"], ["trust_safety_reports.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "ix_trust_safety_queue",
        "trust_safety_reports",
        ["status", "priority", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_trust_safety_assignee",
        "trust_safety_reports",
        ["assigned_to_account_uid", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_trust_safety_reporter",
        "trust_safety_reports",
        ["reporter_account_uid", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_trust_safety_target",
        "trust_safety_reports",
        ["target_account_uid", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_trust_safety_source",
        "trust_safety_reports",
        ["source_type", "source_uid", "created_at"],
        unique=False,
    )

    op.create_table(
        "trust_safety_audit_events",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("previous_status", sa.String(length=24), nullable=True),
        sa.Column("next_status", sa.String(length=24), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["report_uid"], ["trust_safety_reports.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "ix_trust_safety_audit_report_created",
        "trust_safety_audit_events",
        ["report_uid", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_trust_safety_audit_actor_created",
        "trust_safety_audit_events",
        ["actor_account_uid", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_trust_safety_audit_actor_created", table_name="trust_safety_audit_events")
    op.drop_index("ix_trust_safety_audit_report_created", table_name="trust_safety_audit_events")
    op.drop_table("trust_safety_audit_events")

    op.drop_index("ix_trust_safety_source", table_name="trust_safety_reports")
    op.drop_index("ix_trust_safety_target", table_name="trust_safety_reports")
    op.drop_index("ix_trust_safety_reporter", table_name="trust_safety_reports")
    op.drop_index("ix_trust_safety_assignee", table_name="trust_safety_reports")
    op.drop_index("ix_trust_safety_queue", table_name="trust_safety_reports")
    op.drop_table("trust_safety_reports")
