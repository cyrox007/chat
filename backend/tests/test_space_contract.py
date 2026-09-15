import unittest

from pydantic import ValidationError

from app import app
from components.space.invitation_schemas import SpaceInvitationActionRequest
from components.space.membership_schemas import SpaceMembershipActionRequest
from components.space.model import SpaceInvitation, SpaceMembership
from components.space.schemas import SpaceCreateRequest, SpaceUpdateRequest
from components.space.service import _slugify_tag


class SpaceContractTests(unittest.TestCase):
    def test_versioned_space_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/spaces/v1", paths)
        self.assertIn("/spaces/v1/invitations", paths)
        self.assertIn("/spaces/v1/invitations/{invitation_uid}", paths)
        self.assertIn("/spaces/v1/{space_uid}", paths)
        self.assertIn("/spaces/v1/{space_uid}/join", paths)
        self.assertIn("/spaces/v1/{space_uid}/membership", paths)
        self.assertIn("/spaces/v1/{space_uid}/members", paths)
        self.assertIn("/spaces/v1/{space_uid}/members/{account_uid}", paths)
        self.assertIn("/spaces/v1/{space_uid}/members/{account_uid}/membership", paths)
        self.assertIn("/spaces/v1/{space_uid}/invitations/{account_uid}", paths)

    def test_private_space_is_invite_only(self):
        for invalid_policy in ("open", "request"):
            with self.assertRaises(ValidationError):
                SpaceCreateRequest(
                    name="Закрытый клуб",
                    visibility="private",
                    join_policy=invalid_policy,
                )

        payload = SpaceCreateRequest(
            name="Закрытый клуб",
            visibility="private",
            join_policy="invite",
        )
        self.assertEqual(payload.join_policy, "invite")

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
        names = {
            constraint.name
            for constraint in SpaceMembership.__table__.constraints
            if constraint.name
        }
        self.assertIn("uq_space_membership", names)

    def test_invitation_is_unique_per_space_and_invitee(self):
        names = {
            constraint.name
            for constraint in SpaceInvitation.__table__.constraints
            if constraint.name
        }
        self.assertIn("uq_space_invitation_invitee", names)

    def test_membership_actions_are_allowlisted(self):
        for action in ("approve", "reject", "remove"):
            self.assertEqual(SpaceMembershipActionRequest(action=action).action, action)
        with self.assertRaises(ValidationError):
            SpaceMembershipActionRequest(action="ban")

    def test_invitation_actions_are_allowlisted(self):
        for action in ("accept", "decline"):
            self.assertEqual(SpaceInvitationActionRequest(action=action).action, action)
        with self.assertRaises(ValidationError):
            SpaceInvitationActionRequest(action="forward")

    def test_tag_slug_is_stable_for_unicode_and_spaces(self):
        self.assertEqual(_slugify_tag("  Авторское   кино  "), "авторское-кино")


if __name__ == "__main__":
    unittest.main()
