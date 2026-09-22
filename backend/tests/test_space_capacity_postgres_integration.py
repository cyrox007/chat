import asyncio
import os
import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, select

from components.identity.model import Account
from components.model_registry import ensure_models_registered
from components.room.model import Room, RoomMember
from components.space.capacity import lock_space_admission_policy
from components.space.invitation_service import respond_to_invitation
from components.space.membership_service import manage_membership
from components.space.model import SpaceInvitation, SpaceMembership, SpaceSettings
from components.space.service import join_space
from components.user.model import User
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class SpaceCapacityPostgresIntegrationTests(unittest.TestCase):
    def test_capacity_is_serialized_across_join_invite_and_approval_paths(self):
        async def run_case():
            ensure_models_registered()
            owner_user_uid = uuid4()
            join_user_uid = uuid4()
            invite_user_uid = uuid4()
            pending_user_uid = uuid4()

            owner_account_uid = uuid4()
            join_account_uid = uuid4()
            invite_account_uid = uuid4()
            pending_account_uid = uuid4()

            room_uid = uuid4()
            invitation_uid = uuid4()
            now = datetime.utcnow()

            async with Database.sessionmaker()() as setup_db:
                setup_db.add_all(
                    [
                        User(uid=owner_user_uid, username=f"cap-owner-{owner_user_uid.hex[:8]}"),
                        User(uid=join_user_uid, username=f"cap-join-{join_user_uid.hex[:8]}"),
                        User(uid=invite_user_uid, username=f"cap-invite-{invite_user_uid.hex[:8]}"),
                        User(uid=pending_user_uid, username=f"cap-pending-{pending_user_uid.hex[:8]}"),
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
                        Account(
                            uid=join_account_uid,
                            legacy_user_uid=join_user_uid,
                            status="active",
                            trust_level="new",
                        ),
                        Account(
                            uid=invite_account_uid,
                            legacy_user_uid=invite_user_uid,
                            status="active",
                            trust_level="new",
                        ),
                        Account(
                            uid=pending_account_uid,
                            legacy_user_uid=pending_user_uid,
                            status="active",
                            trust_level="new",
                        ),
                    ]
                )
                await setup_db.flush()
                setup_db.add(
                    Room(
                        uid=room_uid,
                        name="Capacity concurrency rehearsal",
                        owner_uid=owner_user_uid,
                        is_active=True,
                    )
                )
                await setup_db.flush()
                setup_db.add_all(
                    [
                        SpaceSettings(
                            room_uid=room_uid,
                            purpose="community",
                            visibility="public",
                            join_policy="open",
                            member_limit=2,
                        ),
                        SpaceMembership(
                            room_uid=room_uid,
                            account_uid=owner_account_uid,
                            role="owner",
                            status="active",
                            joined_at=now,
                        ),
                        SpaceInvitation(
                            uid=invitation_uid,
                            room_uid=room_uid,
                            inviter_account_uid=owner_account_uid,
                            invitee_account_uid=invite_account_uid,
                            status="pending",
                            expires_at=now + timedelta(days=1),
                        ),
                        SpaceMembership(
                            room_uid=room_uid,
                            account_uid=pending_account_uid,
                            role="member",
                            status="pending",
                            joined_at=now,
                        ),
                    ]
                )
                await setup_db.commit()

            async def run_join(account_uid):
                async with Database.sessionmaker()() as db:
                    try:
                        await join_space(db, room_uid, account_uid)
                        return "active"
                    except HTTPException as exc:
                        await db.rollback()
                        return exc.detail.get("error_type")

            async def run_invite_accept():
                async with Database.sessionmaker()() as db:
                    try:
                        await respond_to_invitation(
                            db,
                            invitation_uid=invitation_uid,
                            viewer_uid=invite_account_uid,
                            action="accept",
                        )
                        return "active"
                    except HTTPException as exc:
                        await db.rollback()
                        return exc.detail.get("error_type")

            async def run_approval():
                async with Database.sessionmaker()() as db:
                    try:
                        await manage_membership(
                            db,
                            space_uid=room_uid,
                            target_account_uid=pending_account_uid,
                            viewer_uid=owner_account_uid,
                            action="approve",
                        )
                        return "active"
                    except HTTPException as exc:
                        await db.rollback()
                        return exc.detail.get("error_type")

            async def reset_non_owner_memberships():
                async with Database.sessionmaker()() as db:
                    await db.execute(
                        delete(RoomMember).where(
                            RoomMember.room_uid == room_uid,
                            RoomMember.user_uid.in_(
                                [join_user_uid, invite_user_uid, pending_user_uid]
                            ),
                        )
                    )
                    await db.execute(
                        delete(SpaceMembership).where(
                            SpaceMembership.room_uid == room_uid,
                            SpaceMembership.account_uid.in_(
                                [
                                    join_account_uid,
                                    invite_account_uid,
                                    pending_account_uid,
                                ]
                            ),
                        )
                    )
                    invitation = await db.get(SpaceInvitation, invitation_uid)
                    invitation.status = "pending"
                    invitation.responded_at = None
                    invitation.updated_at = now
                    invitation.expires_at = now + timedelta(days=1)
                    db.add(
                        SpaceMembership(
                            room_uid=room_uid,
                            account_uid=pending_account_uid,
                            role="member",
                            status="pending",
                            joined_at=now,
                        )
                    )
                    await db.commit()

            async def hold_admission_lock():
                db = Database.sessionmaker()()
                await lock_space_admission_policy(
                    db,
                    room_uid,
                    default_join_policy="open",
                    default_member_limit=250,
                )
                return db

            try:
                # Direct join and invitation acceptance must compete for the same
                # final slot. Hold the admission lock first so both service calls
                # reach the lock boundary before either can commit.
                gate_db = await hold_admission_lock()
                join_task = asyncio.create_task(run_join(join_account_uid))
                invite_task = asyncio.create_task(run_invite_accept())
                await asyncio.sleep(0.15)
                self.assertFalse(join_task.done())
                self.assertFalse(invite_task.done())
                await gate_db.commit()
                await gate_db.close()

                results = await asyncio.gather(join_task, invite_task)
                self.assertCountEqual(results, ["active", "space_full"])

                async with Database.sessionmaker()() as verify_db:
                    active_count = int(
                        (
                            await verify_db.execute(
                                select(func.count(SpaceMembership.uid)).where(
                                    SpaceMembership.room_uid == room_uid,
                                    SpaceMembership.status == "active",
                                )
                            )
                        ).scalar_one()
                        or 0
                    )
                    self.assertEqual(active_count, 2)

                # Reset the final slot and repeat with owner approval versus a
                # direct join. This proves manager approval uses the same lock.
                await reset_non_owner_memberships()
                gate_db = await hold_admission_lock()
                join_task = asyncio.create_task(run_join(join_account_uid))
                approval_task = asyncio.create_task(run_approval())
                await asyncio.sleep(0.15)
                self.assertFalse(join_task.done())
                self.assertFalse(approval_task.done())
                await gate_db.commit()
                await gate_db.close()

                results = await asyncio.gather(join_task, approval_task)
                self.assertCountEqual(results, ["active", "space_full"])

                async with Database.sessionmaker()() as verify_db:
                    active_count = int(
                        (
                            await verify_db.execute(
                                select(func.count(SpaceMembership.uid)).where(
                                    SpaceMembership.room_uid == room_uid,
                                    SpaceMembership.status == "active",
                                )
                            )
                        ).scalar_one()
                        or 0
                    )
                    self.assertEqual(active_count, 2)

                # Same-Account duplicate joins must remain idempotent rather than
                # racing into uq_space_membership.
                await reset_non_owner_memberships()
                gate_db = await hold_admission_lock()
                first = asyncio.create_task(run_join(join_account_uid))
                second = asyncio.create_task(run_join(join_account_uid))
                await asyncio.sleep(0.15)
                self.assertFalse(first.done())
                self.assertFalse(second.done())
                await gate_db.commit()
                await gate_db.close()

                results = await asyncio.gather(first, second)
                self.assertEqual(results, ["active", "active"])

                async with Database.sessionmaker()() as verify_db:
                    rows = int(
                        (
                            await verify_db.execute(
                                select(func.count(SpaceMembership.uid)).where(
                                    SpaceMembership.room_uid == room_uid,
                                    SpaceMembership.account_uid == join_account_uid,
                                )
                            )
                        ).scalar_one()
                        or 0
                    )
                    self.assertEqual(rows, 1)
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    await cleanup_db.execute(
                        delete(RoomMember).where(RoomMember.room_uid == room_uid)
                    )
                    await cleanup_db.execute(
                        delete(SpaceInvitation).where(SpaceInvitation.room_uid == room_uid)
                    )
                    await cleanup_db.execute(
                        delete(SpaceMembership).where(SpaceMembership.room_uid == room_uid)
                    )
                    await cleanup_db.execute(
                        delete(SpaceSettings).where(SpaceSettings.room_uid == room_uid)
                    )
                    await cleanup_db.execute(delete(Room).where(Room.uid == room_uid))
                    await cleanup_db.execute(
                        delete(Account).where(
                            Account.uid.in_(
                                [
                                    owner_account_uid,
                                    join_account_uid,
                                    invite_account_uid,
                                    pending_account_uid,
                                ]
                            )
                        )
                    )
                    await cleanup_db.execute(
                        delete(User).where(
                            User.uid.in_(
                                [
                                    owner_user_uid,
                                    join_user_uid,
                                    invite_user_uid,
                                    pending_user_uid,
                                ]
                            )
                        )
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
