# server/db/engine_pool.py
from functools import lru_cache
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

@lru_cache(maxsize=32)
def get_engine(db_url: str) -> AsyncEngine:
    return create_async_engine(db_url, future=True)
