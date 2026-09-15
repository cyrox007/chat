from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy import text
from typing import AsyncGenerator

from utils.logger import setup_logger
from settings import config

logger = setup_logger(__name__)


class Database:
    _engine = None
    _async_session_maker = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            cls._engine = create_async_engine(
                config.database_url(async_mode=True),
                pool_size=20,
                max_overflow=10,
                pool_timeout=30,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False,
            )
            logger.info("Database engine initialized")
        return cls._engine

    @classmethod
    def sessionmaker(cls):
        if cls._async_session_maker is None:
            cls._async_session_maker = async_sessionmaker(
                bind=cls.get_engine(),
                expire_on_commit=False,
                autoflush=False,
                class_=AsyncSession,
            )
        return cls._async_session_maker

    @classmethod
    async def get_session(cls) -> AsyncSession:
        """Return a connected async session for legacy decorators and services."""
        session = cls.sessionmaker()()
        try:
            await session.execute(text("SELECT 1"))
            return session
        except (InterfaceError, OperationalError) as exc:
            await session.close()
            logger.error("Database connection error: %s", exc)
            raise

    @classmethod
    async def session_generator(cls) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI dependency for code that uses Depends."""
        session = await cls.get_session()
        try:
            yield session
        finally:
            await session.close()

    @classmethod
    async def health_check(cls) -> bool:
        session = None
        try:
            session = await cls.get_session()
            await session.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.error("Health check failed: %s", exc)
            return False
        finally:
            if session is not None:
                await session.close()

    @classmethod
    async def dispose(cls):
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
            cls._async_session_maker = None

    Base = declarative_base()
