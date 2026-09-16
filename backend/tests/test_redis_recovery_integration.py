import asyncio
import os
import subprocess
import time
import unittest
from uuid import UUID

import redis.asyncio as redis

from components.realtime.service import RealtimeService, RealtimeUnavailable
from settings import config


@unittest.skipUnless(
    os.getenv("PUBCHAT_REDIS_RECOVERY_INTEGRATION") == "1",
    "Redis recovery integration environment is not enabled",
)
class RedisRecoveryIntegrationTests(unittest.TestCase):
    def test_service_recovers_after_redis_container_restart(self):
        container_id = os.environ.get("PUBCHAT_REDIS_CONTAINER_ID", "").strip()
        self.assertTrue(container_id, "PUBCHAT_REDIS_CONTAINER_ID is required")

        async def wait_for_redis(timeout: float = 15.0) -> None:
            deadline = time.monotonic() + timeout
            client = redis.from_url(config.REDIS_URL, decode_responses=True)
            try:
                while time.monotonic() < deadline:
                    try:
                        if await client.ping():
                            return
                    except Exception:
                        pass
                    await asyncio.sleep(0.25)
            finally:
                await client.aclose()
            raise AssertionError("Redis did not become ready after restart")

        async def run_case():
            original_debug = config.DEBUG
            service_a = RealtimeService()
            service_b = RealtimeService()
            account_uid = UUID("00000000-0000-0000-0000-000000000301")
            stopped = False

            try:
                config.DEBUG = False
                await service_a.start()
                await service_b.start()
                self.assertTrue(service_a.distributed)
                self.assertTrue(service_b.distributed)

                baseline_ticket, _ = await service_a.issue_ticket(account_uid, "messenger")
                self.assertIsNotNone(await service_b.consume_ticket(baseline_ticket, "messenger"))

                subprocess.run(
                    ["docker", "stop", "--time", "1", container_id],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                stopped = True

                # Production semantics: outage must be visible. The service must
                # never silently dispatch locally when Redis is unavailable.
                with self.assertRaises(RealtimeUnavailable):
                    await service_a.publish({"kind": "recovery-outage-probe"})

                subprocess.run(
                    ["docker", "start", container_id],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                stopped = False
                await wait_for_redis()

                # Same service objects must recover through redis-py connection
                # pools; no Python process/service reconstruction is allowed.
                recovered_ticket, _ = await service_a.issue_ticket(account_uid, "messenger")
                self.assertIsNotNone(await service_b.consume_ticket(recovered_ticket, "messenger"))

                received = asyncio.Event()
                payloads = []

                async def on_event(event):
                    if event.get("kind") == "recovery-after-restart":
                        payloads.append(event)
                        received.set()

                service_b.register_callback(on_event)

                # Listener reconnection is asynchronous after server restart. A
                # small retry window validates automatic resubscription without
                # restarting the RealtimeService object.
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline and not received.is_set():
                    try:
                        await service_a.publish(
                            {"kind": "recovery-after-restart", "payload": {"ok": True}}
                        )
                    except RealtimeUnavailable:
                        pass
                    try:
                        await asyncio.wait_for(received.wait(), timeout=0.75)
                    except asyncio.TimeoutError:
                        await asyncio.sleep(0.25)

                self.assertTrue(received.is_set(), "Pub/Sub listener did not recover after Redis restart")
                self.assertEqual(payloads[-1]["payload"], {"ok": True})
                self.assertEqual(payloads[-1]["protocol"], 2)
            finally:
                if stopped:
                    subprocess.run(
                        ["docker", "start", container_id],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    await wait_for_redis()
                config.DEBUG = original_debug
                await service_a.stop()
                await service_b.stop()

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
