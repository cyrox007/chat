import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from utils.database_metrics import database_pool_health, database_pool_snapshot


class _FakePool:
    def __init__(self, *, checked_out: int, checked_in: int, overflow: int = 0):
        self._checked_out = checked_out
        self._checked_in = checked_in
        self._overflow = overflow

    def checkedout(self):
        return self._checked_out

    def checkedin(self):
        return self._checked_in

    def overflow(self):
        return self._overflow


def _engine(pool):
    return SimpleNamespace(sync_engine=SimpleNamespace(pool=pool))


class DatabasePoolMetricsContractTests(unittest.TestCase):
    def test_snapshot_reports_only_aggregate_capacity(self):
        pool = _FakePool(checked_out=7, checked_in=13, overflow=0)
        with (
            patch("utils.database_metrics.Database.get_engine", return_value=_engine(pool)),
            patch.multiple(
                "utils.database_metrics.config",
                DB_POOL_SIZE=20,
                DB_POOL_MAX_OVERFLOW=10,
                DB_POOL_ALERT_UTILIZATION_PERCENT=85,
                DB_POOL_MIN_HEADROOM_CONNECTIONS=3,
            ),
        ):
            payload = database_pool_snapshot()

        self.assertEqual(payload["max_connections"], 30)
        self.assertEqual(payload["checked_out_connections"], 7)
        self.assertEqual(payload["headroom_connections"], 23)
        self.assertEqual(payload["utilization_percent"], 23.33)
        self.assertFalse(payload["near_capacity"])

    def test_health_marks_low_headroom_without_exposing_connection_details(self):
        pool = _FakePool(checked_out=28, checked_in=2, overflow=8)
        with (
            patch("utils.database_metrics.Database.get_engine", return_value=_engine(pool)),
            patch.multiple(
                "utils.database_metrics.config",
                DB_POOL_SIZE=20,
                DB_POOL_MAX_OVERFLOW=10,
                DB_POOL_ALERT_UTILIZATION_PERCENT=95,
                DB_POOL_MIN_HEADROOM_CONNECTIONS=3,
            ),
        ):
            payload = database_pool_health()

        self.assertFalse(payload["healthy"])
        self.assertIn("postgres.pool_near_capacity", payload["attention_reasons"])
        self.assertEqual(payload["pool"]["headroom_connections"], 2)

        serialized = json.dumps(payload).lower()
        for forbidden in (
            "postgresql://",
            "db_password",
            "select ",
            "account_uid",
            "query_parameters",
        ):
            if forbidden == "query_parameters":
                # The privacy declaration may name the category, but no values exist.
                self.assertFalse(payload["privacy"]["contains_query_parameters"])
            else:
                self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
