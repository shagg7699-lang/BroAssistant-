"""
ব্রো (Bro) — Google AI (Gemini) ক্লায়েন্ট
Gemini 3.5 Flash API ইন্টিগ্রেশন — চ্যাট ও ভিশন।
"""

import os
from typing import Any, Dict, List, Optional

from cloud.base_cloud import BaseCloudClient
from cloud.token_manager import TokenManager
from utils.logger import get_logger

log = get_logger("google_client")


class GoogleClient(BaseCloudClient):
    def __init__(self, token_manager: TokenManager, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        super().__init__(
            provider_name="google",
            base_url=cfg.get("base_url", "https://generativelanguage.googleapis.com/v1beta"),
            token_manager=token_manager,
            timeout=cfg.get("timeout", 30),
        )
        self.default_llm = cfg.get("models", {}).get("llm", "gemini-3.5-flash")
        self.default_vision = cfg.get("models", {}).get("vision", "gemini-3.5-flash")
        self.max_tokens = cfg.get("max_tokens", 8192)
        self.temperature = cfg.get("temperature", 0.7)

    def _get_headers(self, token: str) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    def _build_url(self, model: str, token: str) -> str:
        return f"{self.base_url}/models/{model}:generateContent?key={token}"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        model = model or self.default_llm
        token = self.token_manager.get_token(self.provider)
        if not token:
            raise ConnectionError("Google: কোনো API কী নেই")

        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        client = await self._get_client()
        url = self._build_url(model, token)

        for attempt in range(self.max_retries):
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    self.token_manager.report_success(self.provider, token)
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        return parts[0].get("text", "") if parts else ""
                    return ""
                self.token_manager.report_failure(self.provider, token)
                log.warning("Google HTTP %d (attempt %d)", resp.status_code, attempt + 1)
            except Exception as exc:
                self.token_manager.report_failure(self.provider, token)
                log.error("Google চ্যাট ত্রুটি: %s", exc)

        raise ConnectionError("Google: সর্বোচ্চ রিট্রাই শেষ")

    async def vision(
        self,
        prompt: str,
        image_base64: str,
        model: Optional[str] = None,
    ) -> str:
        model = model or self.default_vision
        token = self.token_manager.get_token(self.provider)
        if not token:
            raise ConnectionError("Google: কোনো API কী নেই")

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": image_base64,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": self.max_tokens,
            },
        }

        client = await self._get_client()
        url = self._build_url(model, token)

        resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            self.token_manager.report_success(self.provider, token)
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return parts[0].get("text", "") if parts else ""
        self.token_manager.report_failure(self.provider, token)
        raise ConnectionError(f"Google Vision: HTTP {resp.status_code}")
