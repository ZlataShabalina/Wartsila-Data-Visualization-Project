# switches to activae db connection
import os
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DEFAULT_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db")

_current_db_url = DEFAULT_URL  # mutable; changed when selecting a DB connection

def set_current_db_url(url: str | None):
    global _current_db_url
    _current_db_url = url or DEFAULT_URL
    get_engine.cache_clear()  # reset cached engine

@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    return create_async_engine(_current_db_url, future=True, echo=os.getenv("SQL_ECHO", "0") == "1")

def get_sessionmaker():
    return sessionmaker(bind=get_engine(), class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False)

async def get_session():
    async with get_sessionmaker()() as session:
        yield session
