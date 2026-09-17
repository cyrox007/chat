import inspect
import unittest

from pydantic import ValidationError
from starlette.requests import Request

from app import app
from components.auth.middleware import auth_middle
from components.auth.permissions import validate_profile_update
from components.discovery.moderation import discover_spaces_with_moderation
from components.moderation.account_access import (
    ACCOUNT_ACCESS_HTTP_EXEMPTIONS,
    is_account_access_http_exempt,
)
from components.moderation.model import PlatformRestrictionAppeal
from components.moderation.policy import issue_platform_restriction
from components.moderation.schemas import (
    PlatformRestrictionAppealCreateRequest,
    PlatformRestrictionAppealResolveRequest,
)
from socket_manager.account_control import install_account_control
from views.identity.routers import install as install_identity_routes
from views.moderation.restriction_routers import ENFORCEMENT_READY_CAPABILITIES
from views.realtime.ws_auth import authenticate_websocket
from views.spaces.routers import install as install_space_routes


def _request(method: str, path: str) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("test", 443),
        }
    )


class PlatformRestrictionContractTests(unittest.TestCase):
    def test_restriction_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/trust-safety/v1/restrictions",
            "/trust-safety/v1/me/restrictions",
            "/trust-safety/v1/restrictions/{restriction_uid}/revoke",
            "/trust-safety/v1/restrictions/{restriction_uid}/appeals",
            "/trust-safety/v1/me/restriction-appeals",
            "/trust-safety/v1/restriction-appeals",
            "/trust-safety/v1/restriction-appeals/{appeal_uid}/claim",
            "/trust-safety/v1/restriction-appeals/{appeal_uid}/release",
            "/trust-safety/v1/restriction-appeals/{appeal_uid}",
            "/trust-safety/v1/restriction-capabilities",
        }
        self.assertTrue(expected.issubset(paths))

    def test_only_server_enforced_capabilities_are_exposed(self):
        self.assertEqual(
            ENFORCEMENT_READY_CAPABILITIES,
            frozenset(
                {
                    "messenger.send",
                    "space.chat.send",
                    "media.upload",
                    "space.create",
                    "space.join",
                    "invitation.send",
                    "profile.edit",
                    "discovery.publish",
                    "account.access",
                }
            ),
        )

    def test_http_mutation_discovery_and_account_access_hooks_exist_before_capability_is_exposed(self):
        identity_source = inspect.getsource(install_identity_routes)
        legacy_profile_source = inspect.getsource(validate_profile_update)
        spaces_source = inspect.getsource(install_space_routes)
        discovery_source = inspect.getsource(discover_spaces_with_moderation)
        auth_source = inspect.getsource(auth_middle)
        issue_source = inspect.getsource(issue_platform_restriction)
        websocket_source = inspect.getsource(authenticate_websocket)
        disconnect_source = inspect.getsource(install_account_control)

        self.assertIn('"profile.edit"', identity_source)
        self.assertIn('"profile.edit"', legacy_profile_source)
        self.assertIn('"space.create"', spaces_source)
        self.assertIn('"space.join"', spaces_source)
        self.assertIn('"invitation.send"', spaces_source)
        self.assertIn('"discovery.publish"', discovery_source)
        self.assertIn('"account.access"', discovery_source)
        self.assertIn("assert_http_account_access", auth_source)
        self.assertIn("revoke_account_sessions", issue_source)
        self.assertIn("disconnect_account_realtime", issue_source)
        self.assertIn("active_account_access_restriction", websocket_source)
        self.assertIn("private_manager.disconnect", disconnect_source)
        self.assertIn("room_manager.disconnect", disconnect_source)

    def test_account_access_exemptions_are_narrow_and_appeal_focused(self):
        self.assertEqual(
            set(ACCOUNT_ACCESS_HTTP_EXEMPTIONS),
            {
                ("GET", "/identity/v2/me"),
                ("GET", "/trust-safety/v1/me/restrictions"),
                ("GET", "/trust-safety/v1/me/restriction-appeals"),
            },
        )
        self.assertTrue(is_account_access_http_exempt(_request("GET", "/identity/v2/me")))
        self.assertTrue(
            is_account_access_http_exempt(
                _request("POST", "/trust-safety/v1/restrictions/00000000-0000-0000-0000-000000000001/appeals")
            )
        )
        self.assertFalse(is_account_access_http_exempt(_request("GET", "/spaces/v1")))
        self.assertFalse(is_account_access_http_exempt(_request("POST", "/realtime/v2/tickets")))

    def test_restriction_appeal_is_one_per_account_and_restriction(self):
        names = {
            constraint.name
            for constraint in PlatformRestrictionAppeal.__table__.constraints
            if constraint.name
        }
        self.assertIn("uq_platform_restriction_appeal_appellant", names)

    def test_restriction_appeal_payloads_are_bounded(self):
        payload = PlatformRestrictionAppealCreateRequest(
            body="Прошу пересмотреть ограничение с учётом контекста."
        )
        self.assertGreaterEqual(len(payload.body), 10)
        with self.assertRaises(ValidationError):
            PlatformRestrictionAppealCreateRequest(body="коротко")

        for decision in ("uphold", "overturn"):
            resolution = PlatformRestrictionAppealResolveRequest(
                decision=decision,
                resolution="Решение проверено по апелляции.",
            )
            self.assertEqual(resolution.decision, decision)
        with self.assertRaises(ValidationError):
            PlatformRestrictionAppealResolveRequest(
                decision="ignore",
                resolution="Недопустимое решение.",
            )


if __name__ == "__main__":
    unittest.main()
