# server/storage/sql_repository.py
from __future__ import annotations
from typing import Iterable, Optional, List, Dict
from sqlalchemy import select, func, insert
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import UploadFile, Relationship

class SqlGraphRepository:
    def __init__(self, session: AsyncSession):
        self._db = session

    async def list_datasets(self) -> list[dict]:
        res = await self._db.execute(select(UploadFile).order_by(UploadFile.created_at.desc()))
        return [
            {
                "dataset_id": ds.id,
                "original_name": ds.original_name,
                "saved_path": ds.saved_path,
                "sha256": ds.sha256,
                "rows_loaded": ds.rows_loaded,
                "created_at": str(ds.created_at) if ds.created_at else None,
            }
            for ds in res.scalars()
        ]

    async def get_dataset_id_by_sha(self, sha256: str) -> Optional[int]:
        res = await self._db.execute(select(UploadFile.id).where(UploadFile.sha256 == sha256).limit(1))
        return res.scalar_one_or_none()

    async def insert_dataset(self, original_name: str, saved_path: str, sha256: str, rows: List[Dict]) -> int:
        # Create dataset row
        ds = UploadFile(
            original_name=original_name,
            saved_path=saved_path,
            sha256=sha256,
            rows_loaded=0,
            is_active=False,  # keep old schemas happy
        )
        self._db.add(ds)
        await self._db.flush()  # get ds.id

        # Prepare relationship payload for executemany
        payload = [
            {
                "dataset_id": ds.id,
                "parent_item": r["parent_item"],
                "child_item":  r["child_item"],
                "sequence_no": r["sequence_no"],
                "level":       r["level"],
            }
            for r in rows
        ]

        if payload:
            stmt = insert(Relationship)
            await self._db.execute(stmt, payload)

        ds.rows_loaded = len(payload)
        await self._db.commit()
        return ds.id

    async def list_roots(self, dataset_id: int) -> list[str]:
        parents = select(Relationship.parent_item).where(Relationship.dataset_id == dataset_id).subquery()
        children = select(Relationship.child_item).where(Relationship.dataset_id == dataset_id).subquery()
        q = select(func.distinct(parents.c.parent_item)).where(
            ~parents.c.parent_item.in_(select(children.c.child_item))
        ).order_by(parents.c.parent_item.asc())
        res = await self._db.execute(q)
        return [r[0] for r in res.fetchall()]

    async def get_children(self, dataset_id: int, parent_id: str, limit: int | None = None) -> list[dict]:
        q = (
            select(Relationship.child_item, Relationship.sequence_no, Relationship.level)
            .where((Relationship.dataset_id == dataset_id) & (Relationship.parent_item == parent_id))
            .order_by(Relationship.sequence_no.asc())
        )
        if limit:
            q = q.limit(limit)
        res = await self._db.execute(q)
        rows = res.fetchall()
    
        if not rows:
            return []
        
        # Build result with num_children
        result = []
        for row in rows:
            # Check if this child has children
            check_q = select(func.count()).select_from(Relationship).where(
                (Relationship.dataset_id == dataset_id) & 
                (Relationship.parent_item == row.child_item)
            )
            count_res = await self._db.execute(check_q)
            num_children = count_res.scalar()
            
            result.append({
                "id": row.child_item,
                "name": row.child_item,
                "sequence_no": row.sequence_no,
                "level": row.level,
                "num_children": num_children  # Number of Children
            })
        
        return result

    async def get_parent(self, dataset_id: int, node_id: str) -> Optional[dict]:
        q = (
            select(Relationship.parent_item, Relationship.sequence_no, Relationship.level)
            .where((Relationship.dataset_id == dataset_id) & (Relationship.child_item == node_id))
            .order_by(Relationship.level.asc(), Relationship.sequence_no.asc())
        )
        res = await self._db.execute(q)
        rows = res.fetchall()
        
        parents = []
        for row in rows:
            parent_id = row.parent_item
            
            # Get the parent's own parent data
            q2 = (
                select(Relationship.sequence_no, Relationship.level)
                .where((Relationship.dataset_id == dataset_id) & (Relationship.child_item == parent_id))
                .limit(1)
            )
            res2 = await self._db.execute(q2)
            parent_data = res2.first()
            
            if parent_data:
                parents.append({
                    "id": parent_id,
                    "name": parent_id,
                    "sequence_no": parent_data.sequence_no,
                    "level": parent_data.level
                })
            else:
                # If parent has no parent (it's a root), return with default values
                parents.append({
                    "id": parent_id,
                    "name": parent_id,
                    "sequence_no": 0,
                    "level": 0
                })
        
        return parents


    async def find_path_to_child(self, dataset_id: int, child_id: str) -> dict:
        # Fetch all parent-child relationships for the given dataset
        q = select(Relationship.parent_item, Relationship.child_item).where(
            Relationship.dataset_id == dataset_id
        )
        res = await self._db.execute(q)
        rows = res.fetchall()

        # Build parent map
        parent_map = {child: parent for parent, child in rows}

        # Handle case where child_id does not exist
        if child_id not in parent_map and all(child_id != p for p, c in rows):
            return {"path": []}

        # Reconstruct path from child up to root
        path = [child_id]
        current = child_id
        while current in parent_map:
            parent = parent_map[current]
            path.append(parent)
            current = parent

        path = list(reversed(path))

        # Build structured path list
        structured_path = []
        for i in range(len(path)):
            if i < len(path) - 1:
                structured_path.append({
                    "id": path[i],
                    "child_id": path[i + 1],
                    "child_name": path[i + 1]
                })
            else:
                # Last node (no further child)
                structured_path.append({
                    "id": path[i],
                    "child_id": "",
                    "child_name": ""
                })

        return {"path": structured_path}




