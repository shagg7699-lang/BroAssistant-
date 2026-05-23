"""
ব্রো (Bro) — ALEX-Core প্লাগইন সিস্টেম
ডাইনামিক প্লাগইন লোড, রেজিস্ট্রেশন, লাইফসাইকেল ম্যানেজমেন্ট।
ALEX-Core ইন্সপায়ার্ড।
"""

import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("alex_core")


class PluginMeta:
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        author: str = "",
        dependencies: Optional[List[str]] = None,
    ) -> None:
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.dependencies = dependencies or []


class Plugin:
    def __init__(self, meta: PluginMeta, module: Any = None) -> None:
        self.meta = meta
        self.module = module
        self.enabled = True
        self._hooks: Dict[str, Callable] = {}

    def register_hook(self, event: str, callback: Callable) -> None:
        self._hooks[event] = callback

    async def trigger(self, event: str, data: Any = None) -> Any:
        hook = self._hooks.get(event)
        if hook:
            import asyncio
            if asyncio.iscoroutinefunction(hook):
                return await hook(data)
            return hook(data)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.meta.name,
            "version": self.meta.version,
            "description": self.meta.description,
            "author": self.meta.author,
            "enabled": self.enabled,
        }


class AlexCorePlugin:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.plugins_dir = Path(cfg.get("plugins_dir", "data/plugins"))
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._plugins: Dict[str, Plugin] = {}
        self._registry_file = self.plugins_dir / "registry.json"

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        cmd_lower = command.lower()
        if any(w in cmd_lower for w in ["তালিকা", "list"]):
            return [{"description": "প্লাগইন তালিকা", "action": "list", "risky": False}]
        if any(w in cmd_lower for w in ["ইনস্টল", "install", "লোড", "load"]):
            return [{"description": "প্লাগইন লোড", "action": "load", "risky": True}]
        return [{"description": command, "action": "manage", "risky": False}]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "plugins": len(self._plugins)}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        action = step.get("action", "")
        if action == "list":
            return self.list_plugins()
        elif action == "load":
            path = step.get("params", {}).get("path", "")
            return await self.load_plugin(path)
        return {"status": "unknown_action"}

    def register_plugin(self, meta: PluginMeta, module: Any = None) -> Plugin:
        plugin = Plugin(meta, module)
        self._plugins[meta.name] = plugin
        self._save_registry()
        log.info("প্লাগইন নিবন্ধিত: %s v%s", meta.name, meta.version)
        return plugin

    async def load_plugin(self, plugin_path: str) -> Dict[str, Any]:
        path = Path(plugin_path)
        if not path.exists():
            return {"status": "error", "error": f"পাথ পাওয়া যায়নি: {plugin_path}"}

        try:
            if path.suffix == ".py":
                spec = importlib.util.spec_from_file_location(path.stem, str(path))
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    meta = PluginMeta(
                        name=getattr(module, "PLUGIN_NAME", path.stem),
                        version=getattr(module, "PLUGIN_VERSION", "1.0.0"),
                        description=getattr(module, "PLUGIN_DESCRIPTION", ""),
                        author=getattr(module, "PLUGIN_AUTHOR", ""),
                    )

                    plugin = self.register_plugin(meta, module)

                    if hasattr(module, "on_load"):
                        await plugin.trigger("load")

                    return {"status": "loaded", "plugin": meta.name}

            return {"status": "error", "error": "অসমর্থিত ফাইল ফরম্যাট"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def unload_plugin(self, name: str) -> bool:
        if name in self._plugins:
            del self._plugins[name]
            self._save_registry()
            log.info("প্লাগইন আনলোড: %s", name)
            return True
        return False

    def enable_plugin(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        if plugin:
            plugin.enabled = True
            self._save_registry()
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        if plugin:
            plugin.enabled = False
            self._save_registry()
            return True
        return False

    def list_plugins(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "plugins": [p.to_dict() for p in self._plugins.values()],
            "count": len(self._plugins),
        }

    def get_plugin(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    async def broadcast_event(self, event: str, data: Any = None) -> Dict[str, Any]:
        results = {}
        for name, plugin in self._plugins.items():
            if plugin.enabled:
                try:
                    result = await plugin.trigger(event, data)
                    if result is not None:
                        results[name] = result
                except Exception as exc:
                    log.error("প্লাগইন ইভেন্ট ত্রুটি [%s.%s]: %s", name, event, exc)
        return results

    def _save_registry(self) -> None:
        data = [p.to_dict() for p in self._plugins.values()]
        self._registry_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        return None
