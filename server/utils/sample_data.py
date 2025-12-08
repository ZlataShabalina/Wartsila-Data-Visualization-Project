# server/data/sample_data.py
from __future__ import annotations
from typing import List, Dict

class SampleData:
    def __init__(self):
        self._data: List[Dict] = []  # start empty; CSV loader populates

    def get(self) -> List[Dict]:
        return self._data

    def add(self, parent: str, child: str, sequence: int, level: int) -> Dict:
        item = {
            "parent_item": parent,
            "child_item": child,
            "sequence_no": sequence,
            "level": level,
        }
        self._data.append(item)
        return item

    def clear(self) -> None:
        self._data = []

    def info(self) -> Dict:
        return {
            "total_relationships": len(self._data),
            "data_preview": self._data[:10],
            "is_empty": len(self._data) == 0,
        }

_store = SampleData()

def get_sample_data(): return _store.get()
def add_relationship(parent: str, child: str, sequence: int, level: int): return _store.add(parent, child, sequence, level)
def clear_data(): _store.clear()
def get_data_info(): return _store.info()
