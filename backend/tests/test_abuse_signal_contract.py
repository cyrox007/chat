import unittest
from uuid import uuid4

from components.moderation.abuse_signals import _dedupe_key
from components.moderation.abuse_settings import abuse_signal_config
from views.moderation.abuse_routers import AbuseSignalReviewRequest


class AbuseSignalContractTests(unittest.TestCase):
    def test_dedupe_key_is_stable_within_bucket_and_scope_sensitive(self):
        from datetime import datetime

        account_uid = uuid4()
        scope_uid = uuid4()
        now = datetime(2026, 9, 18, 1, 2, 3)
        first = _dedupe_key(
            account_uid=account_uid,
            signal_type="message_rate_limit",
            surface="space",
            scope_uid=scope_uid,
            bucket_seconds=600,
            now=now,
        )
        same = _dedupe_key(
            account_uid=account_uid,
            signal_type="message_rate_limit",
            surface="space",
            scope_uid=scope_uid,
            bucket_seconds=600,
            now=now,
        )
        other_scope = _dedupe_key(
            account_uid=account_uid,
            signal_type="message_rate_limit",
            surface="space",
            scope_uid=uuid4(),
            bucket_seconds=600,
            now=now,
        )
        self.assertEqual(first, same)
        self.assertNotEqual(first, other_scope)
        self.assertEqual(len(first), 64)

    def test_calibration_labels_must_match_review_decision(self):
        valid = AbuseSignalReviewRequest(
            decision="reviewed",
            calibration_label="true_positive",
        )
        self.assertEqual(valid.calibration_label, "true_positive")

        with self.assertRaises(ValueError):
            AbuseSignalReviewRequest(
                decision="dismissed",
                calibration_label="true_positive",
            )
        with self.assertRaises(ValueError):
            AbuseSignalReviewRequest(
                decision="reviewed",
                calibration_label="false_positive",
            )

    def test_thresholds_are_bounded_to_nontrivial_values(self):
        self.assertGreaterEqual(abuse_signal_config.dm_distinct_recipient_threshold, 3)
        self.assertGreaterEqual(abuse_signal_config.invite_distinct_recipient_threshold, 3)
        self.assertGreaterEqual(abuse_signal_config.rate_limit_dedupe_seconds, 60)


if __name__ == "__main__":
    unittest.main()
