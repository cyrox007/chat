import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()


class Config:
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Frontend
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")

    # Server
    SERVER_HTTP_PROTOCOL = os.getenv("SERVER_HTTP_PROTOCOL", "http://")
    SERVER_ADDR = os.getenv("SERVER_ADDR", "localhost")
    SERVER_PORT = os.getenv("SERVER_PORT", "9000")

    @property
    def BASE_URL(self):
        protocol = self.SERVER_HTTP_PROTOCOL
        address = self.SERVER_ADDR
        port = self.SERVER_PORT
        if port in ["80", "443"]:
            return f"{protocol}{address}"
        return f"{protocol}{address}:{port}"

    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "chat")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

    # Redis / realtime
    # Direct topology remains the default/backward-compatible mode. When both
    # Sentinel fields below are configured, Sentinel takes precedence and
    # REDIS_URL is ignored by the realtime client factory.
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0" if DEBUG else "")
    REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "100"))
    REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS = float(
        os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS", "5")
    )
    REDIS_SOCKET_TIMEOUT_SECONDS = float(os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS", "5"))
    REDIS_SENTINEL_NODES = os.getenv("REDIS_SENTINEL_NODES", "")
    REDIS_SENTINEL_MASTER = os.getenv("REDIS_SENTINEL_MASTER", "")
    REDIS_SENTINEL_MIN_OTHER_SENTINELS = max(
        0, int(os.getenv("REDIS_SENTINEL_MIN_OTHER_SENTINELS", "0"))
    )
    REDIS_SENTINEL_USERNAME = os.getenv("REDIS_SENTINEL_USERNAME", "")
    REDIS_SENTINEL_PASSWORD = os.getenv("REDIS_SENTINEL_PASSWORD", "")
    REDIS_USERNAME = os.getenv("REDIS_USERNAME", "")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB = max(0, int(os.getenv("REDIS_DB", "0")))

    REALTIME_TICKET_TTL_SECONDS = int(os.getenv("REALTIME_TICKET_TTL_SECONDS", "30"))
    REALTIME_AUTH_TIMEOUT_SECONDS = int(os.getenv("REALTIME_AUTH_TIMEOUT_SECONDS", "8"))
    REALTIME_PRESENCE_TTL_SECONDS = int(os.getenv("REALTIME_PRESENCE_TTL_SECONDS", "90"))
    REALTIME_HEARTBEAT_SECONDS = int(os.getenv("REALTIME_HEARTBEAT_SECONDS", "25"))
    REALTIME_SEND_TIMEOUT_SECONDS = float(os.getenv("REALTIME_SEND_TIMEOUT_SECONDS", "5"))
    REALTIME_OUTBOUND_QUEUE_SIZE = max(1, int(os.getenv("REALTIME_OUTBOUND_QUEUE_SIZE", "64")))
    REALTIME_MESSAGE_RATE_LIMIT = int(os.getenv("REALTIME_MESSAGE_RATE_LIMIT", "25"))
    REALTIME_MESSAGE_RATE_WINDOW_SECONDS = int(os.getenv("REALTIME_MESSAGE_RATE_WINDOW_SECONDS", "10"))
    REALTIME_IDEMPOTENCY_TTL_SECONDS = int(os.getenv("REALTIME_IDEMPOTENCY_TTL_SECONDS", "600"))

    # Message external delivery. External channels remain opt-in at the Account
    # preference layer. Safe minimums prevent accidental high-frequency nudges.
    MESSAGE_EMAIL_NUDGE_INACTIVITY_MINUTES = max(
        60, int(os.getenv("MESSAGE_EMAIL_NUDGE_INACTIVITY_MINUTES", "720"))
    )
    MESSAGE_EMAIL_NUDGE_COOLDOWN_MINUTES = max(
        60, int(os.getenv("MESSAGE_EMAIL_NUDGE_COOLDOWN_MINUTES", "1440"))
    )
    MESSAGE_EMAIL_DELIVERY_MAX_ATTEMPTS = max(
        1, int(os.getenv("MESSAGE_EMAIL_DELIVERY_MAX_ATTEMPTS", "5"))
    )
    MESSAGE_EMAIL_DELIVERY_RETRY_BASE_SECONDS = max(
        60, int(os.getenv("MESSAGE_EMAIL_DELIVERY_RETRY_BASE_SECONDS", "300"))
    )

    # Security. There are intentionally no production-capable default secrets.
    JWT_ACCESS_SECRET_KEY = os.getenv("JWT_ACCESS_SECRET_KEY", "")
    JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "")
    CSRF_SECRET_KEY = os.getenv("CSRF_SECRET_KEY", "")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    CSRF_TOKEN_EXPIRE_MINUTES = int(os.getenv("CSRF_TOKEN_EXPIRE_MINUTES", "30"))

    # Paths
    STATICS_DIRNAME = os.getenv("STATICS_DIRNAME", "static")

    def ensure_security_settings(self):
        secrets = {
            "JWT_ACCESS_SECRET_KEY": self.JWT_ACCESS_SECRET_KEY,
            "JWT_REFRESH_SECRET_KEY": self.JWT_REFRESH_SECRET_KEY,
            "CSRF_SECRET_KEY": self.CSRF_SECRET_KEY,
        }
        missing = [name for name, value in secrets.items() if len(value) < 32]
        if missing:
            raise RuntimeError(
                f"{', '.join(missing)} must be configured with at least 32 characters"
            )
        if len(set(secrets.values())) != len(secrets):
            raise RuntimeError("JWT access, refresh and CSRF secrets must be different")

    def redis_configured(self) -> bool:
        sentinel_nodes = self.REDIS_SENTINEL_NODES.strip()
        sentinel_master = self.REDIS_SENTINEL_MASTER.strip()
        return bool(self.REDIS_URL or (sentinel_nodes and sentinel_master))

    def ensure_realtime_settings(self) -> None:
        sentinel_nodes = self.REDIS_SENTINEL_NODES.strip()
        sentinel_master = self.REDIS_SENTINEL_MASTER.strip()
        if bool(sentinel_nodes) != bool(sentinel_master):
            raise RuntimeError(
                "REDIS_SENTINEL_NODES and REDIS_SENTINEL_MASTER must be configured together"
            )
        if not self.DEBUG and not self.redis_configured():
            raise RuntimeError(
                "Production realtime requires REDIS_URL or Redis Sentinel configuration"
            )

    def database_url(self, async_mode=False):
        driver = "postgresql+asyncpg" if async_mode else "postgresql"
        return URL.create(
            drivername=driver,
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=int(self.DB_PORT),
            database=self.DB_NAME,
        ).render_as_string(hide_password=False)

    def alembic_database_url(self):
        """Return a ConfigParser-safe SQLAlchemy URL for Alembic.

        Alembic stores sqlalchemy.url through Python ConfigParser. Percent-encoded
        credentials (for example a backslash rendered as %5C) must therefore
        escape literal percent signs as %% before set_main_option().
        ConfigParser resolves %% back to % when the value is read.
        """
        return self.database_url().replace("%", "%%")

    # File storage
    UPLOADS_BASE_URL = f"{SERVER_HTTP_PROTOCOL}{SERVER_ADDR}/uploads/"
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))
    MAX_FILES_LIMIT = int(os.getenv("MAX_FILES_LIMIT", "10"))


config = Config()
