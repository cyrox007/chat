import unittest

from pydantic import ValidationError

from app import app
from components.moderation.model import (
    ModerationAction,
    ModerationAppeal,
    ModerationReport,
    TrustSafetyAuditEvent,
    TrustSafetyReport,
)
from components.moderation.schemas import (
    ModerationActionCreateRequest,
    ModerationAppealResolveRequest,
    ModerationReportCreateRequest,
    TrustSafetyDecisionRequest,
    TrustSafetyReportCreateRequest,
)
from components.moderation.trust_safety import trust_safety_priority


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

    def test_platform_trust_safety_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/trust-safety/v1/reports",
            "/trust-safety/v1/me/reports",
            "/trust-safety/v1/queue",
            "/trust-safety/v1/reports/{report_uid}/claim",
            "/trust-safety/v1/reports/{report_uid}/release",
            "/trust-safety/v1/reports/{report_uid}/evidence",
            "/trust-safety/v1/reports/{report_uid}",
            "/trust-safety/v1/reports/{report_uid}/audit",
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

    def test_platform_report_source_and_priority_are_server_owned(self):
        report = TrustSafetyReportCreateRequest(
            source_type="messenger_message",
            source_uid="00000000-0000-0000-0000-000000000011",
            category="harassment",
            description="Нежелательное сообщение",
        )
        self.assertEqual(report.source_type, "messenger_message")
        self.assertFalse(hasattr(report, "priority"))

        with self.assertRaises(ValidationError):
            TrustSafetyReportCreateRequest(
                source_type="persona",
                source_uid="00000000-0000-0000-0000-000000000012",
                category="spam",
                priority="high",
            )
        with self.assertRaises(ValidationError):
            TrustSafetyReportCreateRequest(
                source_type="arbitrary_private_object",
                source_uid="00000000-0000-0000-0000-000000000013",
                category="privacy",
            )

    def test_platform_priority_is_deterministic(self):
        self.assertEqual(trust_safety_priority("minor_safety"), "high")
        self.assertEqual(trust_safety_priority("violence"), "high")
        self.assertEqual(trust_safety_priority("harassment"), "normal")
        self.assertEqual(trust_safety_priority("spam"), "low")

    def test_platform_decision_requires_coherent_escalation(self):
        item = TrustSafetyDecisionRequest(
            status="escalated",
            resolution_code="needs_platform_action",
            public_explanation="Требуется дополнительная проверка команды безопасности.",
        )
        self.assertEqual(item.status, "escalated")
        with self.assertRaises(ValidationError):
            TrustSafetyDecisionRequest(
                status="escalated",
                resolution_code="no_violation",
                public_explanation="Некорректное сочетание.",
            )

    def test_platform_moderation_is_separate_and_audited(self):
        report_columns = set(TrustSafetyReport.__table__.c.keys())
        self.assertIn("source_type", report_columns)
        self.assertIn("source_uid", report_columns)
        self.assertIn("assigned_to_account_uid", report_columns)
        self.assertNotIn("room_uid", report_columns)

        audit_columns = set(TrustSafetyAuditEvent.__table__.c.keys())
        self.assertIn("report_uid", audit_columns)
        self.assertIn("event_type", audit_columns)
        self.assertNotIn("updated_at", audit_columns)
        targets = {
            foreign_key.target_fullname
            for foreign_key in TrustSafetyAuditEvent.__table__.c.report_uid.foreign_keys
        }
        self.assertEqual(targets, {"trust_safety_reports.uid"})


if __name__ == "__main__":
    unittest.main()
