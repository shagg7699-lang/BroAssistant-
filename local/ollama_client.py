"""
ব্রো (Bro) — Ollama লোকাল ক্লায়েন্ট
লোকাল LLM ব্যাকআপ — deepseek-r1:8b, qwen3:8b, qwen3-vl:8b।
"""

import os
from typing import Any, Dict, List, Optional

import httpx

from utils.logger import get_logger

log = get_logger("ollama")


class OllamaClient:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.host = cfg.get("ollama_host", os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        models = cfg.get("models", {})
        self.default_llm = models.get("llm", "deepseek-r1:8b")
        self.default_vision = models.get("vision", "qwen3-vl:8b")
        self.default_reasoning = models.get("reasoning", "qwen3:8b")
        self.timeout = cfg.get("timeout", 120)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def is_available(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.host}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.host}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            log.error("Ollama মডেল তালিকা ব্যর্থ: %s", exc)
        return []

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        model = model or self.default_llm
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            resp = await client.post(f"{self.host}/api/chat", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "")
            log.error("Ollama চ্যাট HTTP %d", resp.status_code)
        except Exception as exc:
            log.error("Ollama চ্যাট ত্রুটি: %s", exc)
        return ""

    async def vision(
        self,
        prompt: str,
        image_base64: str,
        model: Optional[str] = None,
    ) -> str:
        model = model or self.default_vision
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_base64],
                }
            ],
            "stream": False,
        }

        try:
            resp = await client.post(f"{self.host}/api/chat", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "")
            log.error("Ollama ভিশন HTTP %d", resp.status_code)
        except Exception as exc:
            log.error("Ollama ভিশন ত্রুটি: %s", exc)
        return ""

    async def reasoning(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.6,
    ) -> str:
        return await self.chat(messages, self.default_reasoning, temperature)

    async def generate(self, prompt: str, model: Optional[str] = None) -> str:
        model = model or self.default_llm
        client = await self._get_client()

        payload = {"model": model, "prompt": prompt, "stream": False}

        try:
            resp = await client.post(f"{self.host}/api/generate", json=payload)
            if resp.status_code == 200:
                return resp.json().get("response", "")
        except Exception as exc:
            log.error("Ollama generate ত্রুটি: %s", exc)
        return ""

    async def pull_model(self, model: str) -> bool:
        client = await self._get_client()
        try:
            resp = await client.post(
                f"{self.host}/api/pull",
                json={"name": model, "stream": False},
                timeout=600,
            )
            return resp.status_code == 200
        except Exception as exc:
            log.error("Ollama মডেল পুল ব্যর্থ: %s", exc)
            return False
