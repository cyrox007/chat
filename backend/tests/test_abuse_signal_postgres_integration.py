import asyncio
import os
import unittest
from uuid import uuid4

from sqlalchemy import delete, select

from components.identity.model import Account
from components.model_registry import ensure_models_registered
from components.moderation.abuse_model import TrustSafetyAbuseSignal
from components.moderation.abuse_signals import emit_abuse_signal, review_abuse_signal
from components.moderation.model import PlatformRestriction
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class AbuseSignalPostgresIntegrationTests(unittest.TestCase):
    def test_signal_dedupe_is_durable_and_review_is_human_only(self):
        async def run_case():
            ensure_models_registered()
            actor_uid = uuid4()
            reviewer_uid = uuid4()

            async with Database.sessionmaker()() as setup_db:
                setup_db.add_all(
                    [
                        Account(uid=actor_uid, status="active", trust_level="new"),
                        Account(uid=reviewer_uid, status="active", trust_level="new"),
                    ]
                )
                await setup_db.commit()

            try:
                async with Database.sessionmaker()() as db:
                    first_uid = await emit_abuse_signal(
                        db,
                        account_uid=actor_uid,
                        signal_type="dm_distinct_recipient_burst",
                        surface="messenger",
                        observed_count=8,
                        window_seconds=600,
                        severity="medium",
                        details={"distinct_recipients": 8, "threshold": 8},
                    )
                    second_uid = await emit_abuse_signal(
                        db,
                        account_uid=actor_uid,
                        signal_type="dm_distinct_recipient_burst",
                        surface="messenger",
                        observed_count=11,
                        window_seconds=600,
                        severity="medium",
                        details={"distinct_recipients": 11, "threshold": 8},
                    )
                    self.assertEqual(first_uid, second_uid)

                    row = await db.get(TrustSafetyAbuseSignal, first_uid)
                    self.assertEqual(row.observed_count, 11)
                    self.assertEqual(row.status, "open")
                    self.assertNotIn("content", row.details)
                    self.assertNotIn("message", row.details)

                async with Database.sessionmaker()() as db:
                    reviewed = await review_abuse_signal(
                        db,
                        signal_uid=first_uid,
                        reviewer_account_uid=reviewer_uid,
                        decision="reviewed",
                        note="Reviewed as behavioral evidence only.",
                        calibration_label="true_positive",
                    )
                    self.assertEqual(reviewed["status"], "reviewed")
                    self.assertEqual(reviewed["calibration_label"], "true_positive")
                    self.assertEqual(reviewed["reviewed_by_account_uid"], str(reviewer_uid))

                    # Reviewing a signal does not create a platform restriction.
                    restriction_count = (
                        await db.execute(
                            select(PlatformRestriction).where(
                                PlatformRestriction.target_account_uid == actor_uid
                            )
                        )
                    ).scalars().all()
                    self.assertEqual(restriction_count, [])
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    await cleanup_db.execute(
                        delete(TrustSafetyAbuseSignal).where(
                            TrustSafetyAbuseSignal.account_uid == actor_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(Account).where(Account.uid.in_([actor_uid, reviewer_uid]))
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
