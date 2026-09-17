import asyncio
import os
import unittest
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select

from components.identity.model import (
    Account,
    AccountRole,
    PlatformPermission,
    PlatformRole,
    RolePermission,
)
from components.model_registry import ensure_models_registered
from components.moderation.model import (
    PlatformRestriction,
    PlatformRestrictionAppeal,
    PlatformRestrictionAuditEvent,
)
from components.moderation.policy import issue_platform_restriction, revoke_platform_restriction
from components.moderation.restriction_appeals import (
    claim_platform_restriction_appeal,
    create_platform_restriction_appeal,
)
from components.moderation.schemas import (
    PlatformRestrictionAppealCreateRequest,
    PlatformRestrictionCreateRequest,
    PlatformRestrictionRevokeRequest,
)
from components.notification.model import UserNotification
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class ModerationPermissionPostgresIntegrationTests(unittest.TestCase):
    def test_sensitive_actions_require_explicit_permission_and_authority(self):
        async def run_case():
            ensure_models_registered()
            target_uid = uuid4()
            moderator_one_uid = uuid4()
            moderator_two_uid = uuid4()
            admin_uid = uuid4()
            manage_only_uid = uuid4()
            custom_role_id = 900000
            restriction_uids = []

            async with Database.sessionmaker()() as setup_db:
                manage_permission_id = (
                    await setup_db.execute(
                        select(PlatformPermission.id).where(
                            PlatformPermission.name == "moderation.platform.manage"
                        )
                    )
                ).scalar_one()
                setup_db.add_all(
                    [
                        Account(uid=target_uid, status="active", trust_level="new"),
                        Account(uid=moderator_one_uid, status="active", trust_level="new"),
                        Account(uid=moderator_two_uid, status="active", trust_level="new"),
                        Account(uid=admin_uid, status="active", trust_level="new"),
                        Account(uid=manage_only_uid, status="active", trust_level="new"),
                        PlatformRole(
                            id=custom_role_id,
                            name=f"manage-only-{manage_only_uid.hex}",
                            description="Integration-test role with queue access only",
                            authority_level=60,
                        ),
                    ]
                )
                await setup_db.flush()
                setup_db.add_all(
                    [
                        AccountRole(account_uid=target_uid, role_id=1),
                        AccountRole(account_uid=moderator_one_uid, role_id=2),
                        AccountRole(account_uid=moderator_two_uid, role_id=2),
                        AccountRole(account_uid=admin_uid, role_id=3),
                        AccountRole(account_uid=manage_only_uid, role_id=custom_role_id),
                        RolePermission(
                            role_id=custom_role_id,
                            permission_id=manage_permission_id,
                        ),
                    ]
                )
                await setup_db.commit()

            try:
                temporary_payload = PlatformRestrictionCreateRequest(
                    target_account_uid=target_uid,
                    capability="messenger.send",
                    reason_code="integration_test",
                    public_explanation="Временное ограничение для проверки полномочий.",
                    duration_minutes=60,
                )

                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await issue_platform_restriction(db, manage_only_uid, temporary_payload)
                    self.assertEqual(
                        context.exception.detail.get("error_type"),
                        "restriction_issue_permission_required",
                    )
                    await db.rollback()

                async with Database.sessionmaker()() as db:
                    moderator_restriction = await issue_platform_restriction(
                        db, moderator_one_uid, temporary_payload
                    )
                    moderator_restriction_uid = moderator_restriction["uid"]
                    restriction_uids.append(moderator_restriction_uid)

                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await revoke_platform_restriction(
                            db,
                            manage_only_uid,
                            moderator_restriction_uid,
                            PlatformRestrictionRevokeRequest(reason="Недостаточно permission."),
                        )
                    self.assertEqual(
                        context.exception.detail.get("error_type"),
                        "restriction_revoke_permission_required",
                    )
                    await db.rollback()

                async with Database.sessionmaker()() as db:
                    revoked = await revoke_platform_restriction(
                        db,
                        moderator_two_uid,
                        moderator_restriction_uid,
                        PlatformRestrictionRevokeRequest(
                            reason="Peer moderator исправил временную санкцию."
                        ),
                    )
                    self.assertEqual(revoked["status"], "revoked")

                async with Database.sessionmaker()() as db:
                    admin_restriction = await issue_platform_restriction(
                        db, admin_uid, temporary_payload
                    )
                    admin_restriction_uid = admin_restriction["uid"]
                    restriction_uids.append(admin_restriction_uid)

                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await revoke_platform_restriction(
                            db,
                            moderator_two_uid,
                            admin_restriction_uid,
                            PlatformRestrictionRevokeRequest(
                                reason="Модератор не должен отменять решение admin."
                            ),
                        )
                    self.assertEqual(
                        context.exception.detail.get("error_type"),
                        "restriction_revoke_authority_insufficient",
                    )
                    await db.rollback()

                async with Database.sessionmaker()() as db:
                    revoked = await revoke_platform_restriction(
                        db,
                        admin_uid,
                        admin_restriction_uid,
                        PlatformRestrictionRevokeRequest(
                            reason="Admin пересмотрел собственное решение."
                        ),
                    )
                    self.assertEqual(revoked["status"], "revoked")

                permanent_payload = PlatformRestrictionCreateRequest(
                    target_account_uid=target_uid,
                    capability="messenger.send",
                    reason_code="integration_test_permanent",
                    public_explanation="Бессрочная санкция требует повышенных полномочий.",
                    duration_minutes=None,
                )
                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await issue_platform_restriction(
                            db, moderator_one_uid, permanent_payload
                        )
                    self.assertEqual(
                        context.exception.detail.get("error_type"),
                        "permanent_restriction_permission_required",
                    )
                    await db.rollback()

                account_access_payload = PlatformRestrictionCreateRequest(
                    target_account_uid=target_uid,
                    capability="account.access",
                    reason_code="integration_test_access",
                    public_explanation="Полный доступ ограничивается только elevated ролью.",
                    duration_minutes=60,
                )
                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await issue_platform_restriction(
                            db, moderator_one_uid, account_access_payload
                        )
                    self.assertEqual(
                        context.exception.detail.get("error_type"),
                        "account_access_permission_required",
                    )
                    await db.rollback()

                async with Database.sessionmaker()() as db:
                    appeal_source = await issue_platform_restriction(
                        db, moderator_one_uid, temporary_payload
                    )
                    appeal_source_uid = appeal_source["uid"]
                    restriction_uids.append(appeal_source_uid)

                async with Database.sessionmaker()() as db:
                    appeal = await create_platform_restriction_appeal(
                        db,
                        target_uid,
                        appeal_source_uid,
                        PlatformRestrictionAppealCreateRequest(
                            body="Прошу независимо пересмотреть временное ограничение."
                        ),
                    )
                    appeal_uid = appeal["uid"]

                async with Database.sessionmaker()() as db:
                    with self.assertRaises(HTTPException) as context:
                        await claim_platform_restriction_appeal(
                            db, appeal_uid, manage_only_uid
                        )
                    self.assertEqual(
                        context.exception.detail.get("error_type"),
                        "appeal_review_permission_required",
                    )
                    await db.rollback()

                async with Database.sessionmaker()() as db:
                    claimed = await claim_platform_restriction_appeal(
                        db, appeal_uid, moderator_two_uid
                    )
                    self.assertEqual(
                        claimed["reviewer_account_uid"], str(moderator_two_uid)
                    )
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    restriction_ids = list(
                        (
                            await cleanup_db.execute(
                                select(PlatformRestriction.uid).where(
                                    PlatformRestriction.target_account_uid == target_uid
                                )
                            )
                        ).scalars().all()
                    )
                    if restriction_ids:
                        await cleanup_db.execute(
                            delete(PlatformRestrictionAppeal).where(
                                PlatformRestrictionAppeal.restriction_uid.in_(restriction_ids)
                            )
                        )
                        await cleanup_db.execute(
                            delete(PlatformRestrictionAuditEvent).where(
                                PlatformRestrictionAuditEvent.restriction_uid.in_(restriction_ids)
                            )
                        )
                    await cleanup_db.execute(
                        delete(UserNotification).where(
                            UserNotification.account_uid.in_(
                                [
                                    target_uid,
                                    moderator_one_uid,
                                    moderator_two_uid,
                                    admin_uid,
                                    manage_only_uid,
                                ]
                            )
                        )
                    )
                    await cleanup_db.execute(
                        delete(PlatformRestriction).where(
                            PlatformRestriction.target_account_uid == target_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(AccountRole).where(
                            AccountRole.account_uid.in_(
                                [
                                    target_uid,
                                    moderator_one_uid,
                                    moderator_two_uid,
                                    admin_uid,
                                    manage_only_uid,
                                ]
                            )
                        )
                    )
                    await cleanup_db.execute(
                        delete(RolePermission).where(
                            RolePermission.role_id == custom_role_id
                        )
                    )
                    await cleanup_db.execute(
                        delete(PlatformRole).where(PlatformRole.id == custom_role_id)
                    )
                    await cleanup_db.execute(
                        delete(Account).where(
                            Account.uid.in_(
                                [
                                    target_uid,
                                    moderator_one_uid,
                                    moderator_two_uid,
                                    admin_uid,
                                    manage_only_uid,
                                ]
                            )
                        )
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
