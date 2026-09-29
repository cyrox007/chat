import asyncio
import json
import os
import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from components.discovery.profiling import profile_discovery
from components.identity.model import Account, AccountRelationship, Persona
from components.message.model import Message
from components.model_registry import ensure_models_registered
from components.room.model import Room
from components.space.model import (
    SpaceEvent,
    SpaceMembership,
    SpaceSettings,
)
from components.user.model import User
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class DiscoveryPrivacyLargePoolPostgresIntegrationTests(unittest.TestCase):
    def test_large_pool_preserves_visibility_block_and_private_context_boundaries(self):
        async def run_case():
            ensure_models_registered()
            now = datetime.utcnow()

            viewer_account_uid = uuid4()
            viewer_legacy_uid = uuid4()
            normal_owner_account_uid = uuid4()
            normal_owner_legacy_uid = uuid4()
            blocked_owner_account_uid = uuid4()
            blocked_owner_legacy_uid = uuid4()

            blocked_public_uid = uuid4()
            blocked_member_uid = uuid4()
            private_outsider_uid = uuid4()
            private_pending_uid = uuid4()
            normal_room_uids = [uuid4() for _ in range(260)]

            async with Database.sessionmaker()() as db:
                db.add_all(
                    [
                        User(
                            uid=viewer_legacy_uid,
                            username=f"privacy-viewer-{viewer_legacy_uid.hex[:8]}",
                        ),
                        User(
                            uid=normal_owner_legacy_uid,
                            username=f"privacy-owner-{normal_owner_legacy_uid.hex[:8]}",
                        ),
                        User(
                            uid=blocked_owner_legacy_uid,
                            username=f"privacy-blocked-{blocked_owner_legacy_uid.hex[:8]}",
                        ),
                    ]
                )
                await db.flush()

                db.add_all(
                    [
                        Account(
                            uid=viewer_account_uid,
                            legacy_user_uid=viewer_legacy_uid,
                            status="active",
                            trust_level="new",
                        ),
                        Account(
                            uid=normal_owner_account_uid,
                            legacy_user_uid=normal_owner_legacy_uid,
                            status="active",
                            trust_level="new",
                        ),
                        Account(
                            uid=blocked_owner_account_uid,
                            legacy_user_uid=blocked_owner_legacy_uid,
                            status="active",
                            trust_level="new",
                        ),
                    ]
                )
                await db.flush()

                db.add_all(
                    [
                        Persona(
                            account_uid=viewer_account_uid,
                            handle=f"dpv{viewer_account_uid.hex[:12]}",
                            display_name="Discovery Privacy Viewer",
                            social_intent="open",
                            is_primary=True,
                        ),
                        Persona(
                            account_uid=normal_owner_account_uid,
                            handle=f"dpn{normal_owner_account_uid.hex[:12]}",
                            display_name="Normal Discovery Owner",
                            social_intent="open",
                            is_primary=True,
                        ),
                        Persona(
                            account_uid=blocked_owner_account_uid,
                            handle=f"dpb{blocked_owner_account_uid.hex[:12]}",
                            display_name="Blocked Discovery Owner",
                            social_intent="open",
                            is_primary=True,
                        ),
                        AccountRelationship(
                            from_account_uid=viewer_account_uid,
                            to_account_uid=blocked_owner_account_uid,
                            relation_type="block",
                            created_at=now,
                        ),
                    ]
                )

                for index, room_uid in enumerate(normal_room_uids):
                    db.add(
                        Room(
                            uid=room_uid,
                            name=f"Large privacy fixture {index:03d}",
                            description="Normal public discovery fixture",
                            owner_uid=normal_owner_legacy_uid,
                            created_at=now - timedelta(minutes=index),
                            is_active=True,
                        )
                    )
                    db.add(
                        SpaceSettings(
                            room_uid=room_uid,
                            purpose="community",
                            visibility="public",
                            join_policy="open",
                            member_limit=250,
                            created_at=now,
                            updated_at=now,
                        )
                    )

                special_rooms = [
                    (
                        blocked_public_uid,
                        "Blocked owner public leak sentinel",
                        blocked_owner_legacy_uid,
                        "public",
                    ),
                    (
                        blocked_member_uid,
                        "Blocked owner member relation sentinel",
                        blocked_owner_legacy_uid,
                        "public",
                    ),
                    (
                        private_outsider_uid,
                        "Private outsider leak sentinel",
                        normal_owner_legacy_uid,
                        "private",
                    ),
                    (
                        private_pending_uid,
                        "Private pending context sentinel",
                        normal_owner_legacy_uid,
                        "private",
                    ),
                ]
                for index, (room_uid, name, owner_uid, visibility) in enumerate(special_rooms):
                    db.add(
                        Room(
                            uid=room_uid,
                            name=name,
                            description=f"Sensitive fixture {name}",
                            owner_uid=owner_uid,
                            created_at=now - timedelta(days=30 + index),
                            is_active=True,
                        )
                    )
                    db.add(
                        SpaceSettings(
                            room_uid=room_uid,
                            purpose="conversation",
                            visibility=visibility,
                            join_policy="request",
                            member_limit=250,
                            created_at=now,
                            updated_at=now,
                        )
                    )

                db.add_all(
                    [
                        SpaceMembership(
                            room_uid=normal_room_uids[0],
                            account_uid=viewer_account_uid,
                            role="member",
                            status="active",
                            joined_at=now - timedelta(days=10),
                            updated_at=now,
                        ),
                        SpaceMembership(
                            room_uid=blocked_member_uid,
                            account_uid=viewer_account_uid,
                            role="member",
                            status="active",
                            joined_at=now - timedelta(days=3),
                            updated_at=now,
                        ),
                        SpaceMembership(
                            room_uid=private_pending_uid,
                            account_uid=viewer_account_uid,
                            role="member",
                            status="pending",
                            joined_at=now - timedelta(days=1),
                            updated_at=now,
                        ),
                    ]
                )

                for room_uid, author_uid, creator_account_uid in (
                    (
                        blocked_public_uid,
                        blocked_owner_legacy_uid,
                        blocked_owner_account_uid,
                    ),
                    (
                        blocked_member_uid,
                        blocked_owner_legacy_uid,
                        blocked_owner_account_uid,
                    ),
                    (
                        private_outsider_uid,
                        normal_owner_legacy_uid,
                        normal_owner_account_uid,
                    ),
                    (
                        private_pending_uid,
                        normal_owner_legacy_uid,
                        normal_owner_account_uid,
                    ),
                ):
                    db.add(
                        Message(
                            content_type="text",
                            text="privacy regression recent activity",
                            room_uid=room_uid,
                            author_uid=author_uid,
                            created_at=now - timedelta(minutes=2),
                        )
                    )
                    db.add(
                        SpaceEvent(
                            room_uid=room_uid,
                            created_by_account_uid=creator_account_uid,
                            title="Privacy regression upcoming event",
                            starts_at=now + timedelta(hours=2),
                            status="scheduled",
                            created_at=now,
                            updated_at=now,
                        )
                    )

                await db.flush()

                results, profile = await profile_discovery(
                    db,
                    viewer_account_uid,
                    limit=200,
                    offset=0,
                )

                by_uid = {item["uid"]: item for item in results}

                # Public Spaces owned by a blocked Account are suppressed from
                # new discovery unless a pre-existing membership relation exists.
                self.assertNotIn(str(blocked_public_uid), by_uid)
                self.assertIn(str(blocked_member_uid), by_uid)
                self.assertEqual(
                    by_uid[str(blocked_member_uid)]["viewer_membership"]["status"],
                    "active",
                )

                # Candidate generation may see recent/upcoming rows for a
                # private Space, but canonical Space eligibility must filter it.
                self.assertNotIn(str(private_outsider_uid), by_uid)

                # Pending membership may reveal the private Space itself, but it
                # must not reveal live recent/upcoming context until active.
                self.assertIn(str(private_pending_uid), by_uid)
                pending = by_uid[str(private_pending_uid)]
                self.assertEqual(pending["viewer_membership"]["status"], "pending")
                self.assertIsNone(pending["discovery"]["upcoming"])
                pending_reasons = {
                    item["code"] for item in pending["discovery"]["reasons"]
                }
                self.assertNotIn("active_conversation", pending_reasons)
                self.assertNotIn("upcoming_activity", pending_reasons)

                serialized = json.dumps(results, ensure_ascii=False, sort_keys=True)
                self.assertNotIn("Blocked owner public leak sentinel", serialized)
                self.assertNotIn("Private outsider leak sentinel", serialized)
                self.assertNotIn(str(private_outsider_uid), serialized)

                # Privacy checks must not turn the large-pool path into N+1.
                self.assertLessEqual(profile.statement_count, 30)
                self.assertLess(profile.wall_elapsed_ms, 5000.0)

                await db.rollback()

            await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
