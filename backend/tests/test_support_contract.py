import unittest

from app import app
from components.support.model import (
    CosmeticEntitlement,
    CreatorSupportProfile,
    GiftDefinition,
    SpaceSupportSettings,
    SupportLedgerEntry,
)
from components.support.schemas import GiftSendRequest
from components.support.service import MAX_GIFTS_PER_DAY


class SupportContractTests(unittest.TestCase):
    def test_support_routes_are_registered(self):
        route_methods = {
            (route.path, method)
            for route in app.routes
            for method in (getattr(route, "methods", None) or set())
        }
        expected = {
            ("/support/v1/catalog", "GET"),
            ("/support/v1/me/profile", "GET"),
            ("/support/v1/me/profile", "PATCH"),
            ("/support/v1/me/received", "GET"),
            ("/support/v1/personas/{persona_uid}/shelf", "GET"),
            ("/support/v1/personas/{persona_uid}/gifts", "POST"),
            ("/support/v1/spaces/{space_uid}/settings", "GET"),
            ("/support/v1/spaces/{space_uid}/settings", "PATCH"),
            ("/support/v1/spaces/{space_uid}/shelf", "GET"),
            ("/support/v1/spaces/{space_uid}/gifts", "POST"),
            ("/support/v1/spaces/{space_uid}/received", "GET"),
        }
        self.assertTrue(expected.issubset(route_methods))

    def test_writable_gift_contract_has_no_financial_or_power_fields(self):
        forbidden = {
            "price", "amount", "currency", "balance", "points", "score",
            "rank", "trust", "role", "permission", "payment", "winner", "prize",
        }
        self.assertTrue(forbidden.isdisjoint(GiftSendRequest.model_fields))
        self.assertTrue(forbidden.isdisjoint(GiftDefinition.__table__.columns.keys()))

    def test_support_ledger_has_no_mutation_routes(self):
        for route in app.routes:
            if not route.path.startswith("/support/v1"):
                continue
            methods = getattr(route, "methods", set()) or set()
            self.assertNotIn("DELETE", methods)
            if "PATCH" in methods:
                self.assertTrue(route.path.endswith("/profile") or route.path.endswith("/settings"))

    def test_support_is_opt_in_by_default(self):
        self.assertFalse(CreatorSupportProfile.__table__.c.enabled.default.arg)
        self.assertFalse(SpaceSupportSettings.__table__.c.enabled.default.arg)

    def test_exact_target_constraints_exist(self):
        ledger_constraints = {
            constraint.name for constraint in SupportLedgerEntry.__table__.constraints if constraint.name
        }
        entitlement_constraints = {
            constraint.name for constraint in CosmeticEntitlement.__table__.constraints if constraint.name
        }
        self.assertIn("ck_support_ledger_exact_target", ledger_constraints)
        self.assertIn("ck_cosmetic_entitlement_exact_target", entitlement_constraints)

    def test_internal_gift_rate_limit_is_bounded(self):
        self.assertGreater(MAX_GIFTS_PER_DAY, 0)
        self.assertLessEqual(MAX_GIFTS_PER_DAY, 20)

    def test_support_api_has_no_payment_or_balance_routes(self):
        paths = {route.path.casefold() for route in app.routes if route.path.startswith("/support/v1")}
        forbidden_terms = ("payment", "checkout", "balance", "wallet", "currency", "price")
        self.assertFalse(any(any(term in path for term in forbidden_terms) for path in paths))


if __name__ == "__main__":
    unittest.main()
