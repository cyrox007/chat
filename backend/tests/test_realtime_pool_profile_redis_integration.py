import asyncio
import json
import os
import unittest

import redis.asyncio as redis

from components.realtime.pool_metrics import run_realtime_pool_profile
from components.realtime.service import RealtimeService
from settings import config


@unittest.skipUnless(
    os.getenv("PUBCHAT_REDIS_POOL_PROFILE_INTEGRATION") == "1",
    "Redis pool profile integration environment is not enabled",
)
class RealtimePoolProfileRedisIntegrationTests(unittest.TestCase):
    def test_bounded_profile_runs_near_small_pool_without_saturation(self):
        async def run_case():
            original = {
                "DEBUG": config.DEBUG,
                "REDIS_MAX_CONNECTIONS": config.REDIS_MAX_CONNECTIONS,
                "REDIS_POOL_ALERT_UTILIZATION_PERCENT": config.REDIS_POOL_ALERT_UTILIZATION_PERCENT,
                "REDIS_POOL_MIN_HEADROOM_CONNECTIONS": config.REDIS_POOL_MIN_HEADROOM_CONNECTIONS,
            }
            service = RealtimeService()
            admin = redis.from_url(config.REDIS_URL, decode_responses=True)

            try:
                config.DEBUG = False
                config.REDIS_MAX_CONNECTIONS = 12
                config.REDIS_POOL_ALERT_UTILIZATION_PERCENT = 90
                config.REDIS_POOL_MIN_HEADROOM_CONNECTIONS = 1
                await admin.flushdb()

                await service.start()
                self.assertTrue(service.distributed)

                report = await run_realtime_pool_profile(
                    service,
                    operations=100,
                    concurrency=10,
                    sample_interval_seconds=0.001,
                )

                self.assertEqual(report["operations"], 100)
                self.assertEqual(report["completed"], 100)
                self.assertEqual(report["failed"], 0)
                self.assertEqual(report["error_rate_percent"], 0.0)
                self.assertEqual(report["pool"]["max_connections"], 12)
                self.assertGreaterEqual(report["pool"]["peak_in_use_connections"], 1)
                self.assertLessEqual(report["pool"]["peak_created_connections"], 12)
                self.assertEqual(report["pool"]["saturation_samples"], 0)
                self.assertEqual(report["error_types"], {})

                serialized = json.dumps(report, sort_keys=True)
                self.assertNotIn(config.REDIS_URL, serialized)
                self.assertFalse(report["privacy"]["contains_redis_url"])
                self.assertFalse(report["privacy"]["contains_credentials"])
                self.assertFalse(report["privacy"]["contains_ticket_values"])
                self.assertFalse(report["privacy"]["contains_account_ids"])
            finally:
                await service.stop()
                try:
                    await admin.flushdb()
                finally:
                    await admin.aclose()
                for name, value in original.items():
                    setattr(config, name, value)

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
