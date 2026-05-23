"""
ব্রো (Bro) — Human Bot Remote
অ্যান্ড্রয়েড ফোন থেকে পিসি রিমোট কমান্ড।
Project-Human-Bot-IGED ইন্সপায়ার্ড।
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("human_bot_remote")

try:
    from aiohttp import web

    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False
    log.warning("aiohttp ইনস্টল নেই — রিমোট সার্ভার অনুপলব্ধ")


class HumanBotRemote:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.host = cfg.get("host", "0.0.0.0")
        self.port = cfg.get("port", 8765)
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._command_handler: Optional[Any] = None
        self._running = False

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [{"description": command, "action": "remote_command", "risky": True}]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "running": self._running, "port": self.port}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        return await self.execute(step.get("description", ""), context)

    def set_command_handler(self, handler: Any) -> None:
        self._command_handler = handler

    async def start_server(self) -> bool:
        if not _HAS_AIOHTTP:
            log.error("aiohttp প্রয়োজন")
            return False

        if self._running:
            return True

        self._app = web.Application()
        self._app.router.add_post("/command", self._handle_command)
        self._app.router.add_get("/status", self._handle_status)
        self._app.router.add_get("/health", self._handle_health)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        self._running = True
        log.info("রিমোট সার্ভার চালু: %s:%d", self.host, self.port)
        return True

    async def stop_server(self) -> None:
        if self._runner:
            await self._runner.cleanup()
        self._running = False
        log.info("রিমোট সার্ভার বন্ধ")

    async def _handle_command(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            command = data.get("command", "")
            source = data.get("source", "android")

            log.info("রিমোট কমান্ড [%s]: %s", source, command[:100])

            if self._command_handler:
                if asyncio.iscoroutinefunction(self._command_handler):
                    result = await self._command_handler(command, {"source": source})
                else:
                    result = self._command_handler(command, {"source": source})
            else:
                result = {"status": "received", "command": command}

            return web.json_response(result)
        except Exception as exc:
            return web.json_response({"error": str(exc)}, status=500)

    async def _handle_status(self, request: web.Request) -> web.Response:
        return web.json_response({
            "status": "running",
            "version": "3.0",
            "name": "ব্রো",
        })

    async def _handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({"healthy": True})

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        return None
