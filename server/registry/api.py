# server/registry/api.py
from __future__ import annotations
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import DbConnection

async def list_connections(db: AsyncSession) -> list[dict]:
    res = await db.execute(select(DbConnection).order_by(DbConnection.created_at.desc()))
    out = []
    for row in res.scalars():
        out.append({
            "id": row.id, "name": row.name, "url": row.url,
            "created_at": str(row.created_at) if row.created_at else None,
            "last_used_at": str(row.last_used_at) if row.last_used_at else None,
            "has_api_key": bool(row.api_key)
        })
    return out

async def register_connection(db: AsyncSession, name: str, url: str, api_key: Optional[str]) -> int:
    conn = DbConnection(name=name, url=url, api_key=api_key or None, is_active=False)
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn.id

async def get_connection(db: AsyncSession, conn_id: int) -> Optional[DbConnection]:
    return await db.get(DbConnection, conn_id)
