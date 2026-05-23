"""
ব্রো (Bro) — keysersoze ফ্রেমওয়ার্ক
উন্নত মেমোরি ব্যাকএন্ড, ফাইল সিস্টেম অপারেশন, কনটেক্সট ম্যানেজমেন্ট।
keysersoze-framework ইন্সপায়ার্ড।
"""

import asyncio
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("keysersoze")


class KnowledgeEntry:
    def __init__(self, topic: str, content: str, source: str = "", tags: Optional[List[str]] = None) -> None:
        self.topic = topic
        self.content = content
        self.source = source
        self.tags = tags or []
        self.created = datetime.now().isoformat()
        self.updated = self.created

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "content": self.content,
            "source": self.source,
            "tags": self.tags,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEntry":
        entry = cls(data["topic"], data["content"], data.get("source", ""), data.get("tags", []))
        entry.created = data.get("created", entry.created)
        entry.updated = data.get("updated", entry.updated)
        return entry


class KeysersozeFramework:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self._data_dir = Path(cfg.get("data_dir", "data"))
        self._knowledge_file = self._data_dir / "knowledge_base.json"
        self._knowledge: Dict[str, KnowledgeEntry] = {}
        self._load_knowledge()

    def _load_knowledge(self) -> None:
        if self._knowledge_file.exists():
            try:
                data = json.loads(self._knowledge_file.read_text(encoding="utf-8"))
                for item in data:
                    entry = KnowledgeEntry.from_dict(item)
                    self._knowledge[entry.topic] = entry
            except Exception as exc:
                log.warning("নলেজ বেস লোড ব্যর্থ: %s", exc)

    def _save_knowledge(self) -> None:
        data = [e.to_dict() for e in self._knowledge.values()]
        self._knowledge_file.parent.mkdir(parents=True, exist_ok=True)
        self._knowledge_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [{"description": command, "action": "manage", "risky": False}]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "knowledge_entries": len(self._knowledge)}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        return await self.execute(step.get("description", ""), context)

    def add_knowledge(self, topic: str, content: str, source: str = "", tags: Optional[List[str]] = None) -> None:
        self._knowledge[topic] = KnowledgeEntry(topic, content, source, tags)
        self._save_knowledge()
        log.info("নলেজ যোগ: %s", topic)

    def get_knowledge(self, topic: str) -> Optional[KnowledgeEntry]:
        return self._knowledge.get(topic)

    def search_knowledge(self, query: str) -> List[KnowledgeEntry]:
        q_lower = query.lower()
        results = []
        for entry in self._knowledge.values():
            if (
                q_lower in entry.topic.lower()
                or q_lower in entry.content.lower()
                or any(q_lower in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)
        return results

    def remove_knowledge(self, topic: str) -> bool:
        if topic in self._knowledge:
            del self._knowledge[topic]
            self._save_knowledge()
            return True
        return False

    async def list_files(self, directory: str, pattern: str = "*") -> List[Dict[str, Any]]:
        path = Path(directory)
        if not path.exists():
            return []

        files = []
        for f in path.glob(pattern):
            stat = f.stat()
            files.append({
                "name": f.name,
                "path": str(f),
                "size": stat.st_size,
                "is_dir": f.is_dir(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return sorted(files, key=lambda x: x["name"])

    async def read_file(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"status": "error", "error": "ফাইল পাওয়া যায়নি"}
        try:
            content = path.read_text(encoding="utf-8")
            return {"status": "success", "content": content, "size": len(content)}
        except UnicodeDecodeError:
            return {"status": "binary", "size": path.stat().st_size}

    async def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {"status": "written", "path": file_path, "size": len(content)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def file_info(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"status": "not_found"}
        stat = path.stat()
        return {
            "status": "success",
            "name": path.name,
            "size": stat.st_size,
            "extension": path.suffix,
            "is_dir": path.is_dir(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "md5": hashlib.md5(path.read_bytes()).hexdigest() if path.is_file() else None,
        }

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        return None
