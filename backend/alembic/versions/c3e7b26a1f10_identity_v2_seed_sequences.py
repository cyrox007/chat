"""identity v2 seed sequence sync

Revision ID: c3e7b26a1f10
Revises: b8d1a7c9e201
Create Date: 2026-09-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c3e7b26a1f10"
down_revision: Union[str, None] = "b8d1a7c9e201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The previous migration seeds stable role/permission IDs explicitly. Keep
    # PostgreSQL sequences ahead of those rows so later inserts cannot collide.
    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('platform_roles', 'id'),
            GREATEST(COALESCE((SELECT MAX(id) FROM platform_roles), 1), 1),
            true
        )
    """)
    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('platform_permissions', 'id'),
            GREATEST(COALESCE((SELECT MAX(id) FROM platform_permissions), 1), 1),
            true
        )
    """)


def downgrade() -> None:
    # Sequence position is operational state and intentionally not rewound.
    pass
