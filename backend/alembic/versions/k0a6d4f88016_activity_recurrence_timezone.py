"""add activity recurrence timezone

Revision ID: k0a6d4f88016
Revises: k0a6d4f88015
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k0a6d4f88016"
down_revision: Union[str, None] = "k0a6d4f88015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "space_activities",
        sa.Column(
            "timezone_name",
            sa.String(length=64),
            nullable=False,
            server_default="UTC",
        ),
    )


def downgrade() -> None:
    op.drop_column("space_activities", "timezone_name")
