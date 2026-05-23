"""
ব্রো (Bro) — হাইব্রিড মেমোরি ম্যানেজার
JSON-ব্যাকড পারসিস্ট্যান্ট মেমোরি — ফ্যাক্ট, কনভার্সেশন ও ইউজার প্রেফারেন্স সংরক্ষণ।
"""

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("memory")


class MemoryEntry:
    __slots__ = ("key", "value", "category", "timestamp", "access_count")

    def __init__(self, key: str, value: Any, category: str = "general") -> None:
        self.key = key
        self.value = value
        self.category = category
        self.timestamp = time.time()
        self.access_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        entry = cls(data["key"], data["value"], data.get("category", "general"))
        entry.timestamp = data.get("timestamp", time.time())
        entry.access_count = data.get("access_count", 0)
        return entry


class BroMemory:
    def __init__(self, file_path: str = "data/bro_memory.json", max_entries: int = 5000) -> None:
        self._file = Path(file_path)
        self._max = max_entries
        self._store: Dict[str, MemoryEntry] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if self._file.exists():
            try:
                raw = json.loads(self._file.read_text(encoding="utf-8"))
                for item in raw:
                    entry = MemoryEntry.from_dict(item)
                    self._store[entry.key] = entry
                log.info("মেমোরি লোড হয়েছে: %d এন্ট্রি", len(self._store))
            except (json.JSONDecodeError, KeyError) as exc:
                log.warning("মেমোরি লোড ব্যর্থ, নতুন শুরু: %s", exc)

    def save(self) -> None:
        with self._lock:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            data = [e.to_dict() for e in self._store.values()]
            self._file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        log.debug("মেমোরি সেভ হয়েছে: %d এন্ট্রি", len(self._store))

    def remember(self, key: str, value: Any, category: str = "general") -> None:
        with self._lock:
            self._store[key] = MemoryEntry(key, value, category)
            self._evict_if_needed()
        self.save()
        log.info("মনে রাখা হলো: [%s] %s", category, key)

    def recall(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry:
                entry.access_count += 1
                return entry.value
        return None

    def search(self, query: str, category: Optional[str] = None) -> List[MemoryEntry]:
        results = []
        q_lower = query.lower()
        with self._lock:
            for entry in self._store.values():
                if category and entry.category != category:
                    continue
                if q_lower in entry.key.lower() or q_lower in str(entry.value).lower():
                    results.append(entry)
        return sorted(results, key=lambda e: e.access_count, reverse=True)

    def forget(self, key: str) -> bool:
        with self._lock:
            removed = self._store.pop(key, None)
        if removed:
            self.save()
            return True
        return False

    def list_categories(self) -> List[str]:
        with self._lock:
            return list({e.category for e in self._store.values()})

    def get_all(self, category: Optional[str] = None) -> List[MemoryEntry]:
        with self._lock:
            entries = list(self._store.values())
        if category:
            entries = [e for e in entries if e.category == category]
        return entries

    def _evict_if_needed(self) -> None:
        while len(self._store) > self._max:
            oldest_key = min(self._store, key=lambda k: self._store[k].timestamp)
            del self._store[oldest_key]

    @property
    def size(self) -> int:
        return len(self._store)
