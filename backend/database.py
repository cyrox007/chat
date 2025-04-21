from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from settings import config

class Database:
    _engine = None
    _async_session = None
    
    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            cls._engine = create_async_engine(
                config.database_url(async_mode=True),
                pool_size=20,
                max_overflow=10,
                pool_timeout=30
            )
        return cls._engine
    
    @classmethod
    async def get_session(cls) -> AsyncSession:
        if cls._async_session is None:
            cls._async_session = async_sessionmaker(
                bind=cls.get_engine(),
                expire_on_commit=False,
                class_=AsyncSession
            )
        return cls._async_session()
    
    Base = declarative_base()