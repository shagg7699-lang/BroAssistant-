"""
ব্রো (Bro) — VS Code CUA (Computer Use Automation) এজেন্ট
VS Code উইন্ডোতে pyautogui দিয়ে সরাসরি কোডিং অটোমেশন।
CUA-VSCode-GHCP-Agent-Automation ইন্সপায়ার্ড।
"""

import asyncio
import subprocess
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("vscode_cua")

try:
    import pyautogui

    _HAS_GUI = True
except ImportError:
    _HAS_GUI = False


class VSCodeCUAAgent:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.workspace_path = cfg.get("workspace_path", "")
        self._vscode_cmd = self._find_vscode()

    def _find_vscode(self) -> Optional[str]:
        for cmd in ["code", "code-insiders", "codium"]:
            if shutil.which(cmd):
                return cmd
        return None

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        steps = []
        cmd_lower = command.lower()

        if "খোলো" in cmd_lower or "open" in cmd_lower:
            steps.append({"description": "VS Code খুলুন", "action": "open_vscode", "risky": False})

        if any(w in cmd_lower for w in ["লেখো", "write", "কোড", "code"]):
            steps.append({"description": "কোড লিখুন", "action": "write_code", "risky": True})

        if any(w in cmd_lower for w in ["চালাও", "run", "টার্মিনাল", "terminal"]):
            steps.append({"description": "টার্মিনালে কমান্ড চালান", "action": "run_terminal", "risky": True})

        if not steps:
            steps.append({"description": command, "action": "execute", "risky": True})

        return steps

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "vscode": self._vscode_cmd is not None, "gui": _HAS_GUI}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        action = step.get("action", "")

        if action == "open_vscode":
            return await self.open_vscode(step.get("params", {}).get("path", self.workspace_path))
        elif action == "write_code":
            return await self.write_code_to_file(
                step.get("params", {}).get("file", ""),
                step.get("params", {}).get("code", ""),
            )
        elif action == "run_terminal":
            return await self.run_in_terminal(step.get("params", {}).get("command", ""))
        elif action == "open_file":
            return await self.open_file(step.get("params", {}).get("file", ""))
        return {"status": "unknown_action"}

    async def open_vscode(self, path: str = "") -> Dict[str, Any]:
        if not self._vscode_cmd:
            return {"status": "error", "error": "VS Code পাওয়া যায়নি"}

        cmd = [self._vscode_cmd]
        if path:
            cmd.append(path)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            log.info("VS Code খোলা হচ্ছে: %s", path or "(default)")
            return {"status": "opened", "path": path}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def open_file(self, file_path: str) -> Dict[str, Any]:
        if not self._vscode_cmd:
            return {"status": "error", "error": "VS Code পাওয়া যায়নি"}

        try:
            await asyncio.create_subprocess_exec(
                self._vscode_cmd, "--goto", file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            return {"status": "opened", "file": file_path}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def write_code_to_file(self, file_path: str, code: str) -> Dict[str, Any]:
        if not file_path or not code:
            return {"status": "error", "error": "ফাইল পাথ ও কোড প্রয়োজন"}

        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code, encoding="utf-8")
            log.info("কোড লেখা হয়েছে: %s", file_path)

            if self._vscode_cmd:
                await self.open_file(file_path)

            return {"status": "written", "file": file_path, "lines": code.count("\n") + 1}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def run_in_terminal(self, command: str) -> Dict[str, Any]:
        if not command:
            return {"status": "error", "error": "কমান্ড প্রয়োজন"}

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

            return {
                "status": "executed",
                "returncode": proc.returncode,
                "stdout": stdout.decode()[:2000],
                "stderr": stderr.decode()[:1000],
            }
        except asyncio.TimeoutError:
            return {"status": "timeout"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def send_keys_to_vscode(self, keys: List[str]) -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error", "error": "pyautogui অনুপলব্ধ"}

        try:
            await asyncio.to_thread(pyautogui.hotkey, *keys)
            return {"status": "keys_sent", "keys": keys}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        log.info("VS Code CUA ফলব্যাক — ফাইল সরাসরি লেখা চেষ্টা")
        return None
