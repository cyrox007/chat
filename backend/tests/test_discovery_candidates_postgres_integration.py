import asyncio
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import delete

from components.discovery import service
from components.message.model import Message
from components.model_registry import ensure_models_registered
from components.room.model import Room
from components.user.model import User
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class DiscoveryCandidatesPostgresIntegrationTests(unittest.TestCase):
    def test_recent_activity_reintroduces_old_space_beyond_freshness_slice(self):
        async def run_case():
            ensure_models_registered()
            now = datetime.utcnow()
            author_uid = uuid4()
            old_room_uid = uuid4()
            fresh_room_uids = [uuid4() for _ in range(4)]
            viewer_uid = uuid4()

            async with Database.sessionmaker()() as setup_db:
                setup_db.add(
                    User(
                        uid=author_uid,
                        username=f"discovery-author-{author_uid.hex[:8]}",
                    )
                )
                await setup_db.flush()

                setup_db.add(
                    Room(
                        uid=old_room_uid,
                        name="Old but active Space",
                        created_at=now - timedelta(days=365),
                        is_active=True,
                    )
                )
                for index, room_uid in enumerate(fresh_room_uids):
                    setup_db.add(
                        Room(
                            uid=room_uid,
                            name=f"Fresh Space {index}",
                            created_at=now - timedelta(minutes=index),
                            is_active=True,
                        )
                    )
                await setup_db.flush()

                setup_db.add(
                    Message(
                        content_type="text",
                        text="recent activity",
                        room_uid=old_room_uid,
                        author_uid=author_uid,
                        created_at=now - timedelta(minutes=2),
                    )
                )
                await setup_db.commit()

            try:
                async with Database.sessionmaker()() as db:
                    with patch.object(service, "DISCOVERY_SOURCE_LIMIT", 2), patch.object(
                        service,
                        "DISCOVERY_POOL_LIMIT",
                        4,
                    ):
                        candidate_uids = await service._candidate_room_uids(
                            db,
                            viewer_uid,
                            viewer_purposes=set(),
                            viewer_tags=set(),
                            now=now,
                        )

                self.assertEqual(len(candidate_uids), 4)
                self.assertIn(old_room_uid, candidate_uids)
                self.assertEqual(candidate_uids[0], old_room_uid)
                # Freshness alone would choose the four newly-created Spaces and
                # exclude this year-old room. Recent activity must reintroduce it.
                self.assertNotEqual(set(candidate_uids), set(fresh_room_uids))
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    await cleanup_db.execute(
                        delete(Message).where(Message.room_uid == old_room_uid)
                    )
                    await cleanup_db.execute(
                        delete(Room).where(
                            Room.uid.in_([old_room_uid, *fresh_room_uids])
                        )
                    )
                    await cleanup_db.execute(
                        delete(User).where(User.uid == author_uid)
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
