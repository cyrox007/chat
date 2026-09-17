"""split platform moderation action permissions

Revision ID: k0a6d4f88010
Revises: k0a6d4f88009
"""

from typing import Sequence, Union

from alembic import op


revision: str = "k0a6d4f88010"
down_revision: Union[str, None] = "k0a6d4f88009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PERMISSION_NAMES = (
    "moderation.platform.restrict",
    "moderation.platform.revoke",
    "moderation.platform.appeal.review",
)


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO platform_permissions (name, description) VALUES
            ('moderation.platform.restrict', 'Issue non-permanent platform capability restrictions'),
            ('moderation.platform.revoke', 'Revoke platform capability restrictions within authority'),
            ('moderation.platform.appeal.review', 'Review platform restriction appeals within authority')
        ON CONFLICT (name) DO UPDATE
        SET description = EXCLUDED.description
        """
    )

    # Baseline moderator can issue/revoke ordinary restrictions and review
    # ordinary peer-level appeals. Permanent/account.access remain admin-only
    # through the existing elevated permissions.
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT role_id, permission_id
        FROM (
            SELECT 2 AS role_id, id AS permission_id
            FROM platform_permissions
            WHERE name IN (
                'moderation.platform.restrict',
                'moderation.platform.revoke',
                'moderation.platform.appeal.review'
            )
            UNION ALL
            SELECT 3 AS role_id, id AS permission_id
            FROM platform_permissions
            WHERE name IN (
                'moderation.platform.restrict',
                'moderation.platform.revoke',
                'moderation.platform.appeal.review'
            )
        ) grants
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM platform_permissions
            WHERE name IN (
                'moderation.platform.restrict',
                'moderation.platform.revoke',
                'moderation.platform.appeal.review'
            )
        )
        """
    )
    op.execute(
        """
        DELETE FROM platform_permissions
        WHERE name IN (
            'moderation.platform.restrict',
            'moderation.platform.revoke',
            'moderation.platform.appeal.review'
        )
        """
    )
