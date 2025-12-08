# server/routes/upload_csv.py
from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from registry.session import get_registry_session
from registry.api import get_connection
from utils.csv_import import (
    DATA_DIR,
    save_bytes_unique,
    parse_csv_text,
    sha256_bytes,
    sha256_text,
)
from db.engine_pool import get_engine
from storage.sql_repository import SqlGraphRepository

router = APIRouter()

@router.post("/upload_csv", summary="Upload CSV (optional: import to DB)")
async def upload_csv(
    # multipart form
    file: UploadFile = File(..., description="CSV file"),
    import_now: bool = Form(False, description="Import into DB right after upload"),
    connection_id: Optional[int] = Form(
        None, description="DB connection id (required if import_now=true)"
    ),
    # scope by root(s)
    eng_id: Optional[str] = Form(
        None, description="Single eng_id to scope dataset (new schema only)"
    ),
    eng_ids: Optional[List[str]] = Form(
        None, description="Multiple eng_ids (repeat the field or use Swagger's 'Add item')"
    ),
    # simple header-based auth (if the connection has an api_key)
    api_key: Optional[str] = Header(default=None, alias="x-api-key"),
    reg: AsyncSession = Depends(get_registry_session),
):
    """
    Upload a CSV via multipart/form-data. By default, it only saves the file
    under server/data/ and returns metadata.

    If `import_now=true`, it will parse/normalize the CSV and insert it into the
    specified DB connection as a dataset (optionally scoped by eng_id/eng_ids).
    """
    # ---- Read the uploaded content
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    # ---- Persist the file under /data (idempotent by name)
    saved_path = save_bytes_unique(file.filename, raw)
    file_sha = sha256_bytes(raw)

    # ---- When not importing now, just return info
    if not import_now:
        return {
            "message": "file uploaded",
            "original_name": file.filename,
            "saved_as": saved_path.name,
            "size": len(raw),
            "sha256": file_sha,
            "tip": "Use POST /api/sources/import_csv to import later, or set import_now=true here.",
        }

    # ---- Import now: need a connection_id
    if not connection_id:
        raise HTTPException(status_code=400, detail="connection_id is required when import_now=true")

    # Normalize eng_ids
    scope_ids: Optional[List[str]] = None
    if eng_id and eng_ids:
        raise HTTPException(status_code=400, detail="Provide either 'eng_id' or 'eng_ids', not both")
    if eng_id:
        scope_ids = [eng_id.strip()] if eng_id.strip() else None
    elif eng_ids:
        cleaned = [x.strip() for x in eng_ids if x and x.strip()]
        scope_ids = cleaned or None

    # ---- Fetch connection & verify simple auth
    dbrow = await get_connection(reg, connection_id)
    if not dbrow:
        raise HTTPException(status_code=404, detail="connection not found")
    if dbrow.api_key and api_key != dbrow.api_key:
        raise HTTPException(status_code=401, detail="invalid API key")

    # ---- Parse/normalize uploaded text directly (no need to re-read from disk)
    text = raw.decode("utf-8", errors="replace")
    rows, meta = parse_csv_text(text, filter_eng_ids=scope_ids)

    # Build a scope-aware dataset SHA: file_sha | eng_ids
    if meta.get("filtered") and meta.get("eng_ids"):
        scope_key = "eng_ids:" + ",".join(meta["eng_ids"])
        dataset_sha = sha256_text(file_sha + "|" + scope_key)
    else:
        dataset_sha = file_sha

    # ---- Insert (or reuse) dataset inside the chosen DB
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
                "saved_as": saved_path.name,
            }

        ds_id = await repo.insert_dataset(
            original_name=file.filename,
            saved_path=str(saved_path),
            sha256=dataset_sha,
            rows=rows,
        )

        return {
            "message": "dataset imported",
            "dataset_id": ds_id,
            "sha256": dataset_sha,
            "rows": len(rows),
            "filtered": meta.get("filtered", False),
            "eng_ids": meta.get("eng_ids"),
            "saved_as": saved_path.name,
        }
