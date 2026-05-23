"""
ব্রো (Bro) — বেস ক্লাউড ক্লায়েন্ট
সকল ক্লাউড প্রোভাইডারের জন্য অ্যাবস্ট্র্যাক্ট বেস ক্লাস।
"""

import abc
import asyncio
from typing import Any, Dict, List, Optional

import httpx

from cloud.token_manager import TokenManager
from utils.logger import get_logger

log = get_logger("base_cloud")


class BaseCloudClient(abc.ABC):
    def __init__(
        self,
        provider_name: str,
        base_url: str,
        token_manager: TokenManager,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        self.provider = provider_name
        self.base_url = base_url.rstrip("/")
        self.token_manager = token_manager
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _get_headers(self, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()

        for attempt in range(self.max_retries):
            token = self.token_manager.get_token(self.provider)
            if not token:
                raise ConnectionError(f"{self.provider}: কোনো সক্রিয় টোকেন নেই")

            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = self._get_headers(token)

            try:
                if method.upper() == "GET":
                    resp = await client.get(url, headers=headers, params=payload)
                else:
                    resp = await client.post(url, headers=headers, json=payload)

                if resp.status_code == 200:
                    self.token_manager.report_success(self.provider, token)
                    return resp.json()

                if resp.status_code in (401, 403, 429):
                    self.token_manager.report_failure(self.provider, token)
                    log.warning(
                        "%s: HTTP %d (attempt %d/%d)",
                        self.provider,
                        resp.status_code,
                        attempt + 1,
                        self.max_retries,
                    )
                    continue

                resp.raise_for_status()

            except httpx.TimeoutException:
                self.token_manager.report_failure(self.provider, token)
                log.warning("%s: টাইমআউট (attempt %d)", self.provider, attempt + 1)
            except httpx.HTTPStatusError as exc:
                self.token_manager.report_failure(self.provider, token)
                log.error("%s: HTTP ত্রুটি %s", self.provider, exc)
                raise

        raise ConnectionError(f"{self.provider}: সর্বোচ্চ রিট্রাই শেষ")

    @abc.abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        ...

    @abc.abstractmethod
    async def vision(
        self,
        prompt: str,
        image_base64: str,
        model: Optional[str] = None,
    ) -> str:
        ...

    async def health_check(self) -> bool:
        try:
            result = await self.chat(
                [{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(result)
        except Exception:
            return False
