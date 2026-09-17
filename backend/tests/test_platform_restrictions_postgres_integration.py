import asyncio
import os
import unittest
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select

from components.identity.model import Account, AccountRole
from components.model_registry import ensure_models_registered
from components.moderation.model import PlatformRestriction, PlatformRestrictionAuditEvent
from components.moderation.policy import (
    active_restriction_for_subject,
    issue_platform_restriction,
    revoke_platform_restriction,
)
from components.moderation.schemas import (
    PlatformRestrictionCreateRequest,
    PlatformRestrictionRevokeRequest,
)
from components.notification.model import UserNotification
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class PlatformRestrictionPostgresIntegrationTests(unittest.TestCase):
    def test_authority_duration_and_revoke_contract(self):
        async def run_case():
            ensure_models_registered()
            user_uid = uuid4()
            moderator_uid = uuid4()
            peer_moderator_uid = uuid4()
            admin_uid = uuid4()
            account_uids = [user_uid, moderator_uid, peer_moderator_uid, admin_uid]
            created_restriction_uids = []

            async with Database.sessionmaker()() as setup_db:
                for account_uid in account_uids:
                    setup_db.add(Account(uid=account_uid, status="active", trust_level="new"))
                await setup_db.flush()
                setup_db.add_all(
                    [
                        AccountRole(account_uid=user_uid, role_id=1),
                        AccountRole(account_uid=moderator_uid, role_id=2),
                        AccountRole(account_uid=peer_moderator_uid, role_id=2),
                        AccountRole(account_uid=admin_uid, role_id=3),
                    ]
                )
                await setup_db.commit()

            try:
                temporary_payload = PlatformRestrictionCreateRequest(
                    target_account_uid=user_uid,
                    capability="messenger.send",
                    reason_code="dm_abuse",
                    public_explanation="Личные сообщения временно ограничены.",
                    duration_minutes=60,
                )
                async with Database.sessionmaker()() as db:
                    item = await issue_platform_restriction(db, moderator_uid, temporary_payload)
                    created_restriction_uids.append(item["uid"])
                    self.assertEqual(item["capability"], "messenger.send")
                    self.assertEqual(item["status"], "active")
                    self.assertIsNotNone(item["expires_at"])

                async with Database.sessionmaker()() as db:
                    active = await active_restriction_for_subject(db, user_uid, "messenger.send")
                    self.assertIsNotNone(active)
                    self.assertEqual(str(active.uid), created_restriction_uids[0])

                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await issue_platform_restriction(
                            db,
                            moderator_uid,
                            PlatformRestrictionCreateRequest(
                                target_account_uid=peer_moderator_uid,
                                capability="space.chat.send",
                                reason_code="peer_test",
                                public_explanation="Недопустимая санкция равному уровню.",
                                duration_minutes=30,
                            ),
                        )
                    self.assertEqual(
                        context.exception.detail.get("error_type"),
                        "moderation_authority_insufficient",
                    )

                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await issue_platform_restriction(
                            db,
                            moderator_uid,
                            PlatformRestrictionCreateRequest(
                                target_account_uid=user_uid,
                                capability="space.chat.send",
                                reason_code="permanent_test",
                                public_explanation="Модератор не должен выдавать бессрочную санкцию.",
                            ),
                        )
                    self.assertEqual(
                        context.exception.detail.get("error_type"),
                        "permanent_restriction_permission_required",
                    )

                async with Database.sessionmaker()() as db:
                    permanent = await issue_platform_restriction(
                        db,
                        admin_uid,
                        PlatformRestrictionCreateRequest(
                            target_account_uid=moderator_uid,
                            capability="space.chat.send",
                            reason_code="admin_review",
                            public_explanation="Бессрочное ограничение до ручного пересмотра.",
                        ),
                    )
                    created_restriction_uids.append(permanent["uid"])
                    self.assertIsNone(permanent["expires_at"])

                async with Database.sessionmaker()() as db:
                    revoked = await revoke_platform_restriction(
                        db,
                        admin_uid,
                        UUID(created_restriction_uids[1]),
                        PlatformRestrictionRevokeRequest(reason="Проверка завершена, ограничение снято."),
                    )
                    self.assertEqual(revoked["status"], "revoked")

                async with Database.sessionmaker()() as verify_db:
                    rows = list(
                        (
                            await verify_db.execute(
                                select(PlatformRestriction).where(
                                    PlatformRestriction.target_account_uid.in_([user_uid, moderator_uid])
                                )
                            )
                        ).scalars().all()
                    )
                    self.assertEqual(len(rows), 2)
                    levels = {(row.actor_authority_level, row.target_authority_level) for row in rows}
                    self.assertIn((50, 0), levels)
                    self.assertIn((100, 50), levels)
                    audit_count = len(
                        list(
                            (
                                await verify_db.execute(
                                    select(PlatformRestrictionAuditEvent).where(
                                        PlatformRestrictionAuditEvent.restriction_uid.in_(
                                            [row.uid for row in rows]
                                        )
                                    )
                                )
                            ).scalars().all()
                        )
                    )
                    self.assertEqual(audit_count, 3)
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    restriction_ids = list(
                        (
                            await cleanup_db.execute(
                                select(PlatformRestriction.uid).where(
                                    PlatformRestriction.target_account_uid.in_(account_uids)
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
                        delete(UserNotification).where(UserNotification.account_uid.in_(account_uids))
                    )
                    await cleanup_db.execute(
                        delete(PlatformRestriction).where(
                            PlatformRestriction.target_account_uid.in_(account_uids)
                        )
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
