"""
ব্রো (Bro) — Groq ক্লায়েন্ট
Llama 3.3 70B, Llama 3.2 Vision — অতিদ্রুত ইনফারেন্স।
"""

from typing import Any, Dict, List, Optional

from cloud.base_cloud import BaseCloudClient
from cloud.token_manager import TokenManager
from utils.logger import get_logger

log = get_logger("groq")


class GroqClient(BaseCloudClient):
    def __init__(self, token_manager: TokenManager, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        super().__init__(
            provider_name="groq",
            base_url=cfg.get("base_url", "https://api.groq.com/openai/v1"),
            token_manager=token_manager,
            timeout=cfg.get("timeout", 30),
        )
        models = cfg.get("models", {})
        self.default_llm = models.get("llm", "llama-3.3-70b-versatile")
        self.default_vision = models.get("vision", "llama-3.2-11b-vision-preview")
        self.max_tokens = cfg.get("max_tokens", 4096)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        model = model or self.default_llm
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = await self._request("POST", "/chat/completions", payload)
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""

    async def vision(
        self,
        prompt: str,
        image_base64: str,
        model: Optional[str] = None,
    ) -> str:
        model = model or self.default_vision
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ],
            }
        ]
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }
        data = await self._request("POST", "/chat/completions", payload)
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""
