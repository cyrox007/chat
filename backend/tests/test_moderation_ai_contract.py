import unittest

from pydantic import ValidationError

from app import app
from components.moderation.ai_model import ModerationAIRecommendation
from components.moderation.schemas import ModerationAIAssessment, ModerationAIOutcomeRequest


class ModerationAIContractTests(unittest.TestCase):
    def test_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/trust-safety/v1/ai-assessment/config",
            "/trust-safety/v1/reports/{report_uid}/ai-assessments",
            "/trust-safety/v1/reports/{report_uid}/ai-assessments/{recommendation_uid}",
        }
        self.assertTrue(expected.issubset(paths))

    def test_assessment_is_advisory_and_cannot_suggest_account_access(self):
        item = ModerationAIAssessment(
            category="harassment",
            severity="medium",
            confidence_percent=82,
            summary="Repeated hostile language in the reported message.",
            recommended_action="temporary_restriction",
            suggested_capability="messenger.send",
            suggested_scope_type="platform",
            suggested_duration_minutes=1440,
            rationale="A temporary messaging restriction is proportionate to the reported evidence.",
        )
        self.assertEqual(item.recommended_action, "temporary_restriction")
        with self.assertRaises(ValidationError):
            ModerationAIAssessment(
                category="harassment",
                severity="critical",
                confidence_percent=99,
                summary="Attempted full account suspension.",
                recommended_action="temporary_restriction",
                suggested_capability="account.access",
                suggested_scope_type="platform",
                suggested_duration_minutes=1440,
                rationale="AI must never recommend the strongest punitive capability.",
            )

    def test_none_action_cannot_smuggle_restriction_fields(self):
        with self.assertRaises(ValidationError):
            ModerationAIAssessment(
                category="other",
                severity="low",
                confidence_percent=25,
                summary="No clear violation.",
                recommended_action="none",
                suggested_capability="messenger.send",
                suggested_scope_type="platform",
                suggested_duration_minutes=60,
                rationale="No action should carry no sanction suggestion.",
            )

    def test_outcome_is_human_feedback_only(self):
        for outcome in ("not_used", "accepted", "modified", "rejected"):
            payload = ModerationAIOutcomeRequest(outcome=outcome, note="Moderator feedback.")
            self.assertEqual(payload.outcome, outcome)
        with self.assertRaises(ValidationError):
            ModerationAIOutcomeRequest(outcome="executed")

    def test_storage_has_no_raw_prompt_or_private_history_columns(self):
        columns = set(ModerationAIRecommendation.__table__.columns.keys())
        forbidden = {
            "prompt",
            "raw_prompt",
            "raw_response",
            "chain_of_thought",
            "conversation_history",
            "attachment_url",
        }
        self.assertTrue(forbidden.isdisjoint(columns))


if __name__ == "__main__":
    unittest.main()
