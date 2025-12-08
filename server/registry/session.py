# server/registry/session.py
import os
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

REGISTRY_URL = os.getenv("REGISTRY_DATABASE_URL", "sqlite+aiosqlite:///./data/registry.db")

registry_engine: AsyncEngine = create_async_engine(
    REGISTRY_URL, future=True, echo=os.getenv("SQL_ECHO", "0") == "1"
)
RegistrySessionLocal = sessionmaker(
    bind=registry_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

async def get_registry_session():
    async with RegistrySessionLocal() as session:
        yield session

# ---------------------------------------------------------------------
# NEW: simple in-memory per-user source store
# ---------------------------------------------------------------------
_active_sources: Dict[str, Dict[str, Any]] = {}

def set_user_source(user_id: str, connection_id: int, dataset_id: int):
    """Remember which connection+dataset a user selected."""
    _active_sources[user_id] = {
        "connection_id": connection_id,
        "dataset_id": dataset_id,
    }

def get_user_source(user_id: str) -> Optional[Dict[str, Any]]:
    """Return the active source for a given user, if any."""
    return _active_sources.get(user_id)
