"""living spaces foundation

Revision ID: d7a4c2b91001
Revises: c3e7b26a1f10
Create Date: 2026-09-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d7a4c2b91001"
down_revision: Union[str, None] = "c3e7b26a1f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "space_settings",
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False, server_default="community"),
        sa.Column("visibility", sa.String(length=24), nullable=False, server_default="public"),
        sa.Column("join_policy", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("member_limit", sa.Integer(), nullable=False, server_default="250"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("room_uid"),
    )

    op.create_table(
        "space_memberships",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False, server_default="member"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("joined_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("room_uid", "account_uid", name="uq_space_membership"),
    )
    op.create_index(
        "ix_space_memberships_account_status",
        "space_memberships",
        ["account_uid", "status"],
        unique=False,
    )
    op.create_index(
        "ix_space_memberships_room_role",
        "space_memberships",
        ["room_uid", "role", "status"],
        unique=False,
    )

    op.create_table(
        "space_tags",
        sa.Column("room_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["room_uid"], ["rooms.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("room_uid", "slug"),
    )
    op.create_index("ix_space_tags_slug", "space_tags", ["slug"], unique=False)

    # Every legacy room becomes a public/open Space by default. Product settings
    # can then evolve without changing the message/room foreign-key backbone.
    op.execute(
        """
        INSERT INTO space_settings (room_uid, purpose, visibility, join_policy, member_limit, created_at, updated_at)
        SELECT uid, 'community', 'public', 'open', 250,
               COALESCE(created_at, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP
        FROM rooms
        ON CONFLICT (room_uid) DO NOTHING
        """
    )

    # Owner membership is canonical and scoped to a Space. Account UID remains
    # separate from the legacy users FK even though current backfilled accounts
    # intentionally share the same UUID.
    op.execute(
        """
        INSERT INTO space_memberships (uid, room_uid, account_uid, role, status, joined_at, updated_at)
        SELECT md5(r.uid::text || ':' || a.uid::text)::uuid,
               r.uid,
               a.uid,
               'owner',
               'active',
               COALESCE(r.created_at, CURRENT_TIMESTAMP),
               CURRENT_TIMESTAMP
        FROM rooms r
        JOIN accounts a
          ON a.legacy_user_uid = r.owner_uid OR a.uid = r.owner_uid
        ON CONFLICT (room_uid, account_uid)
        DO UPDATE SET role = 'owner', status = 'active', updated_at = CURRENT_TIMESTAMP
        """
    )

    # Collapse duplicate legacy room_members rows into one account membership.
    # Active restrictions stay restrictions and are not promoted to active members.
    op.execute(
        """
        WITH normalized AS (
            SELECT
                rm.room_uid,
                a.uid AS account_uid,
                CASE WHEN bool_or(rm.role = 'moderator') THEN 'moderator' ELSE 'member' END AS role,
                MIN(COALESCE(rm.joined_at, CURRENT_TIMESTAMP)) AS joined_at
            FROM room_members rm
            JOIN accounts a
              ON a.legacy_user_uid = rm.user_uid OR a.uid = rm.user_uid
            WHERE COALESCE(rm.is_banned, false) = false
              AND NOT EXISTS (
                  SELECT 1
                  FROM room_bans rb
                  WHERE rb.room_uid = rm.room_uid
                    AND rb.user_uid = rm.user_uid
                    AND rb.is_active = true
                    AND (rb.expires_at IS NULL OR rb.expires_at > CURRENT_TIMESTAMP)
              )
            GROUP BY rm.room_uid, a.uid
        )
        INSERT INTO space_memberships (uid, room_uid, account_uid, role, status, joined_at, updated_at)
        SELECT md5(n.room_uid::text || ':' || n.account_uid::text)::uuid,
               n.room_uid,
               n.account_uid,
               n.role,
               'active',
               n.joined_at,
               CURRENT_TIMESTAMP
        FROM normalized n
        ON CONFLICT (room_uid, account_uid)
        DO UPDATE SET
            role = CASE
                WHEN space_memberships.role = 'owner' THEN 'owner'
                WHEN EXCLUDED.role = 'moderator' THEN 'moderator'
                ELSE space_memberships.role
            END,
            status = 'active',
            joined_at = LEAST(space_memberships.joined_at, EXCLUDED.joined_at),
            updated_at = CURRENT_TIMESTAMP
        """
    )

    # Normalize comma-separated legacy tags into a queryable relation. Legacy
    # rooms.tags remains populated during the compatibility phase.
    op.execute(
        r"""
        INSERT INTO space_tags (room_uid, slug, label, created_at)
        SELECT DISTINCT
            r.uid,
            LEFT(
                TRIM(BOTH '-' FROM regexp_replace(lower(trim(raw_tag)), '[^[:alnum:]_-]+', '-', 'g')),
                64
            ) AS slug,
            LEFT(trim(raw_tag), 64) AS label,
            COALESCE(r.created_at, CURRENT_TIMESTAMP)
        FROM rooms r
        CROSS JOIN LATERAL regexp_split_to_table(COALESCE(r.tags, ''), ',') AS raw_tag
        WHERE trim(raw_tag) <> ''
          AND TRIM(BOTH '-' FROM regexp_replace(lower(trim(raw_tag)), '[^[:alnum:]_-]+', '-', 'g')) <> ''
        ON CONFLICT (room_uid, slug) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_space_tags_slug", table_name="space_tags")
    op.drop_table("space_tags")
    op.drop_index("ix_space_memberships_room_role", table_name="space_memberships")
    op.drop_index("ix_space_memberships_account_status", table_name="space_memberships")
    op.drop_table("space_memberships")
    op.drop_table("space_settings")
