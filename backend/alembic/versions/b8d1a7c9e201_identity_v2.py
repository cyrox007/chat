"""identity v2

Revision ID: b8d1a7c9e201
Revises: 4f3d66790cd3
Create Date: 2026-09-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b8d1a7c9e201"
down_revision: Union[str, None] = "4f3d66790cd3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legacy_user_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("trust_level", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["legacy_user_uid"], ["users.uid"]),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("legacy_user_uid"),
    )

    op.create_table(
        "personas",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("handle", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("avatar", sa.String(length=255), nullable=True),
        sa.Column("bio", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("social_intent", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("handle"),
    )
    op.create_index("ix_personas_account_uid", "personas", ["account_uid"])
    op.create_index("ix_personas_handle", "personas", ["handle"], unique=True)
    op.create_index("ix_personas_account_primary", "personas", ["account_uid", "is_primary"])

    op.create_table(
        "credentials",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("value_normalized", sa.String(length=255), nullable=True),
        sa.Column("secret_hash", sa.String(length=255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("kind", "value_normalized", name="uq_credentials_kind_value"),
    )
    op.create_index("ix_credentials_account_uid", "credentials", ["account_uid"])
    op.create_index("ix_credentials_account_kind", "credentials", ["account_uid", "kind"])

    op.create_table(
        "identity_sessions",
        sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("device_label", sa.String(length=120), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("refresh_token_hash"),
    )
    op.create_index("ix_identity_sessions_account_uid", "identity_sessions", ["account_uid"])
    op.create_index("ix_identity_sessions_refresh_token_hash", "identity_sessions", ["refresh_token_hash"], unique=True)

    op.create_table(
        "privacy_settings",
        sa.Column("persona_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_visibility", sa.String(length=24), nullable=False, server_default="public"),
        sa.Column("dm_policy", sa.String(length=32), nullable=False, server_default="shared_spaces"),
        sa.Column("show_last_seen", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_age", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("show_location", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["persona_uid"], ["personas.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("persona_uid"),
    )

    op.create_table(
        "platform_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "platform_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=96), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "account_roles",
        sa.Column("account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["platform_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_uid", "role_id"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["platform_permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["platform_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_table(
        "account_relationships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_account_uid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["from_account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_account_uid"], ["accounts.uid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_account_uid", "to_account_uid", "relation_type", name="uq_account_relationship"),
    )
    op.create_index("ix_account_relationship_from", "account_relationships", ["from_account_uid", "relation_type"])
    op.create_index("ix_account_relationship_to", "account_relationships", ["to_account_uid", "relation_type"])

    # Existing users become one Account + one primary Persona without changing their legacy UID.
    op.execute("""
        INSERT INTO accounts (uid, legacy_user_uid, status, trust_level, created_at, updated_at, deleted_at)
        SELECT uid, uid,
               CASE WHEN is_active IS FALSE THEN 'suspended' ELSE 'active' END,
               CASE WHEN is_verified IS TRUE THEN 'established' ELSE 'new' END,
               COALESCE(created_at, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP, deleted_at
        FROM users
        WHERE uid IS NOT NULL
        ON CONFLICT (uid) DO NOTHING
    """)
    op.execute("""
        INSERT INTO personas (
            uid, account_uid, handle, display_name, avatar, bio, city, country,
            date_of_birth, gender, social_intent, is_primary, created_at, updated_at
        )
        SELECT uid, uid, username,
               COALESCE(NULLIF(TRIM(CONCAT_WS(' ', first_name, last_name)), ''), username),
               avatar, bio, city, country, date_of_birth::date, gender,
               'open', TRUE, COALESCE(created_at, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP
        FROM users
        WHERE uid IS NOT NULL AND username IS NOT NULL
        ON CONFLICT (uid) DO NOTHING
    """)
    op.execute("""
        INSERT INTO privacy_settings (persona_uid)
        SELECT uid FROM personas
        ON CONFLICT (persona_uid) DO NOTHING
    """)

    # Deterministic UUIDs avoid requiring pgcrypto/uuid-ossp extensions during migration.
    op.execute("""
        INSERT INTO credentials (uid, account_uid, kind, value_normalized, secret_hash, is_primary, verified_at)
        SELECT (
            SUBSTR(MD5(uid::text || ':password'), 1, 8) || '-' ||
            SUBSTR(MD5(uid::text || ':password'), 9, 4) || '-' ||
            SUBSTR(MD5(uid::text || ':password'), 13, 4) || '-' ||
            SUBSTR(MD5(uid::text || ':password'), 17, 4) || '-' ||
            SUBSTR(MD5(uid::text || ':password'), 21, 12)
        )::uuid, uid, 'password', NULL, hashed_password, TRUE, NULL
        FROM users
        WHERE uid IS NOT NULL AND hashed_password IS NOT NULL
    """)
    op.execute("""
        INSERT INTO credentials (uid, account_uid, kind, value_normalized, secret_hash, is_primary, verified_at)
        SELECT (
            SUBSTR(MD5(uid::text || ':email'), 1, 8) || '-' ||
            SUBSTR(MD5(uid::text || ':email'), 9, 4) || '-' ||
            SUBSTR(MD5(uid::text || ':email'), 13, 4) || '-' ||
            SUBSTR(MD5(uid::text || ':email'), 17, 4) || '-' ||
            SUBSTR(MD5(uid::text || ':email'), 21, 12)
        )::uuid, uid, 'email', LOWER(TRIM(email)), NULL, TRUE,
        CASE WHEN is_verified IS TRUE THEN CURRENT_TIMESTAMP ELSE NULL END
        FROM users
        WHERE uid IS NOT NULL AND email IS NOT NULL AND TRIM(email) <> ''
    """)
    op.execute("""
        INSERT INTO credentials (uid, account_uid, kind, value_normalized, secret_hash, is_primary, verified_at)
        SELECT (
            SUBSTR(MD5(uid::text || ':phone'), 1, 8) || '-' ||
            SUBSTR(MD5(uid::text || ':phone'), 9, 4) || '-' ||
            SUBSTR(MD5(uid::text || ':phone'), 13, 4) || '-' ||
            SUBSTR(MD5(uid::text || ':phone'), 17, 4) || '-' ||
            SUBSTR(MD5(uid::text || ':phone'), 21, 12)
        )::uuid, uid, 'phone', REGEXP_REPLACE(phone, '[^0-9+]', '', 'g'), NULL, FALSE, NULL
        FROM users
        WHERE uid IS NOT NULL AND phone IS NOT NULL AND TRIM(phone) <> ''
    """)

    op.execute("""
        INSERT INTO platform_roles (id, name, description) VALUES
            (1, 'user', 'Default platform member'),
            (2, 'moderator', 'Platform trust and safety moderator'),
            (3, 'admin', 'Platform administrator')
        ON CONFLICT (id) DO NOTHING
    """)
    op.execute("""
        INSERT INTO platform_permissions (id, name, description) VALUES
            (1, 'admin.dashboard.read', 'Read platform administration dashboard'),
            (2, 'admin.accounts.manage', 'Manage platform accounts'),
            (3, 'moderation.platform.manage', 'Apply platform-level safety actions')
        ON CONFLICT (id) DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id) VALUES
            (2, 3), (3, 1), (3, 2), (3, 3)
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO account_roles (account_uid, role_id)
        SELECT a.uid,
               CASE
                   WHEN LOWER(COALESCE(u.global_role, 'user')) IN ('admin', 'superadmin') THEN 3
                   WHEN LOWER(COALESCE(u.global_role, 'user')) = 'moderator' THEN 2
                   ELSE 1
               END
        FROM accounts a
        JOIN users u ON u.uid = a.legacy_user_uid
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("ix_account_relationship_to", table_name="account_relationships")
    op.drop_index("ix_account_relationship_from", table_name="account_relationships")
    op.drop_table("account_relationships")
    op.drop_table("role_permissions")
    op.drop_table("account_roles")
    op.drop_table("platform_permissions")
    op.drop_table("platform_roles")
    op.drop_table("privacy_settings")
    op.drop_index("ix_identity_sessions_refresh_token_hash", table_name="identity_sessions")
    op.drop_index("ix_identity_sessions_account_uid", table_name="identity_sessions")
    op.drop_table("identity_sessions")
    op.drop_index("ix_credentials_account_kind", table_name="credentials")
    op.drop_index("ix_credentials_account_uid", table_name="credentials")
    op.drop_table("credentials")
    op.drop_index("ix_personas_account_primary", table_name="personas")
    op.drop_index("ix_personas_handle", table_name="personas")
    op.drop_index("ix_personas_account_uid", table_name="personas")
    op.drop_table("personas")
    op.drop_table("accounts")
