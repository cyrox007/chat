import unittest

from components.realtime.redis_client import (
    create_redis_client,
    parse_sentinel_nodes,
    redis_topology_mode,
)
from settings import config


class RedisTopologyTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            "REDIS_URL": config.REDIS_URL,
            "REDIS_SENTINEL_NODES": config.REDIS_SENTINEL_NODES,
            "REDIS_SENTINEL_MASTER": config.REDIS_SENTINEL_MASTER,
            "REDIS_SENTINEL_MIN_OTHER_SENTINELS": config.REDIS_SENTINEL_MIN_OTHER_SENTINELS,
        }

    def tearDown(self):
        for name, value in self.original.items():
            setattr(config, name, value)

    def test_parse_sentinel_nodes_supports_ipv4_hostname_and_ipv6(self):
        self.assertEqual(
            parse_sentinel_nodes("127.0.0.1:26379, sentinel-b:26380, [::1]:26381"),
            [
                ("127.0.0.1", 26379),
                ("sentinel-b", 26380),
                ("::1", 26381),
            ],
        )

    def test_parse_sentinel_nodes_rejects_invalid_values(self):
        for value in ("", "localhost", "localhost:not-a-port", "localhost:0", "[::1]"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_sentinel_nodes(value)

    def test_direct_mode_remains_backward_compatible(self):
        config.REDIS_URL = "redis://127.0.0.1:6379/0"
        config.REDIS_SENTINEL_NODES = ""
        config.REDIS_SENTINEL_MASTER = ""

        self.assertEqual(redis_topology_mode(), "direct")
        handle = create_redis_client()
        self.assertEqual(handle.mode, "direct")
        self.assertIsNone(handle.sentinel)

    def test_sentinel_mode_takes_precedence_over_direct_url(self):
        config.REDIS_URL = "redis://127.0.0.1:6379/0"
        config.REDIS_SENTINEL_NODES = "127.0.0.1:26379,127.0.0.1:26380"
        config.REDIS_SENTINEL_MASTER = "pubchat-master"
        config.REDIS_SENTINEL_MIN_OTHER_SENTINELS = 1

        self.assertEqual(redis_topology_mode(), "sentinel")
        handle = create_redis_client()
        self.assertEqual(handle.mode, "sentinel")
        self.assertIsNotNone(handle.sentinel)

    def test_partial_sentinel_configuration_is_rejected(self):
        config.REDIS_URL = "redis://127.0.0.1:6379/0"
        config.REDIS_SENTINEL_NODES = "127.0.0.1:26379"
        config.REDIS_SENTINEL_MASTER = ""

        with self.assertRaises(ValueError):
            redis_topology_mode()
        with self.assertRaises(RuntimeError):
            config.ensure_realtime_settings()


if __name__ == "__main__":
    unittest.main()
