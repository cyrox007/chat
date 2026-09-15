import unittest

from pydantic import ValidationError

from app import app
from components.engagement.model import ActivityRSVP, PersonaAppearance, SpaceActivity, SpaceAppearance
from components.engagement.schemas import (
    ActivityCreateRequest,
    ActivityRSVPRequest,
    PersonaAppearanceUpdateRequest,
    SpaceAppearanceUpdateRequest,
)


class EngagementContractTests(unittest.TestCase):
    def test_versioned_engagement_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/appearance/v1/personas/{persona_uid}",
            "/appearance/v1/me/persona",
            "/appearance/v1/spaces/{space_uid}",
            "/activities/v1/spaces/{space_uid}",
            "/activities/v1/spaces/{space_uid}/{activity_uid}",
            "/activities/v1/{activity_uid}/rsvp",
        }
        self.assertTrue(expected.issubset(paths))

    def test_persona_appearance_is_cosmetic_only(self):
        fields = PersonaAppearanceUpdateRequest.model_fields
        for forbidden in ("trust_level", "role", "permissions", "rating", "reputation"):
            self.assertNotIn(forbidden, fields)

    def test_space_appearance_is_cosmetic_only(self):
        fields = SpaceAppearanceUpdateRequest.model_fields
        for forbidden in ("owner_uid", "member_limit", "join_policy", "visibility", "rating"):
            self.assertNotIn(forbidden, fields)

    def test_activity_types_and_rsvp_are_allowlisted(self):
        payload = ActivityCreateRequest(
            title="Вечер викторины",
            activity_type="quiz",
            starts_at="2026-09-20T18:00:00Z",
            recurrence="weekly",
        )
        self.assertEqual(payload.activity_type, "quiz")
        self.assertEqual(payload.recurrence, "weekly")
        self.assertEqual(ActivityRSVPRequest(status="going").status, "going")
        with self.assertRaises(ValidationError):
            ActivityRSVPRequest(status="paid_priority")

    def test_appearance_and_activity_fk_boundaries(self):
        persona_targets = {fk.target_fullname for fk in PersonaAppearance.__table__.c.persona_uid.foreign_keys}
        space_targets = {fk.target_fullname for fk in SpaceAppearance.__table__.c.room_uid.foreign_keys}
        activity_targets = {fk.target_fullname for fk in SpaceActivity.__table__.c.room_uid.foreign_keys}
        self.assertEqual(persona_targets, {"personas.uid"})
        self.assertEqual(space_targets, {"rooms.uid"})
        self.assertEqual(activity_targets, {"rooms.uid"})

    def test_activity_rsvp_is_unique_per_account(self):
        primary_keys = {column.name for column in ActivityRSVP.__table__.primary_key.columns}
        self.assertEqual(primary_keys, {"activity_uid", "account_uid"})


if __name__ == "__main__":
    unittest.main()
