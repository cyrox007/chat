import unittest

from app import app
from components.moderation.protective_hold import _ALLOWED_CAPABILITIES


class TrustSafetyOperationsContractTests(unittest.TestCase):
    def test_metrics_route_is_registered(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/trust-safety/v1/metrics", paths)

    def test_automation_surface_excludes_sensitive_capabilities(self):
        forbidden = {
            "account.access",
            "media.upload",
            "profile.edit",
            "space.create",
            "space.join",
            "discovery.publish",
            "space.chat.send",
        }
        self.assertTrue(forbidden.isdisjoint(_ALLOWED_CAPABILITIES))


if __name__ == "__main__":
    unittest.main()
