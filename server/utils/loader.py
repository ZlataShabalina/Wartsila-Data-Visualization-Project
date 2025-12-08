# server/utils/loader.py
from __future__ import annotations
from pathlib import Path
from fastapi import HTTPException
from utils.sample_data import clear_data, add_relationship, get_sample_data
import pandas as pd, io

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def list_csv_files() -> list[dict]:
    out = []
    for p in sorted(DATA_DIR.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True):
        st = p.stat()
        out.append({"name": p.name, "size": st.st_size, "modified_at": int(st.st_mtime)})
    return out

def _normalize_cols(cols):
    return [str(c).strip().lower().replace("\ufeff", "") for c in cols]

def _extract_parent_from_path(path: str, child: str) -> str:
    """Extract parent from path string.
    Two cases in the data:
    1. Path includes child: '->MODMAT000001->MAT000121' where child='MAT000121'
       → parent is second-to-last element
    2. Path excludes child: '->MODMAT000001->MAT000121->MAT003121' where child='MAT000122'
       → parent is last element (child is one level deeper than path shows)
    """
    parts = [p.strip() for p in path.split('->') if p.strip()]
    
    if not parts:
        return child  # fallback
    
    # Check if last element in path matches the child
    if len(parts) >= 2 and parts[-1] == child:
        return parts[-2]
    else:
        return parts[-1]

def _parse_csv_text(text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
    df.columns = _normalize_cols(df.columns)
    
    # Check for new format columns
    new_format = ["engine_id","system_id", "parent_item_id", "child_item_id", "bom_level", "sequenceno", "path"]
    old_format = ["parent_item", "child_item", "sequence_no", "level"]
    
    has_new = all(c in df.columns for c in new_format)
    has_old = all(c in df.columns for c in old_format)
    
    if set(old_format).issubset(df.columns):
        return df
    elif set(new_format).issubset(df.columns):
        # Import the conversion function from upload_csv
        from utils.upload_csv import _convert_new_to_old
        return _convert_new_to_old(df)
    else:
        missing_old = [c for c in old_format if c not in df.columns]
        missing_new = [c for c in new_format if c not in df.columns]
        raise HTTPException(status_code=400, detail=f"Missing required columns. Either need: {old_format} OR {new_format}. Found: {list(df.columns)}")

def load_csv_file(path: Path) -> int:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"CSV not found: {path.name}")
    text = path.read_text(encoding="utf-8", errors="replace")
    df = _parse_csv_text(text)
    clear_data()

    relationships = {}  # (parent, child) -> (sequence, level)
    
    for idx, row in df.iterrows():
        # Handle both old and new formats
        if 'engine_id' in row.index:  # New format
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
        
        else:  # Old format
            parent = str(row["parent_item"])
            child = str(row["child_item"])
            rel_key = (parent, child)
            sequence = int(row.get("sequence_no", 0))
            level = int(row.get("level", 1))
            
            if rel_key not in relationships:
                relationships[rel_key] = (sequence, level)
    
    # Add all relationships to store
    for (parent, child), (sequence, level) in relationships.items():
        add_relationship(
            parent=parent,
            child=child,
            sequence=sequence,
            level=level,
        )
    
    return len(get_sample_data())

def latest_csv() -> Path | None:
    files = sorted(DATA_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def ensure_data_loaded() -> dict:
    if get_sample_data():
        return {"loaded": False, "reason": "already_in_memory"}
    p = latest_csv()
    if not p:
        raise HTTPException(status_code=404, detail="No CSV loaded and no files found in /data")
    n = load_csv_file(p)
    return {"loaded": True, "from_file": p.name, "relationships": n}