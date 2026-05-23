"""
ব্রো (Bro) — SiliconFlow ক্লায়েন্ট
DeepSeek-V3, DeepSeek-R1, Qwen3-VL-32B ইন্টিগ্রেশন।
"""

from typing import Any, Dict, List, Optional

from cloud.base_cloud import BaseCloudClient
from cloud.token_manager import TokenManager
from utils.logger import get_logger

log = get_logger("siliconflow")


class SiliconFlowClient(BaseCloudClient):
    def __init__(self, token_manager: TokenManager, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        super().__init__(
            provider_name="siliconflow",
            base_url=cfg.get("base_url", "https://api.siliconflow.cn/v1"),
            token_manager=token_manager,
            timeout=cfg.get("timeout", 30),
        )
        models = cfg.get("models", {})
        self.default_llm = models.get("llm", "deepseek-ai/DeepSeek-V3")
        self.default_reasoning = models.get("reasoning", "deepseek-ai/DeepSeek-R1")
        self.default_vision = models.get("vision", "Qwen/Qwen2.5-VL-32B-Instruct")
        self.max_tokens = cfg.get("max_tokens", 4096)
        self.temperature = cfg.get("temperature", 0.7)

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

    async def reasoning(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.6,
        max_tokens: int = 8192,
    ) -> str:
        return await self.chat(messages, self.default_reasoning, temperature, max_tokens)

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
