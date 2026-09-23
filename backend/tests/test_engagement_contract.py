import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from app import app
from components.engagement.batch import SpaceAppearanceBatchRequest
from components.engagement.model import ActivityRSVP, PersonaAppearance, SpaceActivity, SpaceAppearance
from components.engagement.schemas import (
    ActivityCreateRequest,
    ActivityRSVPRequest,
    ActivityUpdateRequest,
    PersonaAppearanceUpdateRequest,
    SpaceAppearanceUpdateRequest,
)
from components.engagement.recurrence import occurrences_between
from components.engagement.service import _next_occurrence


class EngagementContractTests(unittest.TestCase):
    def test_versioned_engagement_routes_are_registered(self):
        route_methods = {
            (route.path, method)
            for route in app.routes
            for method in (getattr(route, "methods", None) or set())
        }
        expected = {
            ("/appearance/v1/me/persona", "GET"),
            ("/appearance/v1/me/persona", "PATCH"),
            ("/appearance/v1/personas/{persona_uid}", "GET"),
            ("/appearance/v1/spaces/batch", "POST"),
            ("/appearance/v1/spaces/{space_uid}", "GET"),
            ("/appearance/v1/spaces/{space_uid}", "PATCH"),
            ("/activities/v1/spaces/{space_uid}", "GET"),
            ("/activities/v1/spaces/{space_uid}", "POST"),
            ("/activities/v1/spaces/{space_uid}/{activity_uid}", "PATCH"),
            ("/activities/v1/{activity_uid}/rsvp", "PUT"),
            ("/activities/v1/{activity_uid}/rsvp", "DELETE"),
        }
        self.assertTrue(expected.issubset(route_methods))

    def test_persona_appearance_is_cosmetic_only(self):
        fields = PersonaAppearanceUpdateRequest.model_fields
        for forbidden in ("trust_level", "role", "permissions", "rating", "reputation"):
            self.assertNotIn(forbidden, fields)

    def test_space_appearance_is_cosmetic_only(self):
        fields = SpaceAppearanceUpdateRequest.model_fields
        for forbidden in ("owner_uid", "member_limit", "join_policy", "visibility", "rating"):
            self.assertNotIn(forbidden, fields)

    def test_space_appearance_batch_is_bounded_and_deduplicated(self):
        payload = SpaceAppearanceBatchRequest(
            space_uids=[
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000002",
            ]
        )
        self.assertEqual(len(payload.space_uids), 2)
        with self.assertRaises(ValidationError):
            SpaceAppearanceBatchRequest(space_uids=[])
        with self.assertRaises(ValidationError):
            SpaceAppearanceBatchRequest(
                space_uids=[f"00000000-0000-0000-0000-{index:012d}" for index in range(101)]
            )

    def test_activity_types_rsvp_and_timezone_are_allowlisted(self):
        payload = ActivityCreateRequest(
            title="Вечер викторины",
            activity_type="quiz",
            starts_at="2026-09-20T18:00:00Z",
            recurrence="weekly",
        )
        self.assertEqual(payload.activity_type, "quiz")
        self.assertEqual(payload.recurrence, "weekly")
        self.assertEqual(payload.timezone, "UTC")
        self.assertEqual(ActivityRSVPRequest(status="going").status, "going")
        with self.assertRaises(ValidationError):
            ActivityRSVPRequest(status="paid_priority")
        with self.assertRaises(ValidationError):
            ActivityCreateRequest(title="Без зоны", starts_at="2026-09-20T18:00:00")
        with self.assertRaises(ValidationError):
            ActivityUpdateRequest(starts_at="2026-09-20T18:00:00")
        with self.assertRaises(ValidationError):
            ActivityCreateRequest(
                title="Неверная зона",
                starts_at="2026-09-20T18:00:00Z",
                timezone="Europe/Not-A-Real-City",
            )

    def test_recurring_activity_projects_next_occurrence_without_rows(self):
        now = datetime(2026, 9, 15, 17, 0, tzinfo=timezone.utc)
        weekly = _next_occurrence(
            datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc),
            "weekly",
            now,
        )
        monthly = _next_occurrence(
            datetime(2026, 1, 31, 18, 0, tzinfo=timezone.utc),
            "monthly",
            datetime(2026, 2, 15, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(weekly, datetime(2026, 9, 15, 18, 0))
        self.assertEqual(monthly, datetime(2026, 2, 28, 18, 0))

    def test_weekly_recurrence_preserves_local_wall_clock_across_dst(self):
        next_start = _next_occurrence(
            datetime(2026, 3, 23, 18, 0, tzinfo=timezone.utc),
            "weekly",
            datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc),
            timezone_name="Europe/Amsterdam",
        )
        # 19:00 Europe/Amsterdam is 18:00 UTC before DST and 17:00 UTC after it.
        self.assertEqual(next_start, datetime(2026, 3, 30, 17, 0))

    def test_nonexistent_spring_forward_wall_time_shifts_only_that_occurrence(self):
        values = occurrences_between(
            datetime(2026, 3, 28, 1, 30, tzinfo=timezone.utc),
            "daily",
            datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 30, 23, 0, tzinfo=timezone.utc),
            timezone_name="Europe/Amsterdam",
        )
        self.assertEqual(
            values,
            [
                datetime(2026, 3, 28, 1, 30),
                datetime(2026, 3, 29, 1, 30),  # local 02:30 -> 03:30 gap shift
                datetime(2026, 3, 30, 0, 30),  # local 02:30 restored
            ],
        )

    def test_monthly_recurrence_preserves_wall_clock_and_anchor_day_across_dst(self):
        values = occurrences_between(
            datetime(2026, 1, 31, 18, 0, tzinfo=timezone.utc),
            "monthly",
            datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
            timezone_name="Europe/Amsterdam",
        )
        self.assertEqual(
            values,
            [
                datetime(2026, 2, 28, 18, 0),  # local 19:00 CET, clamped to month end
                datetime(2026, 3, 31, 17, 0),  # local 19:00 CEST after DST
            ],
        )

    def test_ambiguous_fall_back_wall_time_uses_first_occurrence(self):
        values = occurrences_between(
            datetime(2026, 10, 24, 0, 30, tzinfo=timezone.utc),
            "daily",
            datetime(2026, 10, 24, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 10, 26, 3, 0, tzinfo=timezone.utc),
            timezone_name="Europe/Amsterdam",
        )
        self.assertEqual(
            values,
            [
                datetime(2026, 10, 24, 0, 30),
                datetime(2026, 10, 25, 0, 30),  # first local 02:30 (CEST)
                datetime(2026, 10, 26, 1, 30),  # local 02:30 (CET)
            ],
        )

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
