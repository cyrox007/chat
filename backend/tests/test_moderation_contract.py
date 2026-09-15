import unittest

from pydantic import ValidationError

from app import app
from components.moderation.model import ModerationAction, ModerationAppeal, ModerationReport
from components.moderation.schemas import (
    ModerationActionCreateRequest,
    ModerationAppealResolveRequest,
    ModerationReportCreateRequest,
)


class ModerationContractTests(unittest.TestCase):
    def test_versioned_moderation_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/moderation/v1/me/reports",
            "/moderation/v1/me/actions",
            "/moderation/v1/me/appeals",
            "/moderation/v1/actions/{action_uid}/appeals",
            "/moderation/v1/spaces/{space_uid}/reports",
            "/moderation/v1/spaces/{space_uid}/reports/{report_uid}",
            "/moderation/v1/spaces/{space_uid}/actions",
            "/moderation/v1/spaces/{space_uid}/appeals",
            "/moderation/v1/spaces/{space_uid}/appeals/{appeal_uid}",
        }
        self.assertTrue(expected.issubset(paths))

    def test_report_requires_a_target(self):
        with self.assertRaises(ValidationError):
            ModerationReportCreateRequest(category="spam")

    def test_action_types_are_scoped_and_duration_is_not_allowed_for_warning(self):
        with self.assertRaises(ValidationError):
            ModerationActionCreateRequest(
                target_account_uid="00000000-0000-0000-0000-000000000001",
                action_type="warning",
                reason="Проверочное предупреждение",
                duration_minutes=10,
            )
        with self.assertRaises(ValidationError):
            ModerationActionCreateRequest(
                target_account_uid="00000000-0000-0000-0000-000000000001",
                action_type="global_ban",
                reason="Недопустимое действие",
            )

    def test_appeal_decisions_are_allowlisted(self):
        for decision in ("uphold", "overturn"):
            payload = ModerationAppealResolveRequest(
                decision=decision,
                resolution="Решение проверено другим модератором",
            )
            self.assertEqual(payload.decision, decision)
        with self.assertRaises(ValidationError):
            ModerationAppealResolveRequest(
                decision="ignore",
                resolution="Недопустимое решение",
            )

    def test_one_appeal_per_action_and_appellant_is_enforced_in_db(self):
        names = {constraint.name for constraint in ModerationAppeal.__table__.constraints if constraint.name}
        self.assertIn("uq_moderation_appeal_action_appellant", names)

    def test_one_action_per_report_is_enforced_in_db(self):
        names = {constraint.name for constraint in ModerationAction.__table__.constraints if constraint.name}
        self.assertIn("uq_moderation_action_report", names)

    def test_reports_and_actions_are_space_scoped(self):
        for model in (ModerationReport, ModerationAction):
            targets = {foreign_key.target_fullname for foreign_key in model.__table__.c.room_uid.foreign_keys}
            self.assertEqual(targets, {"rooms.uid"})


if __name__ == "__main__":
    unittest.main()
