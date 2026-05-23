"""
ব্রো (Bro) — Hugging Face ক্লায়েন্ট
Hugging Face Inference API ইন্টিগ্রেশন।
"""

from typing import Any, Dict, List, Optional

from cloud.base_cloud import BaseCloudClient
from cloud.token_manager import TokenManager
from utils.logger import get_logger

log = get_logger("huggingface")


class HuggingFaceClient(BaseCloudClient):
    def __init__(self, token_manager: TokenManager, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        super().__init__(
            provider_name="huggingface",
            base_url=cfg.get("base_url", "https://api-inference.huggingface.co"),
            token_manager=token_manager,
            timeout=cfg.get("timeout", 60),
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        model = model or "meta-llama/Llama-3.3-70B-Instruct"
        payload = {
            "inputs": messages[-1]["content"] if messages else "",
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
            },
        }
        data = await self._request("POST", f"/models/{model}", payload)
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "")
        return ""

    async def vision(
        self,
        prompt: str,
        image_base64: str,
        model: Optional[str] = None,
    ) -> str:
        log.warning("HuggingFace vision — সীমিত সাপোর্ট")
        return await self.chat([{"role": "user", "content": prompt}], model)

    async def text_to_image(self, prompt: str, model: str = "stabilityai/stable-diffusion-xl-base-1.0") -> bytes:
        client = await self._get_client()
        token = self.token_manager.get_token(self.provider)
        if not token:
            raise ConnectionError("HuggingFace: কোনো টোকেন নেই")

        resp = await client.post(
            f"{self.base_url}/models/{model}",
            headers=self._get_headers(token),
            json={"inputs": prompt},
        )
        if resp.status_code == 200:
            return resp.content
        raise ConnectionError(f"HuggingFace image: HTTP {resp.status_code}")
