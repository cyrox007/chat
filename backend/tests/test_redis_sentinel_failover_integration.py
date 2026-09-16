import asyncio
import os
import subprocess
import time
import unittest
from uuid import UUID

from redis.asyncio.sentinel import Sentinel

from components.realtime.service import RealtimeService, RealtimeUnavailable
from settings import config


@unittest.skipUnless(
    os.getenv("PUBCHAT_REDIS_SENTINEL_INTEGRATION") == "1",
    "Redis Sentinel failover integration environment is not enabled",
)
class RedisSentinelFailoverIntegrationTests(unittest.TestCase):
    def test_same_service_objects_recover_after_master_promotion(self):
        master_container = os.environ.get("PUBCHAT_SENTINEL_MASTER_CONTAINER", "").strip()
        sentinel_nodes = os.environ.get(
            "PUBCHAT_SENTINEL_NODES",
            "127.0.0.1:26379,127.0.0.1:26380,127.0.0.1:26381",
        ).strip()
        service_name = os.environ.get("PUBCHAT_SENTINEL_MASTER_NAME", "pubchat-master").strip()
        self.assertTrue(master_container, "PUBCHAT_SENTINEL_MASTER_CONTAINER is required")

        async def run_case():
            original = {
                "DEBUG": config.DEBUG,
                "REDIS_URL": config.REDIS_URL,
                "REDIS_SENTINEL_NODES": config.REDIS_SENTINEL_NODES,
                "REDIS_SENTINEL_MASTER": config.REDIS_SENTINEL_MASTER,
                "REDIS_SENTINEL_MIN_OTHER_SENTINELS": config.REDIS_SENTINEL_MIN_OTHER_SENTINELS,
            }
            service_a = RealtimeService()
            service_b = RealtimeService()
            sentinel = Sentinel(
                [(item.rsplit(":", 1)[0], int(item.rsplit(":", 1)[1])) for item in sentinel_nodes.split(",")],
                socket_timeout=1,
                socket_connect_timeout=1,
                decode_responses=True,
            )
            account_uid = UUID("00000000-0000-0000-0000-000000000401")
            master_stopped = False

            async def wait_for_master_port(expected_port: int, timeout: float = 20.0) -> None:
                deadline = time.monotonic() + timeout
                last = None
                while time.monotonic() < deadline:
                    try:
                        last = await sentinel.discover_master(service_name)
                        if int(last[1]) == expected_port:
                            return
                    except Exception as exc:
                        last = repr(exc)
                    await asyncio.sleep(0.25)
                self.fail(f"Sentinel did not promote expected master port {expected_port}; last={last}")

            async def issue_and_consume_after_failover(timeout: float = 15.0) -> None:
                deadline = time.monotonic() + timeout
                last_error = None
                while time.monotonic() < deadline:
                    try:
                        ticket, _ = await service_a.issue_ticket(account_uid, "messenger")
                        payload = await service_b.consume_ticket(ticket, "messenger")
                        if payload is not None:
                            return
                    except Exception as exc:
                        last_error = exc
                    await asyncio.sleep(0.25)
                self.fail(f"ticket path did not recover after Sentinel promotion: {last_error!r}")

            try:
                config.DEBUG = False
                config.REDIS_URL = ""
                config.REDIS_SENTINEL_NODES = sentinel_nodes
                config.REDIS_SENTINEL_MASTER = service_name
                config.REDIS_SENTINEL_MIN_OTHER_SENTINELS = 1

                await service_a.start()
                await service_b.start()
                self.assertTrue(service_a.distributed)
                self.assertTrue(service_b.distributed)
                self.assertEqual(service_a.redis_mode, "sentinel")
                self.assertEqual(service_b.redis_mode, "sentinel")

                initial_master = await sentinel.discover_master(service_name)
                self.assertEqual(int(initial_master[1]), 6380)

                baseline_ticket, _ = await service_a.issue_ticket(account_uid, "messenger")
                self.assertIsNotNone(await service_b.consume_ticket(baseline_ticket, "messenger"))

                received = asyncio.Event()
                received_payloads = []

                async def on_event(event):
                    if event.get("kind") == "sentinel-after-promotion":
                        received_payloads.append(event)
                        received.set()

                service_b.register_callback(on_event)

                subprocess.run(
                    ["docker", "stop", "--time", "1", master_container],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                master_stopped = True

                await wait_for_master_port(6381)
                await issue_and_consume_after_failover()

                # PubSub may have held a connection to the old master. The listener
                # must recreate that subscription through Sentinel and deliver an
                # event without reconstructing either RealtimeService object.
                deadline = time.monotonic() + 15
                last_publish_error = None
                while time.monotonic() < deadline and not received.is_set():
                    try:
                        await service_a.publish(
                            {
                                "kind": "sentinel-after-promotion",
                                "payload": {"master_port": 6381},
                            }
                        )
                    except RealtimeUnavailable as exc:
                        last_publish_error = exc
                    except Exception as exc:
                        last_publish_error = exc
                    try:
                        await asyncio.wait_for(received.wait(), timeout=0.75)
                    except asyncio.TimeoutError:
                        await asyncio.sleep(0.25)

                self.assertTrue(
                    received.is_set(),
                    f"PubSub did not recover after Sentinel promotion: {last_publish_error!r}",
                )
                self.assertEqual(received_payloads[-1]["payload"]["master_port"], 6381)
                self.assertEqual(received_payloads[-1]["protocol"], 2)
            finally:
                for name, value in original.items():
                    setattr(config, name, value)
                await service_a.stop()
                await service_b.stop()
                for sentinel_client in sentinel.sentinels:
                    try:
                        await sentinel_client.aclose()
                    except Exception:
                        pass

                # The shell harness owns topology cleanup. Do not restart the old
                # master here: a standalone restart before Sentinel reconfiguration
                # could briefly create a split-brain test artifact.
                self.assertTrue(master_stopped or os.getenv("CI") != "true")

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
