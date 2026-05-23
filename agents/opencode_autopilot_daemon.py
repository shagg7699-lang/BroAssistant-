"""
ব্রো (Bro) — OpenCode Autopilot ডেমন
স্বয়ংক্রিয় কোডিং — ফাইল তৈরি, এডিট, রিফ্যাক্টর, টেস্ট।
OpenCode-Autopilot ইন্সপায়ার্ড।
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("opencode_autopilot")


class OpenCodeAutopilotDaemon:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.workspace: Optional[str] = cfg.get("workspace_path")
        self._running = False

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        cmd_lower = command.lower()
        steps = []

        if any(w in cmd_lower for w in ["তৈরি", "create", "বানাও"]):
            steps.append({"description": "ফাইল তৈরি", "action": "create_file", "risky": True})
        if any(w in cmd_lower for w in ["এডিট", "edit", "পরিবর্তন", "modify"]):
            steps.append({"description": "কোড সম্পাদনা", "action": "edit_file", "risky": True})
        if any(w in cmd_lower for w in ["টেস্ট", "test"]):
            steps.append({"description": "টেস্ট চালান", "action": "run_tests", "risky": False})
        if any(w in cmd_lower for w in ["রিফ্যাক্টর", "refactor"]):
            steps.append({"description": "কোড রিফ্যাক্টরিং", "action": "refactor", "risky": True})

        if not steps:
            steps.append({"description": command, "action": "auto_code", "risky": True})

        return steps

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "workspace": self.workspace}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        action = step.get("action", "")
        params = step.get("params", {})

        if action == "create_file":
            return await self.create_file(
                params.get("path", ""),
                params.get("content", ""),
            )
        elif action == "edit_file":
            return await self.edit_file(
                params.get("path", ""),
                params.get("changes", []),
            )
        elif action == "run_tests":
            return await self.run_tests(params.get("path", "."))
        elif action == "refactor":
            return await self.refactor(
                params.get("path", ""),
                params.get("instruction", ""),
            )
        elif action == "auto_code":
            return await self.auto_code(step.get("description", ""))
        return {"status": "unknown_action"}

    async def create_file(self, file_path: str, content: str) -> Dict[str, Any]:
        if not file_path:
            return {"status": "error", "error": "ফাইল পাথ প্রয়োজন"}

        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            log.info("ফাইল তৈরি: %s", file_path)
            return {"status": "created", "file": file_path, "size": len(content)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def edit_file(self, file_path: str, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not file_path or not Path(file_path).exists():
            return {"status": "error", "error": "ফাইল পাওয়া যায়নি"}

        try:
            content = Path(file_path).read_text(encoding="utf-8")
            for change in changes:
                old = change.get("old", "")
                new = change.get("new", "")
                if old in content:
                    content = content.replace(old, new, 1)

            Path(file_path).write_text(content, encoding="utf-8")
            log.info("ফাইল সম্পাদিত: %s (%d পরিবর্তন)", file_path, len(changes))
            return {"status": "edited", "file": file_path, "changes": len(changes)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def run_tests(self, path: str = ".") -> Dict[str, Any]:
        test_commands = [
            ["python", "-m", "pytest", path, "-v", "--tb=short"],
            ["python", "-m", "unittest", "discover", "-s", path],
        ]

        for cmd in test_commands:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
                return {
                    "status": "completed",
                    "returncode": proc.returncode,
                    "output": stdout.decode()[:3000],
                    "errors": stderr.decode()[:1000],
                }
            except (FileNotFoundError, asyncio.TimeoutError):
                continue

        return {"status": "error", "error": "কোনো টেস্ট রানার পাওয়া যায়নি"}

    async def refactor(self, file_path: str, instruction: str) -> Dict[str, Any]:
        return {
            "status": "pending",
            "message": "রিফ্যাক্টরিং-এর জন্য LLM ইনপুট প্রয়োজন",
            "file": file_path,
            "instruction": instruction,
        }

    async def auto_code(self, description: str) -> Dict[str, Any]:
        return {
            "status": "pending",
            "message": "অটো-কোডিং-এর জন্য LLM ইনপুট প্রয়োজন",
            "description": description,
        }

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        log.info("Autopilot ফলব্যাক: %s", error)
        return None
