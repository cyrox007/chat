"""add moderation authority levels and platform capability restrictions

Revision ID: k0a6d4f88008
Revises: k0a6d4f88007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "k0a6d4f88008"
down_revision: Union[str, None] = "k0a6d4f88007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_roles",
        sa.Column("authority_level", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("UPDATE platform_roles SET authority_level = 0 WHERE name = 'user'")
    op.execute("UPDATE platform_roles SET authority_level = 50 WHERE name = 'moderator'")
    op.execute("UPDATE platform_roles SET authority_level = 100 WHERE name = 'admin'")

    op.execute(
        """
        INSERT INTO platform_permissions (id, name, description) VALUES
            (4, 'moderation.platform.permanent', 'Issue permanent platform capability restrictions'),
            (5, 'moderation.platform.account_access', 'Restrict full platform account access')
        ON CONFLICT (id) DO UPDATE
        SET name = EXCLUDED.name, description = EXCLUDED.description
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id) VALUES
            (3, 4), (3, 5)
        ON CONFLICT DO NOTHING
        """
    )

    op.create_table(
        "platform_restrictions",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=16), nullable=False, server_default="platform"),
        sa.Column("scope_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason_code", sa.String(length=48), nullable=False),
        sa.Column("public_explanation", sa.Text(), nullable=False),
        sa.Column("origin", sa.String(length=24), nullable=False, server_default="human"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("actor_authority_level", sa.Integer(), nullable=False),
        sa.Column("target_authority_level", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["report_uid"], ["trust_safety_reports.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revoked_by_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "ix_platform_restrictions_target_active",
        "platform_restrictions",
        ["target_account_uid", "status", "capability", "expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_restrictions_report",
        "platform_restrictions",
        ["report_uid", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_restrictions_actor",
        "platform_restrictions",
        ["actor_account_uid", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_restrictions_scope",
        "platform_restrictions",
        ["scope_type", "scope_uid", "capability"],
        unique=False,
    )

    op.create_table(
        "platform_restriction_audit_events",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restriction_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_account_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["restriction_uid"], ["platform_restrictions.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_account_uid"], ["accounts.uid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "ix_platform_restriction_audit_restriction_created",
        "platform_restriction_audit_events",
        ["restriction_uid", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_restriction_audit_actor_created",
        "platform_restriction_audit_events",
        ["actor_account_uid", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_platform_restriction_audit_actor_created",
        table_name="platform_restriction_audit_events",
    )
    op.drop_index(
        "ix_platform_restriction_audit_restriction_created",
        table_name="platform_restriction_audit_events",
    )
    op.drop_table("platform_restriction_audit_events")

    op.drop_index("ix_platform_restrictions_scope", table_name="platform_restrictions")
    op.drop_index("ix_platform_restrictions_actor", table_name="platform_restrictions")
    op.drop_index("ix_platform_restrictions_report", table_name="platform_restrictions")
    op.drop_index("ix_platform_restrictions_target_active", table_name="platform_restrictions")
    op.drop_table("platform_restrictions")

    op.execute("DELETE FROM role_permissions WHERE permission_id IN (4, 5)")
    op.execute("DELETE FROM platform_permissions WHERE id IN (4, 5)")
    op.drop_column("platform_roles", "authority_level")
