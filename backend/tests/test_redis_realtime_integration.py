import asyncio
import os
import unittest
from uuid import UUID

import redis.asyncio as redis

from components.realtime.service import RealtimeService
from settings import config


@unittest.skipUnless(
    os.getenv("PUBCHAT_REDIS_INTEGRATION") == "1",
    "Redis integration environment is not enabled",
)
class RedisRealtimeIntegrationTests(unittest.TestCase):
    def test_distributed_realtime_primitives(self):
        async def run_case():
            original_debug = config.DEBUG
            original_ticket_ttl = config.REALTIME_TICKET_TTL_SECONDS
            service_a = RealtimeService()
            service_b = RealtimeService()
            admin = redis.from_url(config.REDIS_URL, decode_responses=True)

            account_uid = UUID("00000000-0000-0000-0000-000000000101")
            room_uid = UUID("00000000-0000-0000-0000-000000000201")

            try:
                config.DEBUG = False
                config.REALTIME_TICKET_TTL_SECONDS = 2
                await admin.flushdb()

                await service_a.start()
                await service_b.start()
                self.assertTrue(service_a.distributed)
                self.assertTrue(service_b.distributed)

                # Ticket storage is shared and consume-once across service instances.
                ticket, ttl = await service_a.issue_ticket(account_uid, "room", room_uid)
                self.assertEqual(ttl, 2)
                consumed = await service_b.consume_ticket(ticket, "room", room_uid)
                self.assertIsNotNone(consumed)
                self.assertEqual(consumed["account_uid"], str(account_uid))
                self.assertIsNone(await service_a.consume_ticket(ticket, "room", room_uid))

                # Presence written by one worker is immediately visible to another.
                await service_a.register_connection("conn-a", account_uid, "room", room_uid)
                self.assertTrue(await service_b.is_online(account_uid))
                self.assertEqual(await service_b.room_users(room_uid), [str(account_uid)])
                removed = await service_b.unregister_connection("conn-a")
                self.assertEqual(removed["user_uid"], str(account_uid))
                self.assertFalse(await service_a.is_online(account_uid))

                # Rate limiting is distributed; the third action is rejected even
                # when requests alternate between worker instances.
                self.assertTrue(await service_a.allow_action(account_uid, "integration", 2, 30))
                self.assertTrue(await service_b.allow_action(account_uid, "integration", 2, 30))
                self.assertFalse(await service_a.allow_action(account_uid, "integration", 2, 30))

                # Idempotency claims are also shared and can be released after a
                # failed persistence attempt.
                event_id = "integration-event-1"
                self.assertTrue(await service_a.claim_event(account_uid, "room-message", event_id, 30))
                self.assertFalse(await service_b.claim_event(account_uid, "room-message", event_id, 30))
                await service_b.release_event(account_uid, "room-message", event_id)
                self.assertTrue(await service_a.claim_event(account_uid, "room-message", event_id, 30))

                # Pub/sub must cross instance boundaries, not fall back to local
                # callback dispatch.
                received = asyncio.Event()
                payloads = []

                async def on_event(event):
                    if event.get("kind") == "integration":
                        payloads.append(event)
                        received.set()

                service_b.register_callback(on_event)
                await service_a.publish({"kind": "integration", "payload": {"ok": True}})
                await asyncio.wait_for(received.wait(), timeout=3)
                self.assertTrue(payloads)
                self.assertEqual(payloads[-1]["protocol"], 2)
                self.assertEqual(payloads[-1]["payload"], {"ok": True})

                # Ticket expiry is enforced by Redis TTL in production mode.
                expiring_ticket, _ = await service_a.issue_ticket(account_uid, "messenger")
                await asyncio.sleep(2.1)
                self.assertIsNone(await service_b.consume_ticket(expiring_ticket, "messenger"))
            finally:
                config.DEBUG = original_debug
                config.REALTIME_TICKET_TTL_SECONDS = original_ticket_ttl
                await service_a.stop()
                await service_b.stop()
                try:
                    await admin.flushdb()
                finally:
                    await admin.aclose()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
