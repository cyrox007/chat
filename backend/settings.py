import os
from dotenv import load_dotenv
""" from pydantic_settings import BaseSettings """


load_dotenv()

class Config:
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    # Frontend
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").split(',')

    # Server
    SERVER_HTTP_PROTOCOL = os.getenv("SERVER_HTTP_PROTOCOL", "http://")
    SERVER_ADDR = os.getenv("SERVER_ADDR", "localhost")
    SERVER_PORT = os.getenv("SERVER_PORT", "9000")
    BASE_URL = f"{SERVER_HTTP_PROTOCOL}{SERVER_ADDR}:{SERVER_PORT}"

    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "chat")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

    # JWT
    JWT_ACCESS_SECRET_KEY = "your_access_secret_key"
    JWT_REFRESH_SECRET_KEY = "your_refresh_secret_key"
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 30

    # Paths
    STATICS_DIRNAME = os.getenv("STATICS_DIRNAME", "static")

    def database_url(self, async_mode=False):
        driver = "postgresql+asyncpg" if async_mode else "postgresql"
        return f"{driver}://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
config = Config()

""" class CsrfSettings(BaseSettings):
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key')
    CSRF_TOKEN_EXPIRE_MINUTES: int = 60
    CSRF_COOKIE_NAME: str = 'XSRF-TOKEN'
    CSRF_HEADER_NAME: str = 'X-CSRF-Token'
    COOKIE_SECURE: bool = False  # True в production

csrf = CsrfSettings() """