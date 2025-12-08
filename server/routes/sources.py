# server/routes/sources.py
from __future__ import annotations
from registry.session import set_user_source, get_user_source
from typing import Optional, Iterable, List
from fastapi import APIRouter, Depends, Body, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from registry.session import get_registry_session
from registry.api import list_connections, register_connection, get_connection
from registry.models import DbConnection
from db.engine_pool import get_engine
from storage.sql_repository import SqlGraphRepository
from utils.csv_import import DATA_DIR, read_server_csv

router = APIRouter()

@router.get("/sources")
async def get_sources(reg: AsyncSession = Depends(get_registry_session)):
    """
    Return all available CSVs, DB connections, and datasets grouped by connection.
    """
    # List CSV files
    csvs = []
    for p in sorted(DATA_DIR.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True):
        st = p.stat()
        csvs.append({"name": p.name, "size": st.st_size, "modified_at": int(st.st_mtime)})

    # List database connections
    conns = await list_connections(reg)

    # For each connection, get its datasets
    all_datasets = []
    for conn in conns:
        engine = get_engine(conn["url"])
        Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as sess:
            try:
                repo = SqlGraphRepository(sess)
                datasets = await repo.list_datasets()
                all_datasets.append({
                    "connection_id": conn["id"],
                    "connection_name": conn["name"],
                    "datasets": datasets,
                })
            except Exception as e:
                all_datasets.append({
                    "connection_id": conn["id"],
                    "connection_name": conn["name"],
                    "datasets": [],
                    "error": str(e)
                })

    return {
        "csv_files": csvs,
        "db_connections": conns,
        "datasets_by_connection": all_datasets,
    }


@router.post("/db/register")
async def register_db(
    name: str = Body(...),
    url: str = Body(..., example="sqlite+aiosqlite:///./data/app.db"),
    api_key: Optional[str] = Body(None),
    reg: AsyncSession = Depends(get_registry_session),
):
    cid = await register_connection(reg, name=name, url=url, api_key=api_key)
    return {"message": "db connection registered", "connection_id": cid}

@router.post("/sources/import_csv")
async def import_csv_to_db(
    payload: dict = Body(..., example={"connection_id": 1, "filename": "where_used.csv", "eng_ids": ["MODMAT000001","MODMAT000002"]}),
    api_key: Optional[str] = Header(default=None, alias="x-api-key"),
    reg: AsyncSession = Depends(get_registry_session),
):
    """
    Import a CSV from server data/ into a connection-scoped dataset.
    Optional scoping by one or more eng_id roots using 'eng_id' or 'eng_ids'.
    """
    conn_id = payload.get("connection_id")
    filename = payload.get("filename")
    one_eng  = payload.get("eng_id")
    many_eng = payload.get("eng_ids")

    if not conn_id or not filename:
        raise HTTPException(status_code=400, detail="connection_id and filename required")

    # Normalize eng_ids param
    filter_ids: Optional[List[str]] = None
    if one_eng and many_eng:
        raise HTTPException(status_code=400, detail="Provide either 'eng_id' or 'eng_ids', not both")
    if one_eng:
        filter_ids = [str(one_eng).strip()]
    elif isinstance(many_eng, list):
        filter_ids = [str(x).strip() for x in many_eng if str(x).strip()]

    # Fetch connection & check API key
    dbrow = await get_connection(reg, conn_id)
    if not dbrow:
        raise HTTPException(status_code=404, detail="connection not found")
    if dbrow.api_key and api_key != dbrow.api_key:
        raise HTTPException(status_code=401, detail="invalid API key")

    # Read & normalize rows (with optional eng_id filter)
    dataset_sha, rows, path, meta = read_server_csv(filename, filter_eng_ids=filter_ids)

    # Open a session and insert (dedupe by sha)
    engine = get_engine(dbrow.url)
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as sess:
        repo = SqlGraphRepository(sess)
        existing = await repo.get_dataset_id_by_sha(dataset_sha)
        if existing:
            return {
                "message": "dataset already exists",
                "dataset_id": existing,
                "sha256": dataset_sha,
                "rows": len(rows),
                "filtered": meta.get("filtered", False),
                "eng_ids": meta.get("eng_ids"),
            }
        ds_id = await repo.insert_dataset(
            original_name=filename,
            saved_path=str(path),
            sha256=dataset_sha,
            rows=rows
        )
        return {
            "message": "dataset imported",
            "dataset_id": ds_id,
            "sha256": dataset_sha,
            "rows": len(rows),
            "filtered": meta.get("filtered", False),
            "eng_ids": meta.get("eng_ids"),
        }


@router.post("/sources/select")
async def select_source(
    payload: dict = Body(..., example={"user_id": "u123", "connection_id": 1, "dataset_id": 2}),
    reg: AsyncSession = Depends(get_registry_session),
):
    """
    Store user's active source selection (connection + dataset).
    This enables multiple users to work independently with different data sources.
    """
    user_id = str(payload.get("user_id"))
    connection_id = payload.get("connection_id")
    dataset_id = payload.get("dataset_id")

    if not user_id or not connection_id or not dataset_id:
        raise HTTPException(status_code=400, detail="user_id, connection_id and dataset_id required")

    # Validate that both exist
    conn = await get_connection(reg, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")

    engine = get_engine(conn.url)
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as sess:
        repo = SqlGraphRepository(sess)
        datasets = await repo.list_datasets()
        if not any(ds["dataset_id"] == dataset_id for ds in datasets):
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found in connection {connection_id}")

    set_user_source(user_id, connection_id, dataset_id)
    return {"message": "source selected", "user_id": user_id, "connection_id": connection_id, "dataset_id": dataset_id}


@router.get("/sources/active")
async def get_active_source(user_id: str, reg: AsyncSession = Depends(get_registry_session)):
    """Return the currently active source (connection + dataset) for the given user."""
    src = get_user_source(user_id)
    if not src:
        raise HTTPException(status_code=404, detail=f"No active source for user {user_id}")
    return src

@router.post("/sources/current")
async def set_current_source(payload: dict = Body(...)):
    """
    Optional helper for the frontend to store the user's current source
    (connection_id + dataset_id). No DB write, just a frontend state helper.
    """
    return {
        "message": "source set",
        "connection_id": payload.get("connection_id"),
        "dataset_id": payload.get("dataset_id")
    }
