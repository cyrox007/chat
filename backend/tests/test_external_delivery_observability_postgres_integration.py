import asyncio
import json
import os
import unittest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete

from components.identity.model import Account
from components.model_registry import ensure_models_registered
from components.notification.model import ExternalDeliveryLedger
from components.notification.operations_metrics import external_delivery_metrics
from database import Database


@unittest.skipUnless(
    os.getenv("PUBCHAT_POSTGRES_INTEGRATION") == "1",
    "PostgreSQL integration environment is not enabled",
)
class ExternalDeliveryObservabilityPostgresIntegrationTests(unittest.TestCase):
    def test_metrics_detect_stale_backlog_and_expired_claim_without_identifiers(self):
        async def run_case():
            ensure_models_registered()
            account_uid = uuid4()
            now = datetime.utcnow()

            async with Database.sessionmaker()() as setup_db:
                setup_db.add(
                    Account(
                        uid=account_uid,
                        status="active",
                        trust_level="new",
                    )
                )
                await setup_db.flush()
                setup_db.add_all(
                    [
                        ExternalDeliveryLedger(
                            account_uid=account_uid,
                            channel="email",
                            aggregate_key="private-aggregate-a",
                            dedupe_key=f"obs-email-{uuid4()}",
                            status="pending",
                            unread_count=2,
                            dialog_count=1,
                            attempt_count=0,
                            next_attempt_at=now - timedelta(hours=2),
                            created_at=now - timedelta(hours=2),
                            updated_at=now - timedelta(hours=2),
                        ),
                        ExternalDeliveryLedger(
                            account_uid=account_uid,
                            channel="web_push",
                            aggregate_key="private-aggregate-b",
                            dedupe_key=f"obs-push-processing-{uuid4()}",
                            status="processing",
                            unread_count=1,
                            dialog_count=1,
                            attempt_count=1,
                            attempted_at=now - timedelta(minutes=10),
                            claim_token="private-claim-token",
                            claim_expires_at=now - timedelta(minutes=5),
                            created_at=now - timedelta(minutes=15),
                            updated_at=now - timedelta(minutes=10),
                        ),
                        ExternalDeliveryLedger(
                            account_uid=account_uid,
                            channel="web_push",
                            aggregate_key="private-aggregate-c",
                            dedupe_key=f"obs-push-delivered-{uuid4()}",
                            status="delivered",
                            unread_count=1,
                            dialog_count=1,
                            attempt_count=2,
                            attempted_at=now - timedelta(minutes=3),
                            delivered_at=now - timedelta(minutes=2),
                            provider_message_id="provider-private-id",
                            created_at=now - timedelta(minutes=8),
                            updated_at=now - timedelta(minutes=2),
                        ),
                    ]
                )
                await setup_db.commit()

            try:
                async with Database.sessionmaker()() as db:
                    metrics = await external_delivery_metrics(
                        db,
                        window_hours=24,
                    )

                self.assertFalse(metrics["healthy"])
                self.assertIn(
                    "email.due_backlog_age_exceeded",
                    metrics["attention_reasons"],
                )
                self.assertIn(
                    "web_push.expired_processing_claims",
                    metrics["attention_reasons"],
                )
                self.assertEqual(
                    metrics["channels"]["email"]["due_count"],
                    1,
                )
                self.assertGreaterEqual(
                    metrics["channels"]["email"]["oldest_due_age_seconds"],
                    2 * 60 * 60 - 5,
                )
                self.assertEqual(
                    metrics["channels"]["web_push"]["expired_claim_count"],
                    1,
                )
                self.assertEqual(
                    metrics["channels"]["web_push"]["delivered_count"],
                    1,
                )
                self.assertEqual(
                    metrics["channels"]["web_push"]["retry_pressure_count"],
                    1,
                )

                serialized = json.dumps(metrics, sort_keys=True)
                self.assertNotIn(str(account_uid), serialized)
                self.assertNotIn("private-aggregate", serialized)
                self.assertNotIn("private-claim-token", serialized)
                self.assertNotIn("provider-private-id", serialized)
                self.assertTrue(
                    metrics["privacy"]["contains_account_ids"] is False
                )
                self.assertTrue(
                    metrics["privacy"]["contains_push_endpoints"] is False
                )
                self.assertTrue(
                    metrics["privacy"]["contains_message_content"] is False
                )
            finally:
                async with Database.sessionmaker()() as cleanup_db:
                    await cleanup_db.execute(
                        delete(ExternalDeliveryLedger).where(
                            ExternalDeliveryLedger.account_uid == account_uid
                        )
                    )
                    await cleanup_db.execute(
                        delete(Account).where(Account.uid == account_uid)
                    )
                    await cleanup_db.commit()
                await Database.dispose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
