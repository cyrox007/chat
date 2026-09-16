"""Prepare a representative pre-revival database for migration rehearsal.

This is a CI helper, not a unittest module. It intentionally writes only to the
separate legacy rehearsal database selected through environment variables.
"""

import argparse
import os
from datetime import datetime, timezone
from uuid import UUID

import psycopg2
from psycopg2 import sql


LEGACY_DB_NAME = os.getenv("PUBCHAT_LEGACY_DB_NAME", "chat_legacy_ci")
OWNER_UID = UUID("11111111-1111-1111-1111-111111111111")
MEMBER_UID = UUID("22222222-2222-2222-2222-222222222222")
BANNED_UID = UUID("33333333-3333-3333-3333-333333333333")
ROOM_UID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def connection_kwargs(database: str) -> dict:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": database,
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
    }


def create_database() -> None:
    with psycopg2.connect(**connection_kwargs("postgres")) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (LEGACY_DB_NAME,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(LEGACY_DB_NAME)))


def seed_legacy() -> None:
    now = datetime(2025, 4, 25, 12, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    with psycopg2.connect(**connection_kwargs(LEGACY_DB_NAME)) as connection:
        with connection.cursor() as cursor:
            users = [
                (
                    1,
                    str(OWNER_UID),
                    "legacy_owner",
                    " Owner@Example.COM ",
                    "+49 (170) 123-45-67",
                    "Alex",
                    "Owner",
                    "legacy-password-hash-owner",
                    "admin",
                    True,
                    True,
                    now,
                ),
                (
                    2,
                    str(MEMBER_UID),
                    "legacy_member",
                    "member@example.com",
                    "+49 170 7654321",
                    "Maria",
                    "Member",
                    "legacy-password-hash-member",
                    "user",
                    True,
                    False,
                    now,
                ),
                (
                    3,
                    str(BANNED_UID),
                    "legacy_banned",
                    "banned@example.com",
                    "+49 170 0000000",
                    "Banned",
                    "Member",
                    "legacy-password-hash-banned",
                    "user",
                    True,
                    False,
                    now,
                ),
            ]
            cursor.executemany(
                """
                INSERT INTO users (
                    id, uid, username, email, phone, first_name, last_name,
                    hashed_password, global_role, is_active, is_verified, created_at
                ) VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                users,
            )
            cursor.execute(
                """
                INSERT INTO rooms (
                    id, uid, name, description, tags, owner_uid, created_at, is_active
                ) VALUES (
                    1, %s::uuid, 'Legacy Lounge', 'Migration rehearsal room',
                    'Кино, игры,  Кино', %s::uuid, %s, TRUE
                )
                """,
                (str(ROOM_UID), str(OWNER_UID), now),
            )
            cursor.executemany(
                """
                INSERT INTO room_members (id, room_uid, user_uid, role, joined_at, is_banned)
                VALUES (%s, %s::uuid, %s::uuid, %s, %s, FALSE)
                """,
                [
                    (1, str(ROOM_UID), str(MEMBER_UID), "member", now),
                    (2, str(ROOM_UID), str(MEMBER_UID), "moderator", now),
                    (3, str(ROOM_UID), str(BANNED_UID), "member", now),
                ],
            )
            cursor.execute(
                """
                INSERT INTO room_bans (
                    id, room_uid, user_uid, banned_by_uid, reason,
                    created_at, expires_at, is_active
                ) VALUES (
                    1, %s::uuid, %s::uuid, %s::uuid, 'legacy restriction',
                    %s, NULL, TRUE
                )
                """,
                (str(ROOM_UID), str(BANNED_UID), str(OWNER_UID), now),
            )
        connection.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("create-db", "seed"))
    args = parser.parse_args()
    if args.action == "create-db":
        create_database()
    else:
        seed_legacy()


if __name__ == "__main__":
    main()
