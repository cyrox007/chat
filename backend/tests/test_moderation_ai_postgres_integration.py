import asyncio
import json
import os
import unittest
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select

from components.identity.model import Account, Persona
from components.model_registry import ensure_models_registered
from components.moderation.ai_copilot import (
    ModerationAIProviderError,
    create_moderation_ai_assessment,
    set_moderation_ai_outcome,
)
from components.moderation.ai_model import ModerationAIRecommendation
from components.moderation.model import TrustSafetyAuditEvent, TrustSafetyReport
from components.moderation.schemas import ModerationAIAssessment, ModerationAIOutcomeRequest
from database import Database


class FailingModerationAIProvider:
    key = "failing_test"
    model_name = "offline-v1"

    async def assess(self, payload: dict):
        raise ModerationAIProviderError("simulated provider outage")


class FakeModerationAIProvider:
    key = "fake_test"
    model_name = "deterministic-v1"

    def __init__(self):
        self.payload = None

    async def assess(self, payload: dict) -> ModerationAIAssessment:
        self.payload = payload
        return ModerationAIAssessment(
            category="harassment",
            severity="medium",
            confidence_percent=87,
            summary="Reported profile text may contain targeted harassment.",
            recommended_action="temporary_restriction",
            suggested_capability="profile.edit",
            suggested_scope_type="platform",
            suggested_duration_minutes=1440,
            rationale="A bounded restriction is suggested for human review.",
        )


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class ModerationAIPostgresIntegrationTests(unittest.TestCase):
    def test_assessment_is_privacy_bounded_advisory_and_audited(self):
        async def run_case():
            ensure_models_registered()
            reporter_uid = uuid4()
            target_uid = uuid4()
            moderator_uid = uuid4()
            persona_uid = uuid4()
            report_uid = uuid4()
            handle = f"ai-target-{target_uid.hex[:12]}"
            provider = FakeModerationAIProvider()

            async with Database.sessionmaker()() as setup_db:
                setup_db.add_all(
                    [
                        Account(uid=reporter_uid, status="active", trust_level="new"),
                        Account(uid=target_uid, status="active", trust_level="new"),
                        Account(uid=moderator_uid, status="active", trust_level="new"),
                    ]
                )
                await setup_db.flush()
                setup_db.add(
                    Persona(
                        uid=persona_uid,
                        account_uid=target_uid,
                        handle=handle,
                        display_name="AI test target",
                        bio="Targeted insulting text used only as reported evidence.",
                        social_intent="open",
                        is_primary=True,
                    )
                )
                setup_db.add(
                    TrustSafetyReport(
                        uid=report_uid,
                        reporter_account_uid=reporter_uid,
                        target_account_uid=target_uid,
                        source_type="persona",
                        source_uid=persona_uid,
                        category="harassment",
                        priority="normal",
                        description="Please review this reported profile.",
                        status="in_review",
                        assigned_to_account_uid=moderator_uid,
                    )
                )
                await setup_db.commit()

            try:
                async with Database.sessionmaker()() as db:
                    item = await create_moderation_ai_assessment(
                        db,
                        report_uid,
                        moderator_uid,
                        provider=provider,
                    )
                    self.assertEqual(item["provider"], "fake_test")
                    self.assertEqual(item["outcome"], "not_used")
                    recommendation_uid = item["uid"]

                self.assertIsNotNone(provider.payload)
                serialized_payload = json.dumps(provider.payload, ensure_ascii=False)
                self.assertNotIn(str(reporter_uid), serialized_payload)
                self.assertNotIn(str(target_uid), serialized_payload)
                self.assertNotIn(str(moderator_uid), serialized_payload)
                self.assertNotIn(handle, serialized_payload)
                self.assertNotIn("account.access", provider.payload["constraints"]["allowed_actions"])
                self.assertIn("account.access", provider.payload["constraints"]["forbidden_capabilities"])
                self.assertEqual(
                    provider.payload["evidence"].get("profile", {}).get("bio"),
                    "Targeted insulting text used only as reported evidence.",
                )

                async with Database.sessionmaker()() as db:
                    updated = await set_moderation_ai_outcome(
                        db,
                        report_uid,
                        recommendation_uid,
                        moderator_uid,
                        ModerationAIOutcomeRequest(
                            outcome="modified",
                            note="Human moderator chose a different action.",
                        ),
                    )
                    self.assertEqual(updated["outcome"], "modified")

                async with Database.sessionmaker()() as verify_db:
                    stored = (
                        await verify_db.execute(
                            select(ModerationAIRecommendation).where(
                                ModerationAIRecommendation.report_uid == report_uid
                            )
                        )
                    ).scalar_one()
                    self.assertEqual(stored.model_name, "deterministic-v1")
                    self.assertEqual(stored.outcome, "modified")
                    events = list(
                        (
                            await verify_db.execute(
                                select(TrustSafetyAuditEvent.event_type).where(
                                    TrustSafetyAuditEvent.report_uid == report_uid
                                )
                            )
                        ).scalars().all()
                    )
                    self.assertIn("ai_assessment_created", events)
                    self.assertIn("ai_recommendation_outcome", events)
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    await cleanup_db.execute(
                        delete(TrustSafetyAuditEvent).where(
                            TrustSafetyAuditEvent.report_uid == report_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(ModerationAIRecommendation).where(
                            ModerationAIRecommendation.report_uid == report_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(TrustSafetyReport).where(TrustSafetyReport.uid == report_uid)
                    )
                    await cleanup_db.execute(delete(Persona).where(Persona.uid == persona_uid))
                    await cleanup_db.execute(
                        delete(Account).where(
                            Account.uid.in_([reporter_uid, target_uid, moderator_uid])
                        )
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


    def test_provider_failure_is_audited_without_creating_recommendation_or_changing_claim(self):
        async def run_case():
            ensure_models_registered()
            target_uid = uuid4()
            moderator_uid = uuid4()
            persona_uid = uuid4()
            report_uid = uuid4()

            async with Database.sessionmaker()() as setup_db:
                setup_db.add_all(
                    [
                        Account(uid=target_uid, status="active", trust_level="new"),
                        Account(uid=moderator_uid, status="active", trust_level="new"),
                    ]
                )
                await setup_db.flush()
                setup_db.add(
                    Persona(
                        uid=persona_uid,
                        account_uid=target_uid,
                        handle=f"ai-failure-{target_uid.hex[:10]}",
                        display_name="AI failure target",
                        bio="Reported evidence.",
                        social_intent="open",
                        is_primary=True,
                    )
                )
                setup_db.add(
                    TrustSafetyReport(
                        uid=report_uid,
                        reporter_account_uid=None,
                        target_account_uid=target_uid,
                        source_type="persona",
                        source_uid=persona_uid,
                        category="harassment",
                        priority="normal",
                        description="provider outage rehearsal",
                        status="in_review",
                        assigned_to_account_uid=moderator_uid,
                    )
                )
                await setup_db.commit()

            try:
                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await create_moderation_ai_assessment(
                            db,
                            report_uid,
                            moderator_uid,
                            provider=FailingModerationAIProvider(),
                        )
                    self.assertEqual(context.exception.status_code, 503)
                    self.assertEqual(
                        context.exception.detail["error_type"],
                        "moderation_ai_provider_unavailable",
                    )

                async with Database.sessionmaker()() as verify_db:
                    report = await verify_db.get(TrustSafetyReport, report_uid)
                    self.assertEqual(report.status, "in_review")
                    self.assertEqual(report.assigned_to_account_uid, moderator_uid)

                    recommendations = (
                        await verify_db.execute(
                            select(ModerationAIRecommendation).where(
                                ModerationAIRecommendation.report_uid == report_uid
                            )
                        )
                    ).scalars().all()
                    self.assertEqual(recommendations, [])

                    audit_types = list(
                        (
                            await verify_db.execute(
                                select(TrustSafetyAuditEvent.event_type).where(
                                    TrustSafetyAuditEvent.report_uid == report_uid
                                )
                            )
                        ).scalars().all()
                    )
                    self.assertIn("ai_assessment_failed", audit_types)
                    self.assertNotIn("restriction_issued", audit_types)
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    await cleanup_db.execute(
                        delete(ModerationAIRecommendation).where(
                            ModerationAIRecommendation.report_uid == report_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(TrustSafetyAuditEvent).where(
                            TrustSafetyAuditEvent.report_uid == report_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(TrustSafetyReport).where(TrustSafetyReport.uid == report_uid)
                    )
                    await cleanup_db.execute(delete(Persona).where(Persona.uid == persona_uid))
                    await cleanup_db.execute(
                        delete(Account).where(Account.uid.in_([target_uid, moderator_uid]))
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
