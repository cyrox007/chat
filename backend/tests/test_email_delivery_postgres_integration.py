import asyncio
import os
import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select

from components.identity.model import Account
from components.model_registry import ensure_models_registered
from components.notification.model import ExternalDeliveryLedger
from components.notification.unread_dm_email import claim_pending_email_deliveries
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class EmailDeliveryPostgresIntegrationTests(unittest.TestCase):
    def test_skip_locked_claims_are_disjoint_and_expired_lease_is_recoverable(self):
        async def run_case():
            ensure_models_registered()
            account_uids = [uuid4(), uuid4()]
            delivery_uids = [uuid4(), uuid4()]
            now = datetime.utcnow()

            async with Database.sessionmaker() as setup_db:
                for account_uid in account_uids:
                    setup_db.add(Account(uid=account_uid, status="active", trust_level="new"))
                await setup_db.flush()
                for delivery_uid, account_uid in zip(delivery_uids, account_uids, strict=True):
                    setup_db.add(
                        ExternalDeliveryLedger(
                            uid=delivery_uid,
                            account_uid=account_uid,
                            channel="email",
                            aggregate_key=f"integration:{delivery_uid}",
                            dedupe_key=f"integration:{delivery_uid}",
                            status="pending",
                            unread_count=1,
                            dialog_count=1,
                            next_attempt_at=now,
                        )
                    )
                await setup_db.commit()

            async def claim_one():
                async with Database.sessionmaker() as db:
                    claims = await claim_pending_email_deliveries(db, now=now, limit=1)
                    self.assertEqual(len(claims), 1)
                    return claims[0]

            try:
                first, second = await asyncio.gather(claim_one(), claim_one())
                self.assertNotEqual(first.uid, second.uid)
                self.assertEqual({first.uid, second.uid}, set(delivery_uids))
                self.assertNotEqual(first.claim_token, second.claim_token)

                async with Database.sessionmaker() as verify_db:
                    rows = list(
                        (
                            await verify_db.execute(
                                select(ExternalDeliveryLedger).where(
                                    ExternalDeliveryLedger.uid.in_(delivery_uids)
                                )
                            )
                        ).scalars().all()
                    )
                    self.assertEqual({row.status for row in rows}, {"processing"})
                    old_token = rows[0].claim_token
                    old_attempts = rows[0].attempt_count
                    rows[0].claim_expires_at = now - timedelta(seconds=1)
                    expired_uid = rows[0].uid
                    await verify_db.commit()

                async with Database.sessionmaker() as recovery_db:
                    recovered = await claim_pending_email_deliveries(
                        recovery_db,
                        now=now,
                        limit=1,
                    )
                    self.assertEqual(len(recovered), 1)
                    self.assertEqual(recovered[0].uid, expired_uid)
                    self.assertNotEqual(recovered[0].claim_token, old_token)
                    self.assertEqual(recovered[0].attempt_count, old_attempts + 1)
            finally:
                async with Database.sessionmaker() as cleanup_db:
                    await cleanup_db.execute(
                        delete(ExternalDeliveryLedger).where(
                            ExternalDeliveryLedger.uid.in_(delivery_uids)
                        )
                    )
                    await cleanup_db.execute(
                        delete(Account).where(Account.uid.in_(account_uids))
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
