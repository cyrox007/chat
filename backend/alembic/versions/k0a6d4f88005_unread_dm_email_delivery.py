"""add durable unread DM email delivery ledger

Revision ID: k0a6d4f88005
Revises: k0a6d4f88004
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88005"
down_revision: Union[str, None] = "k0a6d4f88004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

WORKER_NAME = "unread-dm-email-nudge"


def upgrade() -> None:
    op.create_table(
        "external_delivery_ledger",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("aggregate_key", sa.String(length=180), nullable=False),
        sa.Column("dedupe_key", sa.String(length=220), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dialog_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("provider_message_id", sa.String(length=180), nullable=True),
        sa.Column("failure_class", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("account_uid", "channel", "dedupe_key", name="uq_external_delivery_dedupe"),
    )
    op.create_index(
        "ix_external_delivery_pending",
        "external_delivery_ledger",
        ["channel", "status", "next_attempt_at", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_external_delivery_account_created",
        "external_delivery_ledger",
        ["account_uid", "created_at"],
        unique=False,
    )
    op.execute(
        sa.text(
            "INSERT INTO notification_worker_state (worker_name, cursor_account_uid) "
            "VALUES (:worker_name, NULL) ON CONFLICT (worker_name) DO NOTHING"
        ).bindparams(worker_name=WORKER_NAME)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM notification_worker_state WHERE worker_name = :worker_name")
        .bindparams(worker_name=WORKER_NAME)
    )
    op.drop_index("ix_external_delivery_account_created", table_name="external_delivery_ledger")
    op.drop_index("ix_external_delivery_pending", table_name="external_delivery_ledger")
    op.drop_table("external_delivery_ledger")
