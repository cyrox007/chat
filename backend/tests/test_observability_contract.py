import json
import unittest

from utils.observability import structured_event


class ObservabilityContractTests(unittest.TestCase):
    def test_structured_event_is_machine_readable_and_privacy_minimal(self):
        payload = json.loads(
            structured_event(
                "external_delivery.web_push.delivery_complete",
                infrastructure_ready=True,
                claimed=4,
                delivered=3,
                failed=1,
            )
        )
        self.assertEqual(
            payload["event"],
            "external_delivery.web_push.delivery_complete",
        )
        self.assertEqual(payload["claimed"], 4)
        self.assertEqual(payload["delivered"], 3)

    def test_sensitive_field_names_are_rejected(self):
        forbidden = {
            "access_token": "secret",
            "destination_email": "user@example.test",
            "push_endpoint": "https://push.example.test/device",
            "message_body": "private text",
            "authorization_header": "Bearer secret",
        }
        for key, value in forbidden.items():
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    structured_event("unsafe", **{key: value})


if __name__ == "__main__":
    unittest.main()
