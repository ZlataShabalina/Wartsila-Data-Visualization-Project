# server/utils/upload_csv.py
from __future__ import annotations
from fastapi import UploadFile, HTTPException
from pathlib import Path
from utils.sample_data import clear_data, add_relationship, get_sample_data
import pandas as pd
import io, re

# ---- config ----
DATA_DIR = (Path(__file__).resolve().parents[1] / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---- helpers ----
def _safe_name(name: str) -> str:
    """Sanitize the original filename (keep extension), used as canonical name on disk."""
    base = Path(name).name
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_")
    return safe or "uploaded.csv"

def _normalize_cols(cols):
    return [str(c).strip().lower().replace("\ufeff", "") for c in cols]

def _parse_csv_text(text: str) -> pd.DataFrame:
    """Auto-detect delimiter (',' or ';') and validate required headers."""
    df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
    df.columns = _normalize_cols(df.columns)
    
    new_format = ["engine_id","system_id", "parent_item_id", "child_item_id", "bom_level", "sequenceno", "path"]
    old_format = ["parent_item", "child_item", "sequence_no", "level"]
    
    if set(old_format).issubset(df.columns):
        return df
    elif set(new_format).issubset(df.columns):
        return _convert_new_to_old(df)
    else:
        missing_old = [c for c in old_format if c not in df.columns]
        missing_new = [c for c in new_format if c not in df.columns]
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns. Either need: {old_format} OR {new_format}. Found: {list(df.columns)}"
        )

def _convert_new_to_old(df: pd.DataFrame) -> pd.DataFrame:
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
            import re
            path_str = re.sub(r"^-+>", "", path_str)
            parts = [p.strip() for p in path_str.split("->") if p.strip()]
            
            if len(parts) > 1:
                # Create relationships for each consecutive pair in the path
                for i in range(len(parts) - 1):
                    parent = parts[i]
                    child = parts[i + 1]
                    rel_key = (parent, child)
                    
                    # Calculate level: first part (SYSTEM_ID) is level 1
                    level = i + 2
                    
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

def _load_df_into_store(df: pd.DataFrame) -> int:
    clear_data()
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
                relationships[rel_key] = (sequenceno, bom_level)
        
        # 3. Extract intermediate relationships from path
        if path_str:
            # Normalize path: remove leading arrows
            import re
            path_str = re.sub(r"^-+>", "", path_str)
            parts = [p.strip() for p in path_str.split("->") if p.strip()]
            
            if len(parts) > 1:
                # Create relationships for each consecutive pair in the path
                for i in range(len(parts) - 1):
                    parent = parts[i]
                    child = parts[i + 1]
                    rel_key = (parent, child)
                    
                    # Calculate level: first part (SYSTEM_ID) is level 1
                    level = i + 1
                    
                    # For intermediate nodes, use sequence 0 unless we already have data
                    if rel_key not in relationships:
                        relationships[rel_key] = (0, level)
    
    # Add all relationships to store
    for (parent, child), (sequence, level) in relationships.items():
        add_relationship(
            parent=parent,
            child=child,
            sequence=sequence,
            level=level,
        )
    
    return len(get_sample_data())

# ---- main API ----
async def upload_csv(file: UploadFile):
    """
    Behavior:
    - If a CSV with the same sanitized filename already exists in /data, do NOT overwrite;
      load it from disk and return from_cache=True.
    - Otherwise validate the uploaded content, save as <safe_name>, load it, and return from_cache=False.
    """
    try:
        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="File must be a CSV")

        safe_name = _safe_name(file.filename)
        save_path = DATA_DIR / safe_name

        # If already on disk -> reuse cached file
        if save_path.exists():
            text = save_path.read_text(encoding="utf-8", errors="replace")
            df = _parse_csv_text(text)
            n = _load_df_into_store(df)
            return {
                "message": "File already existed; loaded from disk",
                "file_name": file.filename,
                "saved_as": save_path.name,
                "saved_path": str(save_path),
                "relationships_loaded": n,
                "success": True,
                "from_cache": True,
            }

        # New file: read, validate, then persist original bytes
        raw = await file.read()
        text = raw.decode("utf-8", errors="replace")
        df = _parse_csv_text(text)  # raises 400 if invalid

        # persist (idempotent canonical name, no timestamp)
        save_path.write_bytes(raw)

        n = _load_df_into_store(df)
        return {
            "message": "CSV uploaded, saved, and loaded",
            "file_name": file.filename,
            "saved_as": save_path.name,
            "saved_path": str(save_path),
            "relationships_loaded": n,
            "success": True,
            "from_cache": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {e}")