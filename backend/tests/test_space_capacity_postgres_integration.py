import asyncio
import os
import unittest
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select

from components.identity.model import Account
from components.model_registry import ensure_models_registered
from components.room.model import Room, RoomMember
from components.space.model import SpaceMembership, SpaceSettings
from components.space.service import join_space
from components.user.model import User
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class SpaceCapacityPostgresIntegrationTests(unittest.TestCase):
    def test_last_space_slot_is_consumed_by_only_one_concurrent_join(self):
        async def run_case():
            ensure_models_registered()
            room_uid = uuid4()
            owner_user_uid = uuid4()
            joiner_user_uids = [uuid4(), uuid4()]
            owner_account_uid = uuid4()
            joiner_account_uids = [uuid4(), uuid4()]

            async with Database.sessionmaker()() as setup_db:
                setup_db.add_all(
                    [
                        User(
                            uid=owner_user_uid,
                            username=f"capacity-owner-{str(owner_user_uid)[:8]}",
                            is_active=True,
                        ),
                        *[
                            User(
                                uid=user_uid,
                                username=f"capacity-user-{str(user_uid)[:8]}",
                                is_active=True,
                            )
                            for user_uid in joiner_user_uids
                        ],
                    ]
                )
                await setup_db.flush()
                setup_db.add_all(
                    [
                        Account(
                            uid=owner_account_uid,
                            legacy_user_uid=owner_user_uid,
                            status="active",
                            trust_level="new",
                        ),
                        *[
                            Account(
                                uid=account_uid,
                                legacy_user_uid=user_uid,
                                status="active",
                                trust_level="new",
                            )
                            for account_uid, user_uid in zip(
                                joiner_account_uids,
                                joiner_user_uids,
                            )
                        ],
                    ]
                )
                setup_db.add(
                    Room(
                        uid=room_uid,
                        name="Capacity race rehearsal",
                        owner_uid=owner_user_uid,
                        is_active=True,
                    )
                )
                await setup_db.flush()
                setup_db.add(
                    SpaceSettings(
                        room_uid=room_uid,
                        visibility="public",
                        join_policy="open",
                        member_limit=2,
                    )
                )
                setup_db.add(
                    SpaceMembership(
                        room_uid=room_uid,
                        account_uid=owner_account_uid,
                        role="owner",
                        status="active",
                    )
                )
                await setup_db.commit()

            ready = asyncio.Event()
            started = 0
            started_lock = asyncio.Lock()

            async def attempt_join(account_uid):
                nonlocal started
                async with Database.sessionmaker()() as db:
                    async with started_lock:
                        started += 1
                        if started == 2:
                            ready.set()
                    await ready.wait()
                    try:
                        result = await join_space(db, room_uid, account_uid)
                        return ("joined", account_uid, result)
                    except HTTPException as exc:
                        await db.rollback()
                        return ("rejected", account_uid, exc.status_code, exc.detail)

            try:
                results = await asyncio.gather(
                    *(attempt_join(uid) for uid in joiner_account_uids)
                )
                joined = [item for item in results if item[0] == "joined"]
                rejected = [item for item in results if item[0] == "rejected"]
                self.assertEqual(len(joined), 1, results)
                self.assertEqual(len(rejected), 1, results)
                self.assertEqual(rejected[0][2], 409)
                self.assertEqual(
                    rejected[0][3].get("error_type"),
                    "space_full",
                )

                async with Database.sessionmaker()() as verify_db:
                    active = list(
                        (
                            await verify_db.execute(
                                select(SpaceMembership).where(
                                    SpaceMembership.room_uid == room_uid,
                                    SpaceMembership.status == "active",
                                )
                            )
                        ).scalars().all()
                    )
                    self.assertEqual(len(active), 2)
                    active_accounts = {item.account_uid for item in active}
                    self.assertIn(owner_account_uid, active_accounts)
                    self.assertEqual(
                        len(active_accounts.intersection(joiner_account_uids)),
                        1,
                    )
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    await cleanup_db.execute(
                        delete(RoomMember).where(RoomMember.room_uid == room_uid)
                    )
                    await cleanup_db.execute(
                        delete(SpaceMembership).where(
                            SpaceMembership.room_uid == room_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(SpaceSettings).where(
                            SpaceSettings.room_uid == room_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(Room).where(Room.uid == room_uid)
                    )
                    await cleanup_db.execute(
                        delete(Account).where(
                            Account.uid.in_(
                                [owner_account_uid, *joiner_account_uids]
                            )
                        )
                    )
                    await cleanup_db.execute(
                        delete(User).where(
                            User.uid.in_(
                                [owner_user_uid, *joiner_user_uids]
                            )
                        )
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
