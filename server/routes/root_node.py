# server/routes/root_node.py
from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from registry.session import get_registry_session
from registry.api import get_connection
from db.engine_pool import get_engine
from storage.sql_repository import SqlGraphRepository

router = APIRouter()

@router.get("/root_node")
async def get_root_node(
    connection_id: int = Query(..., description="DB connection id"),
    dataset_id: int = Query(..., description="Dataset id within that DB"),
    api_key: str | None = Header(default=None, alias="x-api-key"),
    reg: AsyncSession = Depends(get_registry_session),
):
    dbrow = await get_connection(reg, connection_id)
    if not dbrow:
        raise HTTPException(status_code=404, detail="connection not found")
    if dbrow.api_key and api_key != dbrow.api_key:
        raise HTTPException(status_code=401, detail="invalid API key")

    engine = get_engine(dbrow.url)
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as sess:
        repo = SqlGraphRepository(sess)
        roots = await repo.list_roots(dataset_id)
        children_count = {}
        if not roots:
            return {"message": "no roots found", "root_nodes": [], "count": 0}
        for root in roots:
            children = await repo.get_children(dataset_id, parent_id=root)
            children_count[root] = len(children)
        return {"message": "roots", "root_nodes": roots, "count": len(roots), "children_count": children_count}
