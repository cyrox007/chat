import asyncio
import os
import unittest
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from components.identity.model import Account, AccountRole, IdentitySession
from components.model_registry import ensure_models_registered
from components.moderation.account_access import (
    active_account_access_restriction,
    account_access_projection,
)
from components.moderation.model import PlatformRestriction, PlatformRestrictionAuditEvent
from components.moderation.policy import issue_platform_restriction, revoke_platform_restriction
from components.moderation.schemas import PlatformRestrictionCreateRequest, PlatformRestrictionRevokeRequest
from components.notification.model import UserNotification
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class AccountAccessPostgresIntegrationTests(unittest.TestCase):
    def test_account_access_revokes_sessions_and_restores_only_after_revoke(self):
        async def run_case():
            ensure_models_registered()
            user_uid = uuid4()
            admin_uid = uuid4()
            session_uid = uuid4()
            restriction_uid = None

            async with Database.sessionmaker()() as setup_db:
                setup_db.add_all(
                    [
                        Account(uid=user_uid, status="active", trust_level="new"),
                        Account(uid=admin_uid, status="active", trust_level="new"),
                    ]
                )
                await setup_db.flush()
                setup_db.add_all(
                    [
                        AccountRole(account_uid=user_uid, role_id=1),
                        AccountRole(account_uid=admin_uid, role_id=3),
                        IdentitySession(
                            uid=session_uid,
                            account_uid=user_uid,
                            refresh_token_hash=f"test-{uuid4().hex}",
                            expires_at=datetime.utcnow() + timedelta(days=7),
                        ),
                    ]
                )
                await setup_db.commit()

            try:
                # Normal API input is rejected at the schema boundary before it
                # can reach the service.
                with self.assertRaises(ValidationError):
                    PlatformRestrictionCreateRequest(
                        target_account_uid=user_uid,
                        capability="account.access",
                        scope_type="space",
                        scope_uid=uuid4(),
                        reason_code="scope_test",
                        public_explanation="Неверная область ограничения.",
                        duration_minutes=60,
                    )

                # Keep the service-level invariant too, so an internal caller
                # cannot bypass the Pydantic contract with a constructed model.
                invalid_payload = PlatformRestrictionCreateRequest.model_construct(
                    target_account_uid=user_uid,
                    capability="account.access",
                    scope_type="space",
                    scope_uid=uuid4(),
                    reason_code="scope_test",
                    public_explanation="Неверная область ограничения.",
                    duration_minutes=60,
                    report_uid=None,
                )
                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await issue_platform_restriction(db, admin_uid, invalid_payload)
                    self.assertEqual(
                        context.exception.detail.get("error_type"),
                        "account_access_must_be_platform_scoped",
                    )

                async with Database.sessionmaker()() as db:
                    item = await issue_platform_restriction(
                        db,
                        admin_uid,
                        PlatformRestrictionCreateRequest(
                            target_account_uid=user_uid,
                            capability="account.access",
                            reason_code="platform_suspension",
                            public_explanation="Доступ к платформе временно ограничен.",
                            duration_minutes=60,
                        ),
                    )
                    restriction_uid = UUID(item["uid"])
                    self.assertEqual(item["capability"], "account.access")
                    self.assertEqual(item["scope_type"], "platform")

                async with Database.sessionmaker()() as verify_db:
                    session = await verify_db.get(IdentitySession, session_uid)
                    self.assertIsNotNone(session.revoked_at)
                    active = await active_account_access_restriction(verify_db, user_uid)
                    self.assertIsNotNone(active)
                    projection = await account_access_projection(verify_db, user_uid)
                    self.assertEqual(projection["uid"], str(restriction_uid))

                async with Database.sessionmaker()() as db:
                    revoked = await revoke_platform_restriction(
                        db,
                        admin_uid,
                        restriction_uid,
                        PlatformRestrictionRevokeRequest(
                            reason="Апелляция рассмотрена, доступ восстановлен."
                        ),
                    )
                    self.assertEqual(revoked["status"], "revoked")

                async with Database.sessionmaker()() as verify_db:
                    self.assertIsNone(await active_account_access_restriction(verify_db, user_uid))
                    session = await verify_db.get(IdentitySession, session_uid)
                    self.assertIsNotNone(session.revoked_at)
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    restriction_ids = list(
                        (
                            await cleanup_db.execute(
                                select(PlatformRestriction.uid).where(
                                    PlatformRestriction.target_account_uid == user_uid
                                )
                            )
                        ).scalars().all()
                    )
                    if restriction_ids:
                        await cleanup_db.execute(
                            delete(PlatformRestrictionAuditEvent).where(
                                PlatformRestrictionAuditEvent.restriction_uid.in_(restriction_ids)
                            )
                        )
                    await cleanup_db.execute(
                        delete(UserNotification).where(
                            UserNotification.account_uid.in_([user_uid, admin_uid])
                        )
                    )
                    await cleanup_db.execute(
                        delete(IdentitySession).where(
                            IdentitySession.account_uid.in_([user_uid, admin_uid])
                        )
                    )
                    await cleanup_db.execute(
                        delete(PlatformRestriction).where(
                            PlatformRestriction.target_account_uid == user_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(AccountRole).where(
                            AccountRole.account_uid.in_([user_uid, admin_uid])
                        )
                    )
                    await cleanup_db.execute(
                        delete(Account).where(Account.uid.in_([user_uid, admin_uid]))
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
