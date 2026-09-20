import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select

from components.identity.model import Account, AccountRole
from components.message.model import PrivateMessage
from components.model_registry import ensure_models_registered
from components.moderation.media_model import ModerationMediaRecord
from components.moderation.media_service import (
    quarantine_report_attachment,
    remove_report_attachment,
    restore_report_attachment,
)
from components.moderation.model import TrustSafetyAuditEvent, TrustSafetyReport
from components.user.model import User
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class ModerationMediaPostgresIntegrationTests(unittest.TestCase):
    def test_quarantine_restore_and_remove_are_reversible_and_audited(self):
        async def run_case():
            ensure_models_registered()
            sender_user_uid = uuid4()
            receiver_user_uid = uuid4()
            sender_account_uid = uuid4()
            receiver_account_uid = uuid4()
            moderator_account_uid = uuid4()
            message_uid = uuid4()
            report_uid = uuid4()

            with tempfile.TemporaryDirectory() as tmp:
                upload_root = Path(tmp) / "uploads"
                private_root = Path(tmp) / "moderation_media"
                source = upload_root / "images" / "reported.jpg"
                source.parent.mkdir(parents=True)
                source.write_bytes(b"reported-media-test")

                async with Database.sessionmaker()() as setup_db:
                    setup_db.add_all(
                        [
                            User(
                                uid=sender_user_uid,
                                username=f"media-sender-{sender_user_uid.hex[:8]}",
                                email=f"{sender_user_uid.hex[:12]}@example.test",
                                phone=f"+7000{sender_user_uid.int % 100000000:08d}",
                                hashed_password="not-used",
                            ),
                            User(
                                uid=receiver_user_uid,
                                username=f"media-receiver-{receiver_user_uid.hex[:8]}",
                                email=f"{receiver_user_uid.hex[:12]}@example.test",
                                phone=f"+7001{receiver_user_uid.int % 100000000:08d}",
                                hashed_password="not-used",
                            ),
                        ]
                    )
                    await setup_db.flush()
                    setup_db.add_all(
                        [
                            Account(
                                uid=sender_account_uid,
                                legacy_user_uid=sender_user_uid,
                                status="active",
                                trust_level="new",
                            ),
                            Account(
                                uid=receiver_account_uid,
                                legacy_user_uid=receiver_user_uid,
                                status="active",
                                trust_level="new",
                            ),
                            Account(
                                uid=moderator_account_uid,
                                status="active",
                                trust_level="new",
                            ),
                        ]
                    )
                    await setup_db.flush()
                    setup_db.add(AccountRole(account_uid=moderator_account_uid, role_id=2))
                    setup_db.add(
                        PrivateMessage(
                            uid=message_uid,
                            content_type="image",
                            text="",
                            media_metadata={
                                "files": [
                                    {
                                        "url": "/uploads/images/reported.jpg",
                                        "type": "image/jpeg",
                                        "name": "reported.jpg",
                                        "size": 19,
                                    }
                                ]
                            },
                            sender_uid=sender_user_uid,
                            receiver_uid=receiver_user_uid,
                            is_read=False,
                        )
                    )
                    setup_db.add(
                        TrustSafetyReport(
                            uid=report_uid,
                            reporter_account_uid=receiver_account_uid,
                            target_account_uid=sender_account_uid,
                            source_type="messenger_message",
                            source_uid=message_uid,
                            category="other",
                            priority="low",
                            status="in_review",
                            assigned_to_account_uid=moderator_account_uid,
                        )
                    )
                    await setup_db.commit()

                try:
                    async with Database.sessionmaker()() as db:
                        quarantined = await quarantine_report_attachment(
                            db,
                            report_uid=report_uid,
                            attachment_index=0,
                            moderator_account_uid=moderator_account_uid,
                            reason="Reported attachment requires review.",
                            upload_root=upload_root,
                            private_root=private_root,
                        )
                        self.assertEqual(quarantined["status"], "quarantined")
                        self.assertFalse(source.exists())
                        record_uid = quarantined["uid"]

                        message = (
                            await db.execute(
                                select(PrivateMessage).where(PrivateMessage.uid == message_uid)
                            )
                        ).scalar_one()
                        self.assertEqual(
                            message.media_metadata["files"][0]["moderation_status"],
                            "quarantined",
                        )

                    private_files = [path for path in private_root.rglob("*") if path.is_file()]
                    self.assertEqual(len(private_files), 1)
                    self.assertEqual(private_files[0].read_bytes(), b"reported-media-test")

                    async with Database.sessionmaker()() as db:
                        restored = await restore_report_attachment(
                            db,
                            report_uid=report_uid,
                            record_uid=record_uid,
                            moderator_account_uid=moderator_account_uid,
                            upload_root=upload_root,
                            private_root=private_root,
                        )
                        self.assertEqual(restored["status"], "restored")
                        self.assertTrue(source.exists())

                        message = (
                            await db.execute(
                                select(PrivateMessage).where(PrivateMessage.uid == message_uid)
                            )
                        ).scalar_one()
                        self.assertNotIn(
                            "moderation_status",
                            message.media_metadata["files"][0],
                        )

                    async with Database.sessionmaker()() as db:
                        quarantined_again = await quarantine_report_attachment(
                            db,
                            report_uid=report_uid,
                            attachment_index=0,
                            moderator_account_uid=moderator_account_uid,
                            reason="Confirmed policy review.",
                            upload_root=upload_root,
                            private_root=private_root,
                        )
                        self.assertEqual(quarantined_again["uid"], record_uid)
                        removed = await remove_report_attachment(
                            db,
                            report_uid=report_uid,
                            record_uid=record_uid,
                            moderator_account_uid=moderator_account_uid,
                            reason="Removed from public delivery after review.",
                        )
                        self.assertEqual(removed["status"], "removed")
                        self.assertFalse(source.exists())

                        message = (
                            await db.execute(
                                select(PrivateMessage).where(PrivateMessage.uid == message_uid)
                            )
                        ).scalar_one()
                        self.assertEqual(
                            message.media_metadata["files"][0]["moderation_status"],
                            "removed",
                        )

                        events = (
                            await db.execute(
                                select(TrustSafetyAuditEvent.event_type).where(
                                    TrustSafetyAuditEvent.report_uid == report_uid
                                )
                            )
                        ).scalars().all()
                        self.assertIn("media_quarantined", events)
                        self.assertIn("media_restored", events)
                        self.assertIn("media_removed", events)
                finally:
                    async with Database.sessionmaker()() as cleanup_db:
                        await cleanup_db.execute(
                            delete(ModerationMediaRecord).where(
                                ModerationMediaRecord.report_uid == report_uid
                            )
                        )
                        await cleanup_db.execute(
                            delete(TrustSafetyAuditEvent).where(
                                TrustSafetyAuditEvent.report_uid == report_uid
                            )
                        )
                        await cleanup_db.execute(
                            delete(TrustSafetyReport).where(TrustSafetyReport.uid == report_uid)
                        )
                        await cleanup_db.execute(
                            delete(PrivateMessage).where(PrivateMessage.uid == message_uid)
                        )
                        await cleanup_db.execute(
                            delete(AccountRole).where(AccountRole.account_uid == moderator_account_uid)
                        )
                        await cleanup_db.execute(
                            delete(Account).where(
                                Account.uid.in_(
                                    [sender_account_uid, receiver_account_uid, moderator_account_uid]
                                )
                            )
                        )
                        await cleanup_db.execute(
                            delete(User).where(User.uid.in_([sender_user_uid, receiver_user_uid]))
                        )
                        await cleanup_db.commit()
                    await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
