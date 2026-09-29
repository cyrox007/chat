import unittest
from unittest.mock import patch

from app import app
from components.realtime.pool_metrics import realtime_pool_health, redis_pool_snapshot
from settings import config


class _FakePool:
    max_connections = 20
    _in_use_connections = {1, 2, 3, 4}
    _available_connections = [5, 6]


class _FakeRedis:
    connection_pool = _FakePool()


class _FakeService:
    redis = _FakeRedis()
    redis_mode = "sentinel"


class RealtimePoolMetricsContractTests(unittest.TestCase):
    def test_admin_pool_health_route_is_registered(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/admin/operations/realtime-redis", paths)

    def test_pool_snapshot_is_aggregate_and_privacy_safe(self):
        with patch.multiple(
            config,
            REDIS_POOL_ALERT_UTILIZATION_PERCENT=85,
            REDIS_POOL_MIN_HEADROOM_CONNECTIONS=5,
        ):
            snapshot = redis_pool_snapshot(_FakeService())

        self.assertTrue(snapshot["connected"])
        self.assertEqual(snapshot["mode"], "sentinel")
        self.assertEqual(snapshot["max_connections"], 20)
        self.assertEqual(snapshot["in_use_connections"], 4)
        self.assertEqual(snapshot["available_connections"], 2)
        self.assertEqual(snapshot["created_connections"], 6)
        self.assertEqual(snapshot["headroom_connections"], 16)
        self.assertEqual(snapshot["utilization_percent"], 20.0)
        self.assertFalse(snapshot["near_capacity"])

    def test_health_flags_near_capacity_without_exposing_connection_details(self):
        class SaturatedPool:
            max_connections = 10
            _in_use_connections = set(range(9))
            _available_connections = []

        class SaturatedRedis:
            connection_pool = SaturatedPool()

        class SaturatedService:
            redis = SaturatedRedis()
            redis_mode = "direct"

        with patch.multiple(
            config,
            REDIS_POOL_ALERT_UTILIZATION_PERCENT=85,
            REDIS_POOL_MIN_HEADROOM_CONNECTIONS=2,
        ):
            report = realtime_pool_health(SaturatedService())

        self.assertFalse(report["healthy"])
        self.assertIn("redis.pool_near_capacity", report["attention_reasons"])
        self.assertEqual(report["pool"]["utilization_percent"], 90.0)
        self.assertFalse(report["privacy"]["contains_redis_url"])
        self.assertFalse(report["privacy"]["contains_credentials"])
        self.assertFalse(report["privacy"]["contains_ticket_values"])
        self.assertFalse(report["privacy"]["contains_account_ids"])


if __name__ == "__main__":
    unittest.main()
