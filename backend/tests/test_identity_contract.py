import unittest

from pydantic import ValidationError

from app import app
from components.identity.schemas import PrivacyUpdateRequest, RegisterRequest


class IdentityContractTests(unittest.TestCase):
    def test_registration_is_persona_first_and_email_optional(self):
        payload = RegisterRequest(
            handle="alex.pub",
            display_name="Alex",
            password="correct-horse-battery-staple",
            social_intent="open",
        )
        self.assertEqual(payload.handle, "alex.pub")
        self.assertIsNone(payload.email)
        self.assertEqual(payload.display_name, "Alex")

    def test_registration_rejects_unsafe_handle(self):
        with self.assertRaises(ValidationError):
            RegisterRequest(
                handle="Alex with spaces",
                password="long-enough-password",
            )

    def test_privacy_contract_rejects_unknown_dm_policy(self):
        with self.assertRaises(ValidationError):
            PrivacyUpdateRequest(dm_policy="pay_to_message")

    def test_identity_routes_are_registered_and_sensitive_legacy_reads_are_gone(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/identity/v2/register", paths)
        self.assertIn("/identity/v2/me", paths)
        self.assertIn("/identity/v2/profiles/{account_uid}", paths)
        self.assertIn("/identity/v2/personas/batch", paths)
        self.assertNotIn("/users/by-uids", paths)
        self.assertNotIn("/users/{user_uid}", paths)


if __name__ == "__main__":
    unittest.main()
