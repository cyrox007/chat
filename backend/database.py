from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from settings import config

class Database:
    def connect_database() -> Session:
        engine = create_engine(config.database_url())
        db_session = Session(bind=engine)
        return db_session
    
    async def get_async_session() -> AsyncSession:
        async with sessionmaker(autocommit=False, autoflush=False, bind=create_async_engine(config.database_url())) as session:
            async with session.begin():
                return session
    
    Base = declarative_base()