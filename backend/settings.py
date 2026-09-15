import os
from dotenv import load_dotenv

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

    # JWT. There are intentionally no production-capable default secrets.
    JWT_ACCESS_SECRET_KEY = os.getenv("JWT_ACCESS_SECRET_KEY", "")
    JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", "")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # Paths
    STATICS_DIRNAME = os.getenv("STATICS_DIRNAME", "static")

    def ensure_security_settings(self):
        secrets = {
            "JWT_ACCESS_SECRET_KEY": self.JWT_ACCESS_SECRET_KEY,
            "JWT_REFRESH_SECRET_KEY": self.JWT_REFRESH_SECRET_KEY,
        }
        missing = [name for name, value in secrets.items() if len(value) < 32]
        if missing:
            raise RuntimeError(
                f"{', '.join(missing)} must be configured with at least 32 characters"
            )
        if self.JWT_ACCESS_SECRET_KEY == self.JWT_REFRESH_SECRET_KEY:
            raise RuntimeError("JWT access and refresh secrets must be different")

    def database_url(self, async_mode=False):
        driver = "postgresql+asyncpg" if async_mode else "postgresql"
        return (
            f"{driver}://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # File storage
    UPLOADS_BASE_URL = f"{SERVER_HTTP_PROTOCOL}{SERVER_ADDR}/uploads/"
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))
    MAX_FILES_LIMIT = int(os.getenv("MAX_FILES_LIMIT", "10"))


config = Config()
