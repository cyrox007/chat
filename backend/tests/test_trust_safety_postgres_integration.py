import asyncio
import os
import unittest
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select

from components.identity.model import Account, Persona
from components.model_registry import ensure_models_registered
from components.moderation.model import TrustSafetyAuditEvent, TrustSafetyReport
from components.user.model import User
from components.moderation.trust_safety import (
    claim_trust_safety_report,
    list_my_trust_safety_reports,
    trust_safety_evidence,
)
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class TrustSafetyPostgresIntegrationTests(unittest.TestCase):
    def test_claim_is_exclusive_and_evidence_view_is_audited(self):
        async def run_case():
            ensure_models_registered()
            reporter_uid = uuid4()
            legacy_reporter_uid = uuid4()
            target_uid = uuid4()
            moderator_uids = [uuid4(), uuid4()]
            persona_uid = uuid4()
            primary_persona_uid = uuid4()
            report_uid = uuid4()

            async with Database.sessionmaker()() as setup_db:
                setup_db.add(
                    User(
                        uid=legacy_reporter_uid,
                        username=f"ts-reporter-{legacy_reporter_uid.hex[:10]}",
                        email=f"ts-reporter-{legacy_reporter_uid.hex[:10]}@example.test",
                        phone=f"+1999{legacy_reporter_uid.int % 10000000:07d}",
                        hashed_password="integration-test-not-a-real-password-hash",
                        is_active=True,
                    )
                )
                await setup_db.flush()
                for account_uid in [reporter_uid, target_uid, *moderator_uids]:
                    setup_db.add(
                        Account(
                            uid=account_uid,
                            legacy_user_uid=(
                                legacy_reporter_uid if account_uid == reporter_uid else None
                            ),
                            status="active",
                            trust_level="new",
                        )
                    )
                setup_db.add_all(
                    [
                        Persona(
                            uid=persona_uid,
                            account_uid=target_uid,
                            handle=f"ts-source-{str(persona_uid)[:8]}",
                            display_name="Reported Persona",
                            social_intent="open",
                            is_primary=False,
                        ),
                        Persona(
                            uid=primary_persona_uid,
                            account_uid=target_uid,
                            handle=f"ts-primary-{str(primary_persona_uid)[:8]}",
                            display_name="Private Primary Persona",
                            social_intent="open",
                            is_primary=True,
                        ),
                    ]
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
                        description="integration",
                        status="triage",
                    )
                )
                await setup_db.commit()

            async def try_claim(moderator_uid):
                async with Database.sessionmaker()() as db:
                    try:
                        item = await claim_trust_safety_report(db, report_uid, moderator_uid)
                        return ("claimed", moderator_uid, item)
                    except HTTPException as exc:
                        return ("rejected", moderator_uid, exc.detail)

            try:
                async with Database.sessionmaker()() as reporter_db:
                    reports, total = await list_my_trust_safety_reports(
                        reporter_db,
                        reporter_uid,
                    )
                    self.assertEqual(total, 1)
                    self.assertEqual(len(reports), 1)
                    reporter_view = reports[0]
                    self.assertNotIn("target", reporter_view)
                    self.assertNotIn("priority", reporter_view)
                    self.assertNotIn("assigned_to_account_uid", reporter_view)
                    self.assertNotIn("resolution_code", reporter_view)
                    self.assertEqual(reporter_view["source_uid"], str(persona_uid))
                    serialized = str(reporter_view)
                    self.assertNotIn(str(target_uid), serialized)
                    self.assertNotIn(str(primary_persona_uid), serialized)
                    self.assertNotIn("Private Primary Persona", serialized)

                results = await asyncio.gather(*(try_claim(uid) for uid in moderator_uids))
                claimed = [item for item in results if item[0] == "claimed"]
                rejected = [item for item in results if item[0] == "rejected"]
                self.assertEqual(len(claimed), 1, results)
                self.assertEqual(len(rejected), 1, results)
                self.assertEqual(
                    rejected[0][2].get("error_type"),
                    "trust_safety_report_already_claimed",
                )

                owner_uid = claimed[0][1]
                async with Database.sessionmaker()() as evidence_db:
                    evidence = await trust_safety_evidence(evidence_db, report_uid, owner_uid)
                    self.assertTrue(evidence["available"])
                    self.assertEqual(evidence["source_type"], "persona")
                    self.assertEqual(evidence["persona"]["uid"], str(persona_uid))

                async with Database.sessionmaker()() as verify_db:
                    report = await verify_db.get(TrustSafetyReport, report_uid)
                    self.assertEqual(report.status, "in_review")
                    self.assertEqual(report.assigned_to_account_uid, owner_uid)
                    events = list(
                        (
                            await verify_db.execute(
                                select(TrustSafetyAuditEvent)
                                .where(TrustSafetyAuditEvent.report_uid == report_uid)
                                .order_by(TrustSafetyAuditEvent.created_at.asc())
                            )
                        ).scalars().all()
                    )
                    self.assertEqual(
                        [event.event_type for event in events],
                        ["report_claimed", "evidence_viewed"],
                    )
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    await cleanup_db.execute(
                        delete(TrustSafetyAuditEvent).where(TrustSafetyAuditEvent.report_uid == report_uid)
                    )
                    await cleanup_db.execute(
                        delete(TrustSafetyReport).where(TrustSafetyReport.uid == report_uid)
                    )
                    await cleanup_db.execute(
                        delete(Persona).where(
                            Persona.uid.in_([persona_uid, primary_persona_uid])
                        )
                    )
                    await cleanup_db.execute(
                        delete(Account).where(
                            Account.uid.in_([reporter_uid, target_uid, *moderator_uids])
                        )
                    )
                    await cleanup_db.execute(
                        delete(User).where(User.uid == legacy_reporter_uid)
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
