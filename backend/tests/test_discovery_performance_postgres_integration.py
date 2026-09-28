import asyncio
import os
import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from components.discovery.profiling import profile_discovery
from components.identity.model import Account, Persona
from components.message.model import Message
from components.model_registry import ensure_models_registered
from components.room.model import Room
from components.space.model import (
    SpaceEvent,
    SpaceMembership,
    SpaceSettings,
    SpaceTag,
)
from components.user.model import User
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class DiscoveryPerformancePostgresIntegrationTests(unittest.TestCase):
    def test_large_candidate_set_stays_within_query_and_latency_budget(self):
        async def run_case():
            ensure_models_registered()
            now = datetime.utcnow()
            viewer_account_uid = uuid4()
            viewer_legacy_uid = uuid4()
            owner_account_uid = uuid4()
            owner_legacy_uid = uuid4()
            room_uids = [uuid4() for _ in range(260)]

            async with Database.sessionmaker()() as db:
                db.add_all(
                    [
                        User(
                            uid=viewer_legacy_uid,
                            username=f"profile-viewer-{viewer_legacy_uid.hex[:8]}",
                        ),
                        User(
                            uid=owner_legacy_uid,
                            username=f"profile-owner-{owner_legacy_uid.hex[:8]}",
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
                            uid=owner_account_uid,
                            legacy_user_uid=owner_legacy_uid,
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
                            handle=f"pv{viewer_account_uid.hex[:12]}",
                            display_name="Profile Viewer",
                            social_intent="open",
                            is_primary=True,
                        ),
                        Persona(
                            account_uid=owner_account_uid,
                            handle=f"po{owner_account_uid.hex[:12]}",
                            display_name="Profile Owner",
                            social_intent="open",
                            is_primary=True,
                        ),
                    ]
                )

                for index, room_uid in enumerate(room_uids):
                    purpose = "conversation" if index % 2 == 0 else "games"
                    tag_slug = "music" if index % 3 == 0 else "general"
                    db.add(
                        Room(
                            uid=room_uid,
                            name=f"Discovery profile Space {index:03d}",
                            description="Synthetic bounded discovery profiling fixture",
                            owner_uid=owner_legacy_uid,
                            created_at=now - timedelta(minutes=index),
                            is_active=True,
                        )
                    )
                    db.add(
                        SpaceSettings(
                            room_uid=room_uid,
                            purpose=purpose,
                            visibility="public",
                            join_policy="open",
                            member_limit=250,
                            created_at=now - timedelta(minutes=index),
                            updated_at=now - timedelta(minutes=index),
                        )
                    )
                    db.add(
                        SpaceTag(
                            room_uid=room_uid,
                            slug=tag_slug,
                            label=tag_slug.title(),
                        )
                    )

                    if index < 12:
                        db.add(
                            SpaceMembership(
                                room_uid=room_uid,
                                account_uid=viewer_account_uid,
                                role="member",
                                status="active",
                                joined_at=now - timedelta(days=2),
                                updated_at=now - timedelta(minutes=index),
                            )
                        )
                    if index < 64:
                        db.add(
                            Message(
                                content_type="text",
                                text="synthetic recent discovery activity",
                                room_uid=room_uid,
                                author_uid=owner_legacy_uid,
                                created_at=now - timedelta(minutes=index),
                            )
                        )
                    if index < 48:
                        db.add(
                            SpaceEvent(
                                room_uid=room_uid,
                                created_by_account_uid=owner_account_uid,
                                title=f"Upcoming profile event {index}",
                                starts_at=now + timedelta(hours=index + 1),
                                status="scheduled",
                                created_at=now,
                                updated_at=now,
                            )
                        )

                await db.flush()

                organic_items, organic = await profile_discovery(
                    db,
                    viewer_account_uid,
                    limit=30,
                    offset=0,
                )
                filtered_items, filtered = await profile_discovery(
                    db,
                    viewer_account_uid,
                    purpose="games",
                    limit=30,
                    offset=0,
                )

                # Query count is the primary regression gate: it must stay
                # bounded even when the candidate fixture exceeds the 200 pool.
                self.assertEqual(len(organic_items), 30)
                self.assertLessEqual(organic.statement_count, 30)
                self.assertLessEqual(organic.select_count, 30)

                # Explicit filter mode skips multi-source candidate generation
                # and should remain materially cheaper in round-trips.
                self.assertEqual(len(filtered_items), 30)
                self.assertLessEqual(filtered.statement_count, 20)
                self.assertLess(filtered.statement_count, organic.statement_count)

                # Wide ceiling catches catastrophic scans/N+1 while avoiding
                # flaky micro-benchmark expectations on shared CI runners.
                self.assertLess(organic.wall_elapsed_ms, 5000.0)
                self.assertLess(filtered.wall_elapsed_ms, 5000.0)

                # Profiling itself is privacy-safe aggregate telemetry only.
                payload = organic.as_dict()
                self.assertEqual(
                    set(payload),
                    {
                        "result_count",
                        "statement_count",
                        "select_count",
                        "database_elapsed_ms",
                        "wall_elapsed_ms",
                    },
                )

                await db.rollback()
            await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
