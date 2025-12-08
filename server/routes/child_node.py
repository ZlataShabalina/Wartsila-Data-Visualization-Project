# server/routes/child_node.py
from __future__ import annotations
from fastapi import APIRouter, Depends, Query, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from registry.session import get_registry_session
from registry.api import get_connection
from db.engine_pool import get_engine
from storage.sql_repository import SqlGraphRepository

router = APIRouter()

@router.get("/child_node")
async def get_child_node(
    connection_id: int = Query(..., description="DB connection id"),
    dataset_id: int = Query(..., description="Dataset id within that DB"),
    node_id: str = Query(..., description="Parent node whose children to fetch"),
    limit: int | None = Query(None, ge=1, description="Max number of children to return"),
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
        parent = await repo.get_parent(dataset_id, node_id)
        children = await repo.get_children(dataset_id, node_id, limit=limit)
        if not parent and not children:
            return {"error": f"Node {node_id} not found", "children": [], "count_children": 0}
        return {"search_id": node_id, "parent": parent, "children": children, "count_children": len(children)}
    
@router.get("/sources/children/path/{child_id}")
async def get_child_path(
    child_id: str,
    connection_id: int,
    dataset_id: int,
    api_key: str | None = Header(default=None, alias="x-api-key"),
    reg: AsyncSession = Depends(get_registry_session),
):
    """
    Return the path from root to the specified child node.
    """
    dbrow = await get_connection(reg, connection_id)
    if not dbrow:
        raise HTTPException(status_code=404, detail="connection not found")

    if dbrow.api_key and api_key != dbrow.api_key:
        raise HTTPException(status_code=401, detail="invalid API key")

    engine = get_engine(dbrow.url)
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as sess:
        repo = SqlGraphRepository(sess)
        path = await repo.find_path_to_child(dataset_id, child_id)
        if not path:
            raise HTTPException(status_code=404, detail=f"Child node {child_id} not found.")
        return {"path": path, "length": len(path)}

