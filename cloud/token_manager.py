"""
ব্রো (Bro) — টোকেন ম্যানেজার
একাধিক API কী ম্যানেজমেন্ট, রোটেশন, হেলথ ট্র্যাকিং।
"""

import os
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from utils.logger import get_logger

log = get_logger("token_manager")


@dataclass
class TokenInfo:
    key: str
    provider: str
    env_var: str
    healthy: bool = True
    last_used: float = 0.0
    fail_count: int = 0
    cooldown_until: float = 0.0


class TokenManager:
    COOLDOWN_SECONDS = 60
    MAX_FAILS_BEFORE_COOLDOWN = 3

    def __init__(self) -> None:
        self._tokens: Dict[str, List[TokenInfo]] = {}
        self._lock = threading.Lock()
        self._load_tokens()

    def _load_tokens(self) -> None:
        token_map = {
            "siliconflow": [
                "SILICONFLOW_DEEPSEEK_V3",
                "SILICONFLOW_QWEN3_VL_32B",
                "SILICONFLOW_DEEPSEEK_R1",
            ],
            "google": ["GOOGLE_API_KEY"],
            "github_models": ["GITHUB_TOKEN"],
            "groq": ["GROQ_API_KEY"],
            "huggingface": ["HUGGINGFACE_TOKEN"],
        }

        for provider, env_vars in token_map.items():
            tokens: List[TokenInfo] = []
            for var in env_vars:
                val = os.getenv(var)
                if val:
                    tokens.append(TokenInfo(key=val, provider=provider, env_var=var))
            if tokens:
                self._tokens[provider] = tokens
                log.info("%s: %d টোকেন লোড হয়েছে", provider, len(tokens))
            else:
                log.warning("%s: কোনো টোকেন পাওয়া যায়নি", provider)

    def get_token(self, provider: str) -> Optional[str]:
        with self._lock:
            tokens = self._tokens.get(provider, [])
            now = time.time()

            for token in tokens:
                if token.healthy and token.cooldown_until <= now:
                    token.last_used = now
                    return token.key

            for token in tokens:
                if token.cooldown_until <= now:
                    token.healthy = True
                    token.fail_count = 0
                    token.last_used = now
                    return token.key

        log.warning("কোনো সক্রিয় টোকেন নেই: %s", provider)
        return None

    def report_success(self, provider: str, key: str) -> None:
        with self._lock:
            for token in self._tokens.get(provider, []):
                if token.key == key:
                    token.fail_count = 0
                    token.healthy = True
                    break

    def report_failure(self, provider: str, key: str) -> None:
        with self._lock:
            for token in self._tokens.get(provider, []):
                if token.key == key:
                    token.fail_count += 1
                    if token.fail_count >= self.MAX_FAILS_BEFORE_COOLDOWN:
                        token.healthy = False
                        token.cooldown_until = time.time() + self.COOLDOWN_SECONDS
                        log.warning(
                            "%s টোকেন কুলডাউনে (%s): %d ব্যর্থতা",
                            provider,
                            token.env_var,
                            token.fail_count,
                        )
                    break

    def get_available_providers(self) -> List[str]:
        with self._lock:
            available = []
            now = time.time()
            for provider, tokens in self._tokens.items():
                if any(t.healthy and t.cooldown_until <= now for t in tokens):
                    available.append(provider)
            return available

    def has_provider(self, provider: str) -> bool:
        return provider in self._tokens and len(self._tokens[provider]) > 0
