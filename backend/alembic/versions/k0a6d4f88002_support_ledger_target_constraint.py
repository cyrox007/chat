"""enforce compatible target shape for support ledger

Revision ID: k0a6d4f88002
Revises: k0a6d4f88001
"""

from typing import Sequence, Union

from alembic import op


revision: str = "k0a6d4f88002"
down_revision: Union[str, None] = "k0a6d4f88001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_support_ledger_exact_target",
        "support_ledger_entries",
        "(target_kind = 'persona' AND target_room_uid IS NULL) OR "
        "(target_kind = 'space' AND target_persona_uid IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_support_ledger_exact_target",
        "support_ledger_entries",
        type_="check",
    )
