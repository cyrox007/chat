import asyncio
import json
import os
import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select

from components.identity.model import Account, AccountRole
from components.model_registry import ensure_models_registered
from components.moderation.abuse_model import TrustSafetyAbuseSignal
from components.moderation.automation_settings import ModerationAutomationConfig
from components.moderation.model import PlatformRestriction
from components.moderation.operations_metrics import trust_safety_metrics
from components.moderation.protective_hold import maybe_apply_protective_hold
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class TrustSafetyOperationsPostgresIntegrationTests(unittest.TestCase):
    def test_protective_hold_requires_corroboration_is_bounded_and_metrics_are_aggregate(self):
        async def run_case():
            ensure_models_registered()
            account_uid = uuid4()
            moderator_uid = uuid4()
            now = datetime.utcnow()
            first_signal_uid = uuid4()
            second_signal_uid = uuid4()
            moderator_signal_a = uuid4()
            moderator_signal_b = uuid4()

            async with Database.sessionmaker()() as setup_db:
                setup_db.add_all(
                    [
                        Account(uid=account_uid, status="active", trust_level="new"),
                        Account(uid=moderator_uid, status="active", trust_level="new"),
                    ]
                )
                await setup_db.flush()
                setup_db.add(AccountRole(account_uid=moderator_uid, role_id=2))
                setup_db.add_all(
                    [
                        TrustSafetyAbuseSignal(
                            uid=first_signal_uid,
                            account_uid=account_uid,
                            signal_type="dm_distinct_recipient_burst",
                            surface="messenger",
                            severity="high",
                            observed_count=20,
                            window_seconds=600,
                            dedupe_key=f"ops-a-{first_signal_uid}",
                            details={"distinct_recipients": 20, "threshold": 8},
                            status="open",
                            first_seen_at=now,
                            last_seen_at=now,
                            created_at=now,
                            updated_at=now,
                        ),
                        TrustSafetyAbuseSignal(
                            uid=second_signal_uid,
                            account_uid=account_uid,
                            signal_type="space_invite_recipient_burst",
                            surface="space_invitation",
                            severity="high",
                            observed_count=30,
                            window_seconds=600,
                            dedupe_key=f"ops-b-{second_signal_uid}",
                            details={"distinct_recipients": 30, "threshold": 12},
                            status="open",
                            first_seen_at=now,
                            last_seen_at=now,
                            created_at=now,
                            updated_at=now,
                        ),
                        TrustSafetyAbuseSignal(
                            uid=moderator_signal_a,
                            account_uid=moderator_uid,
                            signal_type="dm_distinct_recipient_burst",
                            surface="messenger",
                            severity="critical",
                            observed_count=50,
                            window_seconds=600,
                            dedupe_key=f"ops-mod-a-{moderator_signal_a}",
                            details={"distinct_recipients": 50, "threshold": 8},
                            status="open",
                            first_seen_at=now,
                            last_seen_at=now,
                            created_at=now,
                            updated_at=now,
                        ),
                        TrustSafetyAbuseSignal(
                            uid=moderator_signal_b,
                            account_uid=moderator_uid,
                            signal_type="space_invite_recipient_burst",
                            surface="space_invitation",
                            severity="critical",
                            observed_count=50,
                            window_seconds=600,
                            dedupe_key=f"ops-mod-b-{moderator_signal_b}",
                            details={"distinct_recipients": 50, "threshold": 12},
                            status="open",
                            first_seen_at=now,
                            last_seen_at=now,
                            created_at=now,
                            updated_at=now,
                        ),
                    ]
                )
                await setup_db.commit()

            disabled = ModerationAutomationConfig(
                enabled=False,
                hold_minutes=10,
                corroboration_lookback_seconds=1800,
                min_high_signals=2,
            )
            enabled = ModerationAutomationConfig(
                enabled=True,
                hold_minutes=10,
                corroboration_lookback_seconds=1800,
                min_high_signals=2,
            )

            try:
                async with Database.sessionmaker()() as db:
                    self.assertIsNone(
                        await maybe_apply_protective_hold(
                            db, signal_uid=first_signal_uid, config=disabled
                        )
                    )
                    before = (
                        await db.execute(
                            select(PlatformRestriction).where(
                                PlatformRestriction.target_account_uid == account_uid
                            )
                        )
                    ).scalars().all()
                    self.assertEqual(before, [])

                async with Database.sessionmaker()() as db:
                    hold = await maybe_apply_protective_hold(
                        db, signal_uid=first_signal_uid, config=enabled
                    )
                    self.assertIsNotNone(hold)
                    self.assertEqual(hold["origin"], "automation")
                    self.assertEqual(hold["capability"], "messenger.send")
                    self.assertNotEqual(hold["capability"], "account.access")

                    row = (
                        await db.execute(
                            select(PlatformRestriction).where(
                                PlatformRestriction.target_account_uid == account_uid,
                                PlatformRestriction.origin == "automation",
                            )
                        )
                    ).scalar_one()
                    self.assertIsNone(row.actor_account_uid)
                    self.assertIsNotNone(row.expires_at)
                    duration = row.expires_at - row.starts_at
                    self.assertGreaterEqual(duration, timedelta(minutes=5))
                    self.assertLessEqual(duration, timedelta(minutes=15))

                    metrics = await trust_safety_metrics(db, window_hours=24)
                    self.assertGreaterEqual(
                        metrics["restrictions"]["origin_counts"].get("automation", 0), 1
                    )
                    self.assertGreaterEqual(
                        metrics["restrictions"]["active_automation_holds"], 1
                    )
                    serialized = json.dumps(metrics)
                    self.assertNotIn("account_uid", serialized)
                    self.assertNotIn(str(account_uid), serialized)

                async with Database.sessionmaker()() as db:
                    privileged = await maybe_apply_protective_hold(
                        db, signal_uid=moderator_signal_a, config=enabled
                    )
                    self.assertIsNone(privileged)
                    privileged_holds = (
                        await db.execute(
                            select(PlatformRestriction).where(
                                PlatformRestriction.target_account_uid == moderator_uid,
                                PlatformRestriction.origin == "automation",
                            )
                        )
                    ).scalars().all()
                    self.assertEqual(privileged_holds, [])
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    await cleanup_db.execute(
                        delete(AccountRole).where(AccountRole.account_uid == moderator_uid)
                    )
                    await cleanup_db.execute(
                        delete(Account).where(Account.uid.in_([account_uid, moderator_uid]))
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
