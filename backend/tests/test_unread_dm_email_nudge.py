import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from components.notification.model import ExternalDeliveryLedger
from components.notification.unread_dm_email import (
    cooldown_slot,
    email_nudge_dedupe_key,
    should_queue_again,
)


class UnreadDmEmailNudgeTests(unittest.TestCase):
    def test_same_unread_window_respects_full_cooldown_not_epoch_boundary(self):
        previous = datetime(2026, 9, 16, 23, 59, 30)
        now = previous + timedelta(minutes=2)
        self.assertFalse(
            should_queue_again(
                previous_aggregate_key="unread-dm:message-a",
                previous_created_at=previous,
                aggregate_key="unread-dm:message-a",
                now=now,
                cooldown_minutes=60,
            )
        )

    def test_same_unread_window_can_queue_after_cooldown(self):
        previous = datetime(2026, 9, 16, 12, 0, 0)
        now = previous + timedelta(minutes=60)
        self.assertTrue(
            should_queue_again(
                previous_aggregate_key="unread-dm:message-a",
                previous_created_at=previous,
                aggregate_key="unread-dm:message-a",
                now=now,
                cooldown_minutes=60,
            )
        )

    def test_new_unread_message_can_queue_without_waiting_for_cooldown(self):
        previous = datetime(2026, 9, 16, 12, 0, 0)
        self.assertTrue(
            should_queue_again(
                previous_aggregate_key="unread-dm:message-a",
                previous_created_at=previous,
                aggregate_key="unread-dm:message-b",
                now=previous + timedelta(minutes=1),
                cooldown_minutes=1440,
            )
        )

    def test_dedupe_key_changes_for_message_or_cooldown_slot(self):
        message_a = uuid4()
        message_b = uuid4()
        now = datetime(2026, 9, 16, 12, 0, 0)
        first = email_nudge_dedupe_key(message_a, now, 60)
        self.assertEqual(first, email_nudge_dedupe_key(message_a, now + timedelta(minutes=30), 60))
        self.assertNotEqual(first, email_nudge_dedupe_key(message_b, now, 60))
        self.assertNotEqual(first, email_nudge_dedupe_key(message_a, now + timedelta(minutes=61), 60))
        self.assertGreaterEqual(cooldown_slot(now, 1), 0)

    def test_delivery_ledger_does_not_persist_message_contents_or_email_address(self):
        columns = set(ExternalDeliveryLedger.__table__.columns.keys())
        self.assertNotIn("body", columns)
        self.assertNotIn("message_text", columns)
        self.assertNotIn("email", columns)
        self.assertIn("unread_count", columns)
        self.assertIn("dialog_count", columns)
        self.assertIn("provider_message_id", columns)


if __name__ == "__main__":
    unittest.main()
