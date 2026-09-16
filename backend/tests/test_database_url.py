import unittest

from sqlalchemy.engine import make_url

from settings import Config


class DatabaseUrlTests(unittest.TestCase):
    def test_database_url_round_trips_special_credentials(self):
        cfg = Config()
        cfg.DB_USER = "pub@chat user"
        cfg.DB_PASSWORD = "p@ss:/?#[] value"
        cfg.DB_HOST = "db.example.test"
        cfg.DB_PORT = "5432"
        cfg.DB_NAME = "chat-db"

        parsed = make_url(cfg.database_url())
        self.assertEqual(parsed.drivername, "postgresql")
        self.assertEqual(parsed.username, cfg.DB_USER)
        self.assertEqual(parsed.password, cfg.DB_PASSWORD)
        self.assertEqual(parsed.host, cfg.DB_HOST)
        self.assertEqual(parsed.port, 5432)
        self.assertEqual(parsed.database, cfg.DB_NAME)

    def test_async_database_url_uses_asyncpg(self):
        cfg = Config()
        cfg.DB_USER = "pubchat"
        cfg.DB_PASSWORD = "secret"
        cfg.DB_HOST = "localhost"
        cfg.DB_PORT = "5432"
        cfg.DB_NAME = "chat"

        parsed = make_url(cfg.database_url(async_mode=True))
        self.assertEqual(parsed.drivername, "postgresql+asyncpg")
        self.assertEqual(parsed.password, "secret")


if __name__ == "__main__":
    unittest.main()
