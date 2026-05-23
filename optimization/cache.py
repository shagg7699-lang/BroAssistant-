"""
ব্রো (Bro) — ক্যাশ লেয়ার
SQLite-ব্যাকড রেসপন্স ক্যাশ — TTL, LRU ইভিকশন সহ।
"""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from utils.logger import get_logger

log = get_logger("cache")

try:
    import aiosqlite

    _HAS_SQLITE = True
except ImportError:
    _HAS_SQLITE = False
    log.warning("aiosqlite ইনস্টল নেই — ক্যাশ নিষ্ক্রিয়")


class ResponseCache:
    def __init__(
        self,
        db_path: str = "data/cache.db",
        ttl_seconds: int = 3600,
        max_entries: int = 10000,
    ) -> None:
        self.db_path = db_path
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._db: Optional[Any] = None
        self._initialized = False

    async def _init_db(self) -> None:
        if self._initialized or not _HAS_SQLITE:
            return
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                provider TEXT,
                model TEXT,
                created_at REAL NOT NULL,
                accessed_at REAL NOT NULL,
                hit_count INTEGER DEFAULT 0
            )
            """
        )
        await self._db.commit()
        self._initialized = True
        log.info("ক্যাশ ডাটাবেস প্রস্তুত: %s", self.db_path)

    @staticmethod
    def _make_key(prompt: str, model: str = "", provider: str = "", context_hash: str = "") -> str:
        raw = f"{provider}:{model}:{context_hash}:{prompt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def get(self, prompt: str, model: str = "", provider: str = "", context_hash: str = "") -> Optional[str]:
        if not _HAS_SQLITE:
            return None
        await self._init_db()
        assert self._db is not None

        key = self._make_key(prompt, model, provider, context_hash)
        now = time.time()

        async with self._db.execute(
            "SELECT value, created_at FROM cache WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            value, created = row
            if now - created < self.ttl:
                await self._db.execute(
                    "UPDATE cache SET accessed_at = ?, hit_count = hit_count + 1 WHERE key = ?",
                    (now, key),
                )
                await self._db.commit()
                log.debug("ক্যাশ হিট: %s", key[:16])
                return value
            else:
                await self._db.execute("DELETE FROM cache WHERE key = ?", (key,))
                await self._db.commit()

        return None

    async def put(
        self, prompt: str, response: str, model: str = "", provider: str = "", context_hash: str = ""
    ) -> None:
        if not _HAS_SQLITE:
            return
        await self._init_db()
        assert self._db is not None

        key = self._make_key(prompt, model, provider, context_hash)
        now = time.time()

        await self._db.execute(
            """
            INSERT OR REPLACE INTO cache (key, value, provider, model, created_at, accessed_at, hit_count)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (key, response, provider, model, now, now),
        )
        await self._db.commit()
        await self._evict_if_needed()
        log.debug("ক্যাশ সেভ: %s", key[:16])

    async def _evict_if_needed(self) -> None:
        assert self._db is not None
        async with self._db.execute("SELECT COUNT(*) FROM cache") as cursor:
            row = await cursor.fetchone()
            count = row[0] if row else 0

        if count > self.max_entries:
            excess = count - self.max_entries
            await self._db.execute(
                "DELETE FROM cache WHERE key IN (SELECT key FROM cache ORDER BY accessed_at ASC LIMIT ?)",
                (excess,),
            )
            await self._db.commit()
            log.info("ক্যাশ ইভিক্ট: %d এন্ট্রি", excess)

    async def clear(self) -> None:
        if self._db:
            await self._db.execute("DELETE FROM cache")
            await self._db.commit()
            log.info("ক্যাশ সম্পূর্ণ মুছে ফেলা হয়েছে")

    async def stats(self) -> Dict[str, Any]:
        if not self._db:
            return {"entries": 0, "total_hits": 0}
        async with self._db.execute("SELECT COUNT(*), COALESCE(SUM(hit_count), 0) FROM cache") as cursor:
            row = await cursor.fetchone()
        return {"entries": row[0] if row else 0, "total_hits": row[1] if row else 0}

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
            self._initialized = False
