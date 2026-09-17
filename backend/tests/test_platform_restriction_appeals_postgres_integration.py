import asyncio
import os
import unittest
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select

from components.identity.model import Account, AccountRole
from components.model_registry import ensure_models_registered
from components.moderation.model import (
    PlatformRestriction,
    PlatformRestrictionAppeal,
    PlatformRestrictionAuditEvent,
)
from components.moderation.policy import issue_platform_restriction
from components.moderation.restriction_appeals import (
    claim_platform_restriction_appeal,
    create_platform_restriction_appeal,
    resolve_platform_restriction_appeal,
)
from components.moderation.schemas import (
    PlatformRestrictionAppealCreateRequest,
    PlatformRestrictionAppealResolveRequest,
    PlatformRestrictionCreateRequest,
)
from components.notification.model import UserNotification
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class PlatformRestrictionAppealPostgresIntegrationTests(unittest.TestCase):
    def test_independent_reviewer_overturns_restriction(self):
        async def run_case():
            ensure_models_registered()
            user_uid = uuid4()
            issuer_uid = uuid4()
            reviewer_uid = uuid4()
            account_uids = [user_uid, issuer_uid, reviewer_uid]
            restriction_uid = None
            appeal_uid = None

            async with Database.sessionmaker()() as setup_db:
                setup_db.add_all(
                    [
                        Account(uid=user_uid, status="active", trust_level="new"),
                        Account(uid=issuer_uid, status="active", trust_level="new"),
                        Account(uid=reviewer_uid, status="active", trust_level="new"),
                    ]
                )
                await setup_db.flush()
                setup_db.add_all(
                    [
                        AccountRole(account_uid=user_uid, role_id=1),
                        AccountRole(account_uid=issuer_uid, role_id=2),
                        AccountRole(account_uid=reviewer_uid, role_id=2),
                    ]
                )
                await setup_db.commit()

            try:
                async with Database.sessionmaker()() as db:
                    restriction = await issue_platform_restriction(
                        db,
                        issuer_uid,
                        PlatformRestrictionCreateRequest(
                            target_account_uid=user_uid,
                            capability="messenger.send",
                            reason_code="dm_abuse",
                            public_explanation="Личные сообщения временно ограничены.",
                            duration_minutes=60,
                        ),
                    )
                    restriction_uid = UUID(restriction["uid"])

                async with Database.sessionmaker()() as db:
                    appeal = await create_platform_restriction_appeal(
                        db,
                        user_uid,
                        restriction_uid,
                        PlatformRestrictionAppealCreateRequest(
                            body="Прошу пересмотреть ограничение: контекст сообщения был неверно понят."
                        ),
                    )
                    appeal_uid = UUID(appeal["uid"])
                    self.assertEqual(appeal["status"], "pending")

                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await claim_platform_restriction_appeal(db, appeal_uid, issuer_uid)
                    self.assertEqual(
                        context.exception.detail.get("error_type"),
                        "independent_appeal_reviewer_required",
                    )

                async with Database.sessionmaker()() as db:
                    claimed = await claim_platform_restriction_appeal(
                        db,
                        appeal_uid,
                        reviewer_uid,
                    )
                    self.assertEqual(claimed["reviewer_account_uid"], str(reviewer_uid))

                async with Database.sessionmaker()() as db:
                    resolved = await resolve_platform_restriction_appeal(
                        db,
                        appeal_uid,
                        reviewer_uid,
                        PlatformRestrictionAppealResolveRequest(
                            decision="overturn",
                            resolution="Апелляция подтверждена; ограничение отменено после независимой проверки.",
                        ),
                    )
                    self.assertEqual(resolved["status"], "overturned")
                    self.assertEqual(resolved["restriction"]["status"], "revoked")

                async with Database.sessionmaker()() as verify_db:
                    restriction_row = await verify_db.get(PlatformRestriction, restriction_uid)
                    appeal_row = await verify_db.get(PlatformRestrictionAppeal, appeal_uid)
                    self.assertEqual(restriction_row.status, "revoked")
                    self.assertEqual(appeal_row.status, "overturned")
                    self.assertEqual(appeal_row.reviewer_account_uid, reviewer_uid)
                    events = list(
                        (
                            await verify_db.execute(
                                select(PlatformRestrictionAuditEvent.event_type).where(
                                    PlatformRestrictionAuditEvent.restriction_uid == restriction_uid
                                )
                            )
                        ).scalars().all()
                    )
                    self.assertIn("appeal_created", events)
                    self.assertIn("appeal_claimed", events)
                    self.assertIn("restriction_revoked_on_appeal", events)
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    if appeal_uid:
                        await cleanup_db.execute(
                            delete(PlatformRestrictionAppeal).where(
                                PlatformRestrictionAppeal.uid == appeal_uid
                            )
                        )
                    if restriction_uid:
                        await cleanup_db.execute(
                            delete(PlatformRestrictionAuditEvent).where(
                                PlatformRestrictionAuditEvent.restriction_uid == restriction_uid
                            )
                        )
                        await cleanup_db.execute(
                            delete(PlatformRestriction).where(
                                PlatformRestriction.uid == restriction_uid
                            )
                        )
                    await cleanup_db.execute(
                        delete(UserNotification).where(UserNotification.account_uid.in_(account_uids))
                    )
                    await cleanup_db.execute(
                        delete(AccountRole).where(AccountRole.account_uid.in_(account_uids))
                    )
                    await cleanup_db.execute(delete(Account).where(Account.uid.in_(account_uids)))
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
