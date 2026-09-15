import unittest

from pydantic import ValidationError

from app import app
from components.space.model import SpaceMembership
from components.space.schemas import SpaceCreateRequest, SpaceUpdateRequest
from components.space.service import _slugify_tag


class SpaceContractTests(unittest.TestCase):
    def test_versioned_space_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/spaces/v1", paths)
        self.assertIn("/spaces/v1/{space_uid}", paths)
        self.assertIn("/spaces/v1/{space_uid}/join", paths)
        self.assertIn("/spaces/v1/{space_uid}/membership", paths)
        self.assertIn("/spaces/v1/{space_uid}/members", paths)
        self.assertIn("/spaces/v1/{space_uid}/members/{account_uid}", paths)

    def test_private_space_cannot_be_open_join(self):
        with self.assertRaises(ValidationError):
            SpaceCreateRequest(
                name="Закрытый клуб",
                visibility="private",
                join_policy="open",
            )

    def test_visible_name_cannot_be_only_whitespace(self):
        with self.assertRaises(ValidationError):
            SpaceCreateRequest(name="      ")

    def test_tags_are_trimmed_and_deduplicated(self):
        payload = SpaceCreateRequest(
            name="Кино по пятницам",
            tags=[" кино ", "КИНО", " авторское   кино "],
        )
        self.assertEqual(payload.tags, ["кино", "авторское кино"])

    def test_update_contract_does_not_accept_privileged_legacy_fields(self):
        fields = SpaceUpdateRequest.model_fields
        for forbidden in ("owner_uid", "rating", "is_active", "created_at"):
            self.assertNotIn(forbidden, fields)

    def test_membership_is_unique_per_space_and_account(self):
        unique_constraints = {
            constraint.name
            for constraint in SpaceMembership.__table__.constraints
            if constraint.name
        }
        self.assertIn("uq_space_membership", unique_constraints)

    def test_tag_slug_is_stable_for_unicode_and_spaces(self):
        self.assertEqual(_slugify_tag("  Авторское   кино  "), "авторское-кино")


if __name__ == "__main__":
    unittest.main()
