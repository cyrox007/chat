import unittest
from datetime import datetime, timedelta

from components.notification.model import ExternalDeliveryLedger, WebPushSubscription
from components.notification.web_push import (
    build_messenger_push_payload,
    classify_web_push_exception,
    endpoint_fingerprint,
    normalize_push_endpoint,
    push_retry_delay_seconds,
)
from settings import config


class _Response:
    def __init__(self, status_code):
        self.status_code = status_code


class _PushError:
    def __init__(self, status_code):
        self.response = _Response(status_code)


class WebPushContractTests(unittest.TestCase):
    def test_payload_is_privacy_minimal_and_points_to_messenger(self):
        payload = build_messenger_push_payload()
        serialized = repr(payload)
        self.assertEqual(payload["url"], "/messenger")
        self.assertEqual(payload["type"], "messenger")
        self.assertNotIn("message_text", serialized)
        self.assertNotIn("sender_name", serialized)
        self.assertNotIn("secret-private-body", serialized)

    def test_regular_http_push_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_push_endpoint("http://push.example.test/subscription")
        self.assertEqual(
            normalize_push_endpoint("https://push.example.test/subscription"),
            "https://push.example.test/subscription",
        )

    def test_endpoint_fingerprint_is_stable_and_not_plain_endpoint(self):
        endpoint = "https://push.example.test/device/secret-token"
        first = endpoint_fingerprint(endpoint)
        self.assertEqual(first, endpoint_fingerprint(endpoint))
        self.assertEqual(len(first), 64)
        self.assertNotIn("secret-token", first)

    def test_terminal_subscription_statuses_are_removed_not_retried(self):
        for code in (404, 410):
            error = classify_web_push_exception(_PushError(code))
            self.assertTrue(error.terminal_subscription)
            self.assertFalse(error.retryable)

    def test_throttle_and_provider_outage_are_retryable(self):
        for code in (429, 500, 503):
            error = classify_web_push_exception(_PushError(code))
            self.assertTrue(error.retryable)
            self.assertFalse(error.terminal_subscription)

    def test_retry_delay_is_exponential_and_capped(self):
        first = push_retry_delay_seconds(1)
        second = push_retry_delay_seconds(2)
        very_late = push_retry_delay_seconds(100)
        self.assertEqual(first, config.WEB_PUSH_DELIVERY_RETRY_BASE_SECONDS)
        self.assertGreaterEqual(second, first)
        self.assertLessEqual(very_late, config.WEB_PUSH_DELIVERY_RETRY_MAX_SECONDS)

    def test_subscription_credentials_do_not_expand_delivery_ledger(self):
        subscription_columns = set(WebPushSubscription.__table__.columns.keys())
        ledger_columns = set(ExternalDeliveryLedger.__table__.columns.keys())
        self.assertTrue({"endpoint", "endpoint_hash", "p256dh", "auth"}.issubset(subscription_columns))
        self.assertNotIn("endpoint", ledger_columns)
        self.assertNotIn("p256dh", ledger_columns)
        self.assertNotIn("auth", ledger_columns)
        self.assertNotIn("message_text", ledger_columns)

    def test_conversation_cooldown_has_safe_minimum(self):
        self.assertGreaterEqual(config.WEB_PUSH_CONVERSATION_COOLDOWN_SECONDS, 30)
        now = datetime(2026, 9, 16, 12, 0, 0)
        self.assertGreater(
            now + timedelta(seconds=config.WEB_PUSH_CONVERSATION_COOLDOWN_SECONDS),
            now,
        )


if __name__ == "__main__":
    unittest.main()
