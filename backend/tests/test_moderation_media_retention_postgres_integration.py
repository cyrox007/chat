import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select

from components.identity.model import Account
from components.model_registry import ensure_models_registered
from components.moderation.media_model import ModerationMediaRecord
from components.moderation.media_retention import expire_due_media_evidence
from components.moderation.model import (
    PlatformRestriction,
    PlatformRestrictionAppeal,
    TrustSafetyAuditEvent,
    TrustSafetyReport,
)
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class ModerationMediaRetentionPostgresIntegrationTests(unittest.TestCase):
    def test_expiry_waits_for_final_report_and_pending_appeal_then_scrubs_private_metadata(self):
        async def run_case():
            ensure_models_registered()
            target_uid = uuid4()
            moderator_uid = uuid4()
            report_uid = uuid4()
            record_uid = uuid4()
            restriction_uid = uuid4()
            appeal_uid = uuid4()
            now = datetime.utcnow()

            with tempfile.TemporaryDirectory() as tmp:
                upload_root = Path(tmp) / "uploads"
                private_root = Path(tmp) / "moderation_media"
                evidence_path = private_root / str(record_uid) / "reported.jpg"
                evidence_path.parent.mkdir(parents=True)
                evidence_path.write_bytes(b"expired-private-evidence")

                async with Database.sessionmaker()() as setup_db:
                    setup_db.add_all(
                        [
                            Account(uid=target_uid, status="active", trust_level="new"),
                            Account(uid=moderator_uid, status="active", trust_level="new"),
                        ]
                    )
                    await setup_db.flush()
                    setup_db.add(
                        TrustSafetyReport(
                            uid=report_uid,
                            reporter_account_uid=None,
                            target_account_uid=target_uid,
                            source_type="messenger_message",
                            source_uid=uuid4(),
                            category="other",
                            priority="normal",
                            status="in_review",
                            assigned_to_account_uid=moderator_uid,
                        )
                    )
                    setup_db.add(
                        ModerationMediaRecord(
                            uid=record_uid,
                            report_uid=report_uid,
                            source_type="messenger_message",
                            source_uid=uuid4(),
                            attachment_index=0,
                            target_account_uid=target_uid,
                            actor_account_uid=moderator_uid,
                            original_url="/uploads/images/reported.jpg",
                            original_relative_path="images/reported.jpg",
                            private_relative_path=f"{record_uid}/reported.jpg",
                            mime_type="image/jpeg",
                            original_name="reported.jpg",
                            status="removed",
                            reason="Removed after moderator review.",
                            removed_at=now - timedelta(days=100),
                            retention_due_at=now - timedelta(days=10),
                            created_at=now - timedelta(days=100),
                            updated_at=now - timedelta(days=10),
                        )
                    )
                    await setup_db.commit()

                try:
                    # Due bytes are still evidence while the report is under review.
                    async with Database.sessionmaker()() as db:
                        stats = await expire_due_media_evidence(
                            db,
                            now=now,
                            private_root=private_root,
                            upload_root=upload_root,
                        )
                        self.assertEqual(stats.candidates, 1)
                        self.assertEqual(stats.purged, 0)
                        self.assertEqual(stats.deferred_active_report, 1)
                        self.assertTrue(evidence_path.exists())

                    # Finalize the report, but create a pending appeal for a linked
                    # restriction. Retention must continue to defer.
                    async with Database.sessionmaker()() as db:
                        report = await db.get(TrustSafetyReport, report_uid)
                        report.status = "resolved"
                        report.resolution_code = "handled"
                        report.public_explanation = "Handled."
                        report.resolved_at = now
                        report.updated_at = now
                        db.add(
                            PlatformRestriction(
                                uid=restriction_uid,
                                report_uid=report_uid,
                                actor_account_uid=moderator_uid,
                                target_account_uid=target_uid,
                                capability="messenger.send",
                                scope_type="platform",
                                scope_uid=None,
                                reason_code="retention_test",
                                public_explanation="Temporary restriction.",
                                origin="human",
                                status="active",
                                actor_authority_level=50,
                                target_authority_level=0,
                                starts_at=now,
                                expires_at=now + timedelta(hours=1),
                            )
                        )
                        await db.flush()
                        db.add(
                            PlatformRestrictionAppeal(
                                uid=appeal_uid,
                                restriction_uid=restriction_uid,
                                appellant_account_uid=target_uid,
                                body="Please review this decision.",
                                status="pending",
                            )
                        )
                        await db.commit()

                    async with Database.sessionmaker()() as db:
                        stats = await expire_due_media_evidence(
                            db,
                            now=now + timedelta(minutes=1),
                            private_root=private_root,
                            upload_root=upload_root,
                        )
                        self.assertEqual(stats.purged, 0)
                        self.assertEqual(stats.deferred_pending_appeal, 1)
                        self.assertTrue(evidence_path.exists())

                    # Once the appeal is final, the policy grants a fresh full
                    # retention window from the latest case-finality event.
                    appeal_resolved_at = now + timedelta(minutes=2)
                    async with Database.sessionmaker()() as db:
                        appeal = await db.get(PlatformRestrictionAppeal, appeal_uid)
                        appeal.status = "upheld"
                        appeal.resolution = "Restriction upheld."
                        appeal.resolved_at = appeal_resolved_at
                        appeal.updated_at = appeal_resolved_at
                        await db.commit()

                    async with Database.sessionmaker()() as db:
                        stats = await expire_due_media_evidence(
                            db,
                            now=now + timedelta(minutes=3),
                            private_root=private_root,
                            upload_root=upload_root,
                        )
                        self.assertEqual(stats.purged, 0)
                        self.assertEqual(stats.extended_after_finality, 1)
                        self.assertTrue(evidence_path.exists())
                        record = await db.get(ModerationMediaRecord, record_uid)
                        extended_due_at = record.retention_due_at
                        self.assertGreater(extended_due_at, appeal_resolved_at)

                    purge_time = extended_due_at + timedelta(seconds=1)
                    async with Database.sessionmaker()() as db:
                        stats = await expire_due_media_evidence(
                            db,
                            now=purge_time,
                            private_root=private_root,
                            upload_root=upload_root,
                        )
                        self.assertEqual(stats.purged, 1)
                        self.assertEqual(stats.failed, 0)
                        self.assertFalse(evidence_path.exists())

                    async with Database.sessionmaker()() as verify_db:
                        record = await verify_db.get(ModerationMediaRecord, record_uid)
                        self.assertIsNotNone(record.purged_at)
                        self.assertIsNone(record.private_relative_path)
                        self.assertIsNone(record.original_url)
                        self.assertIsNone(record.original_relative_path)
                        self.assertIsNone(record.original_name)
                        self.assertIsNone(record.mime_type)
                        self.assertEqual(record.status, "removed")
                        events = list(
                            (
                                await verify_db.execute(
                                    select(TrustSafetyAuditEvent.event_type).where(
                                        TrustSafetyAuditEvent.report_uid == report_uid
                                    )
                                )
                            ).scalars().all()
                        )
                        self.assertIn("media_evidence_expired", events)

                    # Idempotent second run has nothing left to purge.
                    async with Database.sessionmaker()() as db:
                        stats = await expire_due_media_evidence(
                            db,
                            now=purge_time + timedelta(days=1),
                            private_root=private_root,
                            upload_root=upload_root,
                        )
                        self.assertEqual(stats.candidates, 0)
                        self.assertEqual(stats.purged, 0)
                finally:
                    async with Database.sessionmaker()() as cleanup_db:
                        await cleanup_db.execute(
                            delete(PlatformRestrictionAppeal).where(
                                PlatformRestrictionAppeal.uid == appeal_uid
                            )
                        )
                        await cleanup_db.execute(
                            delete(PlatformRestriction).where(
                                PlatformRestriction.uid == restriction_uid
                            )
                        )
                        await cleanup_db.execute(
                            delete(ModerationMediaRecord).where(
                                ModerationMediaRecord.uid == record_uid
                            )
                        )
                        await cleanup_db.execute(
                            delete(TrustSafetyAuditEvent).where(
                                TrustSafetyAuditEvent.report_uid == report_uid
                            )
                        )
                        await cleanup_db.execute(
                            delete(TrustSafetyReport).where(
                                TrustSafetyReport.uid == report_uid
                            )
                        )
                        await cleanup_db.execute(
                            delete(Account).where(
                                Account.uid.in_([target_uid, moderator_uid])
                            )
                        )
                        await cleanup_db.commit()
                    await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
