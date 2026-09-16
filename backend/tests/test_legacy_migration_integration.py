import os
import unittest
from uuid import UUID

import psycopg2


OWNER_UID = UUID("11111111-1111-1111-1111-111111111111")
MEMBER_UID = UUID("22222222-2222-2222-2222-222222222222")
BANNED_UID = UUID("33333333-3333-3333-3333-333333333333")
ROOM_UID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def connection_kwargs() -> dict:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("PUBCHAT_LEGACY_DB_NAME", "chat_legacy_ci"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
    }


@unittest.skipUnless(
    os.getenv("PUBCHAT_LEGACY_MIGRATION_INTEGRATION") == "1",
    "Legacy migration rehearsal environment is not enabled",
)
class LegacyMigrationIntegrationTests(unittest.TestCase):
    def test_identity_and_space_backfill_preserves_semantics(self):
        with psycopg2.connect(**connection_kwargs()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM accounts")
                self.assertEqual(cursor.fetchone()[0], 3)

                cursor.execute(
                    "SELECT legacy_user_uid, status FROM accounts WHERE uid = %s::uuid",
                    (str(OWNER_UID),),
                )
                self.assertEqual(cursor.fetchone(), (OWNER_UID, "active"))

                cursor.execute(
                    "SELECT account_uid, handle, display_name, is_primary FROM personas WHERE uid = %s::uuid",
                    (str(OWNER_UID),),
                )
                account_uid, handle, display_name, is_primary = cursor.fetchone()
                self.assertEqual(account_uid, OWNER_UID)
                self.assertEqual(handle, "legacy_owner")
                self.assertEqual(display_name, "Alex Owner")
                self.assertTrue(is_primary)

                cursor.execute(
                    """
                    SELECT kind, value_normalized, secret_hash, is_primary
                    FROM credentials
                    WHERE account_uid = %s::uuid
                    ORDER BY kind
                    """,
                    (str(OWNER_UID),),
                )
                credentials = {row[0]: row[1:] for row in cursor.fetchall()}
                self.assertEqual(credentials["email"][0], "owner@example.com")
                self.assertEqual(credentials["phone"][0], "+491701234567")
                self.assertEqual(credentials["password"][1], "legacy-password-hash-owner")
                self.assertTrue(credentials["password"][2])

                cursor.execute(
                    """
                    SELECT pr.name
                    FROM account_roles ar
                    JOIN platform_roles pr ON pr.id = ar.role_id
                    WHERE ar.account_uid = %s::uuid
                    """,
                    (str(OWNER_UID),),
                )
                self.assertEqual(cursor.fetchone()[0], "admin")

                cursor.execute(
                    "SELECT visibility, join_policy, purpose FROM space_settings WHERE room_uid = %s::uuid",
                    (str(ROOM_UID),),
                )
                self.assertEqual(cursor.fetchone(), ("public", "open", "community"))

                cursor.execute(
                    """
                    SELECT account_uid, role, status
                    FROM space_memberships
                    WHERE room_uid = %s::uuid
                    ORDER BY account_uid
                    """,
                    (str(ROOM_UID),),
                )
                memberships = {account_uid: (role, status) for account_uid, role, status in cursor.fetchall()}
                self.assertEqual(memberships[OWNER_UID], ("owner", "active"))
                self.assertEqual(memberships[MEMBER_UID], ("moderator", "active"))
                self.assertNotIn(BANNED_UID, memberships)

                cursor.execute(
                    "SELECT label FROM space_tags WHERE room_uid = %s::uuid ORDER BY label",
                    (str(ROOM_UID),),
                )
                self.assertEqual({row[0] for row in cursor.fetchall()}, {"Кино", "игры"})

                cursor.execute("SELECT version_num FROM alembic_version")
                self.assertTrue(cursor.fetchone()[0])


if __name__ == "__main__":
    unittest.main()
