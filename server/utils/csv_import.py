# server/utils/csv_import.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Tuple, Iterable, Optional
import pandas as pd, io, hashlib, re, numpy as np
from fastapi import HTTPException

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _normalize_cols(cols):
    return [str(c).strip().lower().replace("\ufeff", "") for c in cols]

def _sniff_delimiter(sample: str) -> str:
    commas = sample.count(",")
    semis  = sample.count(";")
    return "," if commas >= semis else ";"

def _parse_old_schema(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "parent_item": df["parent_item"].astype(str).str.strip(),
        "child_item":  df["child_item"].astype(str).str.strip(),
        "sequence_no": pd.to_numeric(df["sequence_no"], errors="coerce").fillna(0).astype(int),
        "level":       pd.to_numeric(df["level"], errors="coerce").fillna(0).astype(int),
    })
    out.sort_values(["parent_item","child_item","level","sequence_no"], inplace=True, kind="stable")
    out = out.drop_duplicates(subset=["parent_item","child_item","level"], keep="first").reset_index(drop=True)
    return out

def _parse_new_schema(df: pd.DataFrame) -> pd.DataFrame:
    relationships = {}  # (parent, child) -> (sequence, level)
    
    for idx, row in df.iterrows():
        engine_id = str(row.get("engine_id", "")).strip()
        system_id = str(row.get("system_id", "")).strip()
        path_str = str(row.get("path", "")).strip()
        parent_item_id = str(row.get("parent_item_id", "")).strip()
        child_item_id = str(row.get("child_item_id", "")).strip()
        bom_level = pd.to_numeric(row.get("bom_level"), errors="coerce")
        sequenceno = pd.to_numeric(row.get("sequenceno"), errors="coerce")
        
        if pd.isna(bom_level):
            bom_level = 0
        if pd.isna(sequenceno):
            sequenceno = 0
            
        bom_level = int(bom_level)
        sequenceno = int(sequenceno)
        
        # 1. Add ENGINE_ID -> SYSTEM_ID relationship (level 1)
        if engine_id and system_id:
            rel_key = (engine_id, system_id)
            if rel_key not in relationships:
                relationships[rel_key] = (0, 0)  # Level 1, sequence 0 (implicit)
        
        # 2. Add explicit parent-child relationship from row
        if parent_item_id and child_item_id:
            rel_key = (parent_item_id, child_item_id)
            # Keep the one with highest sequence number (most specific)
            if rel_key not in relationships or sequenceno > relationships[rel_key][0]:
                relationships[rel_key] = (sequenceno, bom_level+1)
        
        # 3. Extract intermediate relationships from path
        if path_str:
            # Normalize path: remove leading arrows
            path_str = re.sub(r"^-+>", "", path_str)
            parts = [p.strip() for p in path_str.split("->") if p.strip()]
            
            if len(parts) > 1:
                # Create relationships for each consecutive pair in the path
                for i in range(len(parts) - 1):
                    parent = parts[i]
                    child = parts[i + 1]
                    rel_key = (parent, child)
                    
                    # Calculate level: first part (SYSTEM_ID) is level 1
                    level = i+2
                    
                    # For intermediate nodes, use sequence 0 unless we already have data
                    if rel_key not in relationships:
                        relationships[rel_key] = (0, level)
    
    # Convert to DataFrame
    rows = []
    for (parent, child), (sequence, level) in relationships.items():
        rows.append({
            "parent_item": parent,
            "child_item": child,
            "sequence_no": sequence,
            "level": level,
        })
    
    if not rows:
        return pd.DataFrame(columns=["parent_item", "child_item", "sequence_no", "level"])
    
    out = pd.DataFrame(rows)
    # Sort but keep all instances (don't drop duplicates at different levels)
    out.sort_values(["parent_item", "child_item", "level", "sequence_no"], inplace=True, kind="stable")
    # Only drop exact duplicates (same parent, child, AND level)
    out = out.drop_duplicates(subset=["parent_item", "child_item", "level"], keep="last").reset_index(drop=True)
    return out

def parse_csv_text(
    text: str,
    filter_eng_ids: Optional[Iterable[str]] = None
) -> tuple[List[Dict], dict]:
    """
    Parse CSV text in either schema, optionally filtering the *new* schema by eng_id.
    Returns (rows, meta) where rows are canonical dicts and meta has details about filtering.
    """
    sample = text[:2048]
    sep = _sniff_delimiter(sample)
    try:
        df = pd.read_csv(io.StringIO(text), sep=sep, engine="c", dtype=str, keep_default_na=False)
    except Exception:
        df = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str, keep_default_na=False)

    df.columns = _normalize_cols(df.columns)
    cols = set(df.columns)

    meta = {
        "schema": None,           # "old" | "new"
        "filtered": False,
        "eng_ids": None,
        "rows_in": int(df.shape[0]),
        "rows_out": None,
    }

    if {"parent_item","child_item","sequence_no","level"}.issubset(cols):
        meta["schema"] = "old"
        out = _parse_old_schema(df)

    elif {"engine_id","system_id","parent_item_id","child_item_id","bom_level","sequenceno","path"}.issubset(cols):
        meta["schema"] = "new"
        if filter_eng_ids:
            eng_ids = sorted({str(x).strip() for x in filter_eng_ids if str(x).strip()})
            if not eng_ids:
                raise HTTPException(status_code=400, detail="eng_ids provided but empty after normalization")
            df = df[df["engine_id"].isin(eng_ids)].copy()
            meta["filtered"] = True
            meta["eng_ids"] = eng_ids
        out = _parse_new_schema(df)

    else:
        raise HTTPException(
            status_code=400,
            detail=f"CSV headers not recognized. Expected either "
                   f"[parent_item, child_item, sequence_no, level] or "
                   f"[engine_id, system_id, parent_item_id, child_item_id, bom_level, sequenceno, path]. "
                   f"Found: {list(df.columns)}"
        )

    meta["rows_out"] = int(out.shape[0])
    return out.to_dict(orient="records"), meta

def save_bytes_unique(name: str, raw: bytes) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name) or "uploaded.csv"
    p = DATA_DIR / safe
    if not p.exists():
        p.write_bytes(raw)
    return p

def read_server_csv(
    filename: str,
    filter_eng_ids: Optional[Iterable[str]] = None
) -> Tuple[str, List[Dict], Path, dict]:
    """
    Reads CSV from data/, optionally filters by eng_id (new schema only).
    Returns (dataset_sha, rows, path, meta).

    The dataset SHA is made unique per (file, filter_eng_ids) so different scoped imports
    produce distinct datasets and won't dedupe against each other.
    """
    p = DATA_DIR / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"CSV not found on server: {filename}")

    raw = p.read_bytes()
    text = raw.decode("utf-8", errors="replace")

    rows, meta = parse_csv_text(text, filter_eng_ids=filter_eng_ids)

    file_sha = sha256_bytes(raw)
    if meta["filtered"] and meta["eng_ids"]:
        scope_key = "eng_ids:" + ",".join(meta["eng_ids"])
        dataset_sha = sha256_text(file_sha + "|" + scope_key)
    else:
        dataset_sha = file_sha

    return dataset_sha, rows, p, meta
