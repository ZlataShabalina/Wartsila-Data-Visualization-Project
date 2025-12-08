# server/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
from db.models import Base as GraphBase
from registry.models import Base as RegistryBase
from db.engine_pool import get_engine
from registry.session import registry_engine

from routes.root_node import router as root_router
from routes.child_node import router as child_router
from routes.sources import router as sources_router
from routes.upload_csv import router as upload_router


import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    # 1) ensure registry tables
    async with registry_engine.begin() as conn:
        await conn.run_sync(RegistryBase.metadata.create_all)

    # 2) ensure default graph DB tables (so a local SQLite conn works out-of-the-box)
    default_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db")
    default_engine: AsyncEngine = get_engine(default_url)
    async with default_engine.begin() as conn:
        await conn.run_sync(GraphBase.metadata.create_all)

    # 3) optional warmup
    async with default_engine.connect() as c:
        await c.execute(text("SELECT 1"))

    yield  # --- application runs here ---

    # --- shutdown ---
    # If you want, dispose cached engines here. get_engine() is lru-cached; you can no-op, or:
    # from sqlalchemy.ext.asyncio import AsyncEngine
    # for url in list_of_urls_you_used:
    #     await get_engine(url).dispose()

app = FastAPI(lifespan=lifespan)

# CORS for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

# Routers
app.include_router(sources_router, prefix="/api")
app.include_router(root_router,    prefix="/api")
app.include_router(child_router,   prefix="/api")
app.include_router(upload_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
