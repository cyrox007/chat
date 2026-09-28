"""add discovery candidate source indexes

Revision ID: k0a6d4f88017
Revises: k0a6d4f88016
"""

from typing import Sequence, Union

from alembic import op


revision: str = "k0a6d4f88017"
down_revision: Union[str, None] = "k0a6d4f88016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_messages_discovery_recent",
        "messages",
        ["created_at", "room_uid", "author_uid"],
        unique=False,
    )
    op.create_index(
        "ix_rooms_discovery_active_created",
        "rooms",
        ["is_active", "created_at", "uid"],
        unique=False,
    )
    op.create_index(
        "ix_space_settings_purpose_updated",
        "space_settings",
        ["purpose", "updated_at", "room_uid"],
        unique=False,
    )
    op.create_index(
        "ix_space_events_status_start",
        "space_events",
        ["status", "starts_at", "room_uid"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_space_events_status_start", table_name="space_events")
    op.drop_index("ix_space_settings_purpose_updated", table_name="space_settings")
    op.drop_index("ix_rooms_discovery_active_created", table_name="rooms")
    op.drop_index("ix_messages_discovery_recent", table_name="messages")
