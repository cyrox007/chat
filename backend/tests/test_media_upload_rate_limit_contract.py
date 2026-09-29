import asyncio
import unittest
from unittest.mock import patch
from uuid import uuid4

from components.realtime.service import RealtimeService
from settings import config


class WeightedMediaRateLimitContractTests(unittest.TestCase):
    def test_debug_fallback_counts_weighted_actual_bytes(self):
        async def run_case():
            service = RealtimeService()
            user_uid = uuid4()
            with patch.object(config, "DEBUG", True):
                self.assertTrue(
                    await service.allow_cost(
                        user_uid,
                        "media-upload-bytes",
                        40,
                        100,
                        60,
                    )
                )
                self.assertTrue(
                    await service.allow_cost(
                        user_uid,
                        "media-upload-bytes",
                        60,
                        100,
                        60,
                    )
                )
                self.assertFalse(
                    await service.allow_cost(
                        user_uid,
                        "media-upload-bytes",
                        1,
                        100,
                        60,
                    )
                )

        asyncio.run(run_case())

    def test_single_cost_above_limit_is_rejected_without_state(self):
        async def run_case():
            service = RealtimeService()
            user_uid = uuid4()
            self.assertFalse(
                await service.allow_cost(
                    user_uid,
                    "media-upload-bytes",
                    101,
                    100,
                    60,
                )
            )
            self.assertTrue(
                await service.allow_cost(
                    user_uid,
                    "media-upload-bytes",
                    100,
                    100,
                    60,
                )
            )

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
