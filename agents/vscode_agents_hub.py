"""
ব্রো (Bro) — VS Code Agents Hub
vscode-agents ইন্সপায়ার্ড — বহু-এজেন্ট অটোমেশন হাব।
84 agents, 62 plugins কনসেপ্ট।
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("vscode_agents_hub")


class VSCodePlugin:
    def __init__(self, name: str, description: str, handler: Optional[Callable] = None) -> None:
        self.name = name
        self.description = description
        self.handler = handler
        self.enabled = True

    async def execute(self, params: Dict[str, Any]) -> Any:
        if self.handler:
            if asyncio.iscoroutinefunction(self.handler):
                return await self.handler(params)
            return self.handler(params)
        return {"status": "no_handler", "plugin": self.name}


class VSCodeAgentsHub:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._plugins: Dict[str, VSCodePlugin] = {}
        self._register_builtin_plugins()

    def _register_builtin_plugins(self) -> None:
        builtins = [
            ("file_create", "নতুন ফাইল তৈরি"),
            ("file_edit", "ফাইল সম্পাদনা"),
            ("file_search", "ফাইল খোঁজা"),
            ("code_format", "কোড ফরম্যাট"),
            ("code_lint", "কোড লিন্ট"),
            ("git_commit", "গিট কমিট"),
            ("git_push", "গিট পুশ"),
            ("terminal_run", "টার্মিনাল কমান্ড"),
            ("dependency_install", "ডিপেন্ডেন্সি ইনস্টল"),
            ("test_run", "টেস্ট চালান"),
            ("debug_start", "ডিবাগিং শুরু"),
            ("snippet_insert", "কোড স্নিপেট"),
            ("refactor", "রিফ্যাক্টরিং"),
            ("documentation", "ডকুমেন্টেশন জেনারেট"),
        ]
        for name, desc in builtins:
            self._plugins[name] = VSCodePlugin(name, desc)

    def register_plugin(self, name: str, description: str, handler: Optional[Callable] = None) -> None:
        self._plugins[name] = VSCodePlugin(name, description, handler)
        log.info("প্লাগইন নিবন্ধিত: %s", name)

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [{"description": command, "action": "route_plugin", "risky": False}]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        matching = self._find_plugins(command)
        if not matching:
            return {"status": "no_matching_plugin", "available": list(self._plugins.keys())}

        results = []
        for plugin in matching:
            result = await plugin.execute({"command": command, "context": context})
            results.append({"plugin": plugin.name, "result": result})

        return {"status": "executed", "results": results}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        return await self.execute(step.get("description", ""), context)

    def _find_plugins(self, command: str) -> List[VSCodePlugin]:
        cmd_lower = command.lower()
        matching = []
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue
            if plugin.name in cmd_lower or any(
                w in cmd_lower for w in plugin.description.lower().split()
            ):
                matching.append(plugin)
        return matching

    def list_plugins(self) -> List[Dict[str, str]]:
        return [
            {"name": p.name, "description": p.description, "enabled": p.enabled}
            for p in self._plugins.values()
        ]

    def enable_plugin(self, name: str) -> bool:
        if name in self._plugins:
            self._plugins[name].enabled = True
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        if name in self._plugins:
            self._plugins[name].enabled = False
            return True
        return False
