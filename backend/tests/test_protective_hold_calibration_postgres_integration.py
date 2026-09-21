import asyncio
import os
import unittest
from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete, select

from components.identity.model import Account
from components.model_registry import ensure_models_registered
from components.moderation.abuse_model import (
    ProtectiveHoldEvaluation,
    TrustSafetyAbuseSignal,
)
from components.moderation.abuse_signals import review_abuse_signal
from components.moderation.automation_settings import ModerationAutomationConfig
from components.moderation.calibration import protective_hold_calibration_summary
from components.moderation.model import PlatformRestriction
from components.moderation.protective_hold import maybe_apply_protective_hold
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class ProtectiveHoldCalibrationPostgresIntegrationTests(unittest.TestCase):
    def test_shadow_labels_gate_enforcement_and_never_punish_during_calibration(self):
        async def run_case():
            ensure_models_registered()
            account_uid = uuid4()
            reviewer_uid = uuid4()
            now = datetime.utcnow()

            dm_shadow_uid = uuid4()
            invite_shadow_uid = uuid4()
            dm_live_uid = uuid4()
            invite_live_uid = uuid4()

            async with Database.sessionmaker()() as setup_db:
                setup_db.add_all(
                    [
                        Account(uid=account_uid, status="active", trust_level="new"),
                        Account(uid=reviewer_uid, status="active", trust_level="new"),
                    ]
                )
                await setup_db.flush()
                setup_db.add_all(
                    [
                        TrustSafetyAbuseSignal(
                            uid=dm_shadow_uid,
                            account_uid=account_uid,
                            signal_type="dm_distinct_recipient_burst",
                            surface="messenger",
                            severity="high",
                            observed_count=20,
                            window_seconds=600,
                            dedupe_key=f"cal-dm-shadow-{dm_shadow_uid}",
                            details={"distinct_recipients": 20, "threshold": 8},
                            status="open",
                            first_seen_at=now,
                            last_seen_at=now,
                            created_at=now,
                            updated_at=now,
                        ),
                        TrustSafetyAbuseSignal(
                            uid=invite_shadow_uid,
                            account_uid=account_uid,
                            signal_type="space_invite_recipient_burst",
                            surface="space_invitation",
                            severity="high",
                            observed_count=30,
                            window_seconds=600,
                            dedupe_key=f"cal-invite-shadow-{invite_shadow_uid}",
                            details={"distinct_recipients": 30, "threshold": 12},
                            status="open",
                            first_seen_at=now,
                            last_seen_at=now,
                            created_at=now,
                            updated_at=now,
                        ),
                        TrustSafetyAbuseSignal(
                            uid=dm_live_uid,
                            account_uid=account_uid,
                            signal_type="dm_distinct_recipient_burst",
                            surface="messenger",
                            severity="high",
                            observed_count=22,
                            window_seconds=600,
                            dedupe_key=f"cal-dm-live-{dm_live_uid}",
                            details={"distinct_recipients": 22, "threshold": 8},
                            status="open",
                            first_seen_at=now,
                            last_seen_at=now,
                            created_at=now,
                            updated_at=now,
                        ),
                        TrustSafetyAbuseSignal(
                            uid=invite_live_uid,
                            account_uid=account_uid,
                            signal_type="space_invite_recipient_burst",
                            surface="space_invitation",
                            severity="high",
                            observed_count=32,
                            window_seconds=600,
                            dedupe_key=f"cal-invite-live-{invite_live_uid}",
                            details={"distinct_recipients": 32, "threshold": 12},
                            status="open",
                            first_seen_at=now,
                            last_seen_at=now,
                            created_at=now,
                            updated_at=now,
                        ),
                    ]
                )
                await setup_db.commit()

            shadow = ModerationAutomationConfig(
                enabled=False,
                mode="shadow",
                hold_minutes=10,
                corroboration_lookback_seconds=1800,
                min_high_signals=2,
                calibration_min_labels_per_type=1,
                calibration_max_false_positive_percent=5.0,
                calibration_gate_required=False,
                enforcement_approved=False,
            )

            try:
                async with Database.sessionmaker()() as db:
                    self.assertIsNone(
                        await maybe_apply_protective_hold(
                            db, signal_uid=dm_shadow_uid, config=shadow
                        )
                    )
                    self.assertIsNone(
                        await maybe_apply_protective_hold(
                            db, signal_uid=invite_shadow_uid, config=shadow
                        )
                    )
                    restrictions = (
                        await db.execute(
                            select(PlatformRestriction).where(
                                PlatformRestriction.target_account_uid == account_uid
                            )
                        )
                    ).scalars().all()
                    self.assertEqual(restrictions, [])

                    evaluations = (
                        await db.execute(
                            select(ProtectiveHoldEvaluation).where(
                                ProtectiveHoldEvaluation.signal_uid.in_(
                                    [dm_shadow_uid, invite_shadow_uid]
                                )
                            )
                        )
                    ).scalars().all()
                    self.assertEqual(len(evaluations), 2)
                    self.assertTrue(all(item.would_hold for item in evaluations))
                    self.assertTrue(all(item.mode == "shadow" for item in evaluations))

                # A human marks DM as confirmed abuse, but invitation as a false
                # positive. One unsafe signal family must keep the gate closed.
                async with Database.sessionmaker()() as db:
                    await review_abuse_signal(
                        db,
                        signal_uid=dm_shadow_uid,
                        reviewer_account_uid=reviewer_uid,
                        decision="reviewed",
                        note="Confirmed abusive burst.",
                        calibration_label="true_positive",
                    )
                async with Database.sessionmaker()() as db:
                    await review_abuse_signal(
                        db,
                        signal_uid=invite_shadow_uid,
                        reviewer_account_uid=reviewer_uid,
                        decision="dismissed",
                        note="Legitimate invitation activity.",
                        calibration_label="false_positive",
                    )

                # A later detector pass in the same reviewed bucket must
                # not rewrite the human-labeled shadow snapshot.
                async with Database.sessionmaker()() as db:
                    before_reviewed = (
                        await db.execute(
                            select(ProtectiveHoldEvaluation).where(
                                ProtectiveHoldEvaluation.signal_uid == dm_shadow_uid
                            )
                        )
                    ).scalar_one()
                    before_decision = before_reviewed.decision
                    before_would_hold = before_reviewed.would_hold
                    self.assertIsNone(
                        await maybe_apply_protective_hold(
                            db, signal_uid=dm_shadow_uid, config=shadow
                        )
                    )
                    after_reviewed = (
                        await db.execute(
                            select(ProtectiveHoldEvaluation).where(
                                ProtectiveHoldEvaluation.signal_uid == dm_shadow_uid
                            )
                        )
                    ).scalar_one()
                    self.assertEqual(after_reviewed.decision, before_decision)
                    self.assertEqual(after_reviewed.would_hold, before_would_hold)

                gate_config = ModerationAutomationConfig(
                    enabled=True,
                    mode="enforce",
                    hold_minutes=10,
                    corroboration_lookback_seconds=1800,
                    min_high_signals=2,
                    calibration_min_labels_per_type=1,
                    calibration_max_false_positive_percent=5.0,
                    calibration_gate_required=True,
                    enforcement_approved=True,
                )
                async with Database.sessionmaker()() as db:
                    summary = await protective_hold_calibration_summary(
                        db, config=gate_config, window_days=30
                    )
                    self.assertFalse(summary["data_ready"])
                    self.assertEqual(
                        summary["signal_types"]["space_invite_recipient_burst"][
                            "false_positive_percent"
                        ],
                        100.0,
                    )
                    blocked = await maybe_apply_protective_hold(
                        db, signal_uid=dm_live_uid, config=gate_config
                    )
                    self.assertIsNone(blocked)

                # Correct the reviewed invitation label after second human review.
                async with Database.sessionmaker()() as db:
                    await review_abuse_signal(
                        db,
                        signal_uid=invite_shadow_uid,
                        reviewer_account_uid=reviewer_uid,
                        decision="reviewed",
                        note="Second review confirmed abusive invitation burst.",
                        calibration_label="true_positive",
                    )

                # Data can be ready while operational approval is still off.
                no_approval = ModerationAutomationConfig(
                    enabled=True,
                    mode="enforce",
                    hold_minutes=10,
                    corroboration_lookback_seconds=1800,
                    min_high_signals=2,
                    calibration_min_labels_per_type=1,
                    calibration_max_false_positive_percent=5.0,
                    calibration_gate_required=True,
                    enforcement_approved=False,
                )
                async with Database.sessionmaker()() as db:
                    summary = await protective_hold_calibration_summary(
                        db, config=no_approval, window_days=30
                    )
                    self.assertTrue(summary["data_ready"])
                    self.assertFalse(summary["enforcement_ready"])
                    self.assertIsNone(
                        await maybe_apply_protective_hold(
                            db, signal_uid=invite_live_uid, config=no_approval
                        )
                    )

                # With both human-reviewed data and explicit approval, only the
                # already allow-listed short hold path can execute.
                approved = ModerationAutomationConfig(
                    enabled=True,
                    mode="enforce",
                    hold_minutes=10,
                    corroboration_lookback_seconds=1800,
                    min_high_signals=2,
                    calibration_min_labels_per_type=1,
                    calibration_max_false_positive_percent=5.0,
                    calibration_gate_required=True,
                    enforcement_approved=True,
                )
                async with Database.sessionmaker()() as db:
                    hold = await maybe_apply_protective_hold(
                        db, signal_uid=invite_live_uid, config=approved
                    )
                    self.assertIsNotNone(hold)
                    self.assertEqual(hold["capability"], "invitation.send")
                    self.assertIsNotNone(hold["expires_at"])
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    await cleanup_db.execute(
                        delete(PlatformRestriction).where(
                            PlatformRestriction.target_account_uid == account_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(ProtectiveHoldEvaluation).where(
                            ProtectiveHoldEvaluation.account_uid == account_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(TrustSafetyAbuseSignal).where(
                            TrustSafetyAbuseSignal.account_uid == account_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(Account).where(
                            Account.uid.in_([account_uid, reviewer_uid])
                        )
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
