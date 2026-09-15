"""add durable notification worker cursor

Revision ID: k0a6d4f88003
Revises: k0a6d4f88002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88003"
down_revision: Union[str, None] = "k0a6d4f88002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WORKER_NAME = "activity-reminders"


def upgrade() -> None:
    op.create_table(
        "notification_worker_state",
        sa.Column("worker_name", sa.String(length=64), nullable=False),
        sa.Column("cursor_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("worker_name"),
    )
    op.execute(
        sa.text(
            "INSERT INTO notification_worker_state (worker_name, cursor_account_uid) "
            "VALUES (:worker_name, NULL)"
        ).bindparams(worker_name=WORKER_NAME)
    )


def downgrade() -> None:
    op.drop_table("notification_worker_state")
