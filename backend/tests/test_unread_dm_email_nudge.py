import smtplib
import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from components.notification.email_provider import (
    EmailDeliveryRequest,
    _classify_smtp_exception,
    build_unread_dm_email,
    deterministic_message_id,
)
from components.notification.model import ExternalDeliveryLedger
from components.notification.unread_dm_email import (
    cooldown_slot,
    email_nudge_dedupe_key,
    retry_delay_seconds,
    should_queue_again,
)
from settings import config


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

    def test_delivery_ledger_is_privacy_minimal_and_has_claim_lease(self):
        columns = set(ExternalDeliveryLedger.__table__.columns.keys())
        self.assertNotIn("body", columns)
        self.assertNotIn("message_text", columns)
        self.assertNotIn("email", columns)
        self.assertIn("unread_count", columns)
        self.assertIn("dialog_count", columns)
        self.assertIn("provider_message_id", columns)
        self.assertIn("claim_token", columns)
        self.assertIn("claim_expires_at", columns)

    def test_retry_delay_is_exponential_and_capped(self):
        first = retry_delay_seconds(1)
        second = retry_delay_seconds(2)
        very_late = retry_delay_seconds(100)
        self.assertEqual(first, config.MESSAGE_EMAIL_DELIVERY_RETRY_BASE_SECONDS)
        self.assertGreaterEqual(second, first)
        self.assertLessEqual(very_late, config.MESSAGE_EMAIL_DELIVERY_RETRY_MAX_SECONDS)

    def test_smtp_error_classification_distinguishes_retryable_and_terminal(self):
        temporary = _classify_smtp_exception(smtplib.SMTPResponseException(451, b"temporary"))
        permanent = _classify_smtp_exception(smtplib.SMTPResponseException(550, b"permanent"))
        auth = _classify_smtp_exception(smtplib.SMTPAuthenticationError(535, b"bad auth"))
        self.assertTrue(temporary.retryable)
        self.assertFalse(permanent.retryable)
        self.assertFalse(auth.retryable)

    def test_email_template_contains_counts_but_never_private_message_text(self):
        previous_from_email = config.MESSAGE_EMAIL_FROM_EMAIL
        previous_from_name = config.MESSAGE_EMAIL_FROM_NAME
        previous_frontend = config.FRONTEND_URL
        try:
            config.MESSAGE_EMAIL_FROM_EMAIL = "notify@example.test"
            config.MESSAGE_EMAIL_FROM_NAME = "PubChat"
            config.FRONTEND_URL = ["https://pubchat.example"]
            delivery_uid = uuid4()
            request = EmailDeliveryRequest(
                delivery_uid=delivery_uid,
                recipient="recipient@example.test",
                unread_count=7,
                dialog_count=2,
            )
            message = build_unread_dm_email(request)
            plain = message.get_body(preferencelist=("plain",)).get_content()
            html = message.get_body(preferencelist=("html",)).get_content()
            decoded = f"{plain}\n{html}"
            self.assertIn("7", decoded)
            self.assertIn("2", decoded)
            self.assertNotIn("secret-message-body", decoded)
            self.assertIn("/messenger", plain)
            self.assertIn("/messenger", html)
            self.assertEqual(
                message["Message-ID"],
                deterministic_message_id(delivery_uid, "notify@example.test"),
            )
        finally:
            config.MESSAGE_EMAIL_FROM_EMAIL = previous_from_email
            config.MESSAGE_EMAIL_FROM_NAME = previous_from_name
            config.FRONTEND_URL = previous_frontend


if __name__ == "__main__":
    unittest.main()
