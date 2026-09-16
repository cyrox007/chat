import unittest

from app import app
from views.moderation.restriction_routers import ENFORCEMENT_READY_CAPABILITIES


class PlatformRestrictionContractTests(unittest.TestCase):
    def test_restriction_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/trust-safety/v1/restrictions",
            "/trust-safety/v1/me/restrictions",
            "/trust-safety/v1/restrictions/{restriction_uid}/revoke",
            "/trust-safety/v1/restriction-capabilities",
        }
        self.assertTrue(expected.issubset(paths))

    def test_only_server_enforced_capabilities_are_exposed(self):
        self.assertEqual(
            ENFORCEMENT_READY_CAPABILITIES,
            frozenset({"messenger.send", "space.chat.send", "media.upload"}),
        )
        self.assertNotIn("account.access", ENFORCEMENT_READY_CAPABILITIES)
        self.assertNotIn("profile.edit", ENFORCEMENT_READY_CAPABILITIES)


if __name__ == "__main__":
    unittest.main()
