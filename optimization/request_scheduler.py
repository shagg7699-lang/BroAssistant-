"""
ব্রো (Bro) — রিকোয়েস্ট শিডিউলার
দ্রুততম প্রোভাইডার নির্বাচন, হেলথ চেক, ফেইলওভার।
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("scheduler")


@dataclass
class ProviderHealth:
    name: str
    healthy: bool = True
    avg_latency: float = 0.0
    total_requests: int = 0
    total_failures: int = 0
    last_check: float = 0.0
    _latencies: List[float] = field(default_factory=list)

    def record_latency(self, latency: float) -> None:
        self._latencies.append(latency)
        if len(self._latencies) > 50:
            self._latencies = self._latencies[-50:]
        self.avg_latency = sum(self._latencies) / len(self._latencies)
        self.total_requests += 1

    def record_failure(self) -> None:
        self.total_failures += 1
        if self.total_failures > 5 and self.total_failures / max(self.total_requests, 1) > 0.5:
            self.healthy = False
            log.warning("প্রোভাইডার অস্বাস্থ্যকর: %s", self.name)


class RequestScheduler:
    def __init__(
        self,
        fallback_order: Optional[List[str]] = None,
        strategy: str = "fastest_first",
        health_check_interval: int = 60,
    ) -> None:
        self.fallback_order = fallback_order or [
            "google", "siliconflow", "github_models", "groq", "local"
        ]
        self.strategy = strategy
        self.health_check_interval = health_check_interval
        self._health: Dict[str, ProviderHealth] = {}

        for provider in self.fallback_order:
            self._health[provider] = ProviderHealth(name=provider)

    def select_provider(self, task_type: str = "chat") -> str:
        healthy = [
            p for p in self.fallback_order
            if self._health.get(p, ProviderHealth(name=p)).healthy
        ]

        if not healthy:
            log.warning("কোনো স্বাস্থ্যকর প্রোভাইডার নেই — প্রথম ফলব্যাক ব্যবহার")
            for p in self.fallback_order:
                self._health[p].healthy = True
            return self.fallback_order[0]

        if self.strategy == "fastest_first":
            return min(healthy, key=lambda p: self._health[p].avg_latency)
        elif self.strategy == "round_robin":
            oldest = min(healthy, key=lambda p: self._health[p].last_check)
            return oldest
        else:
            return healthy[0]

    def get_fallback_chain(self, exclude: Optional[List[str]] = None) -> List[str]:
        exclude = exclude or []
        return [
            p for p in self.fallback_order
            if p not in exclude and self._health.get(p, ProviderHealth(name=p)).healthy
        ]

    def report_success(self, provider: str, latency: float) -> None:
        health = self._health.get(provider)
        if health:
            health.record_latency(latency)
            health.healthy = True
            health.last_check = time.time()

    def report_failure(self, provider: str) -> None:
        health = self._health.get(provider)
        if health:
            health.record_failure()
            health.last_check = time.time()

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "healthy": h.healthy,
                "avg_latency_ms": round(h.avg_latency * 1000, 1),
                "total_requests": h.total_requests,
                "total_failures": h.total_failures,
            }
            for name, h in self._health.items()
        }

    async def execute_with_fallback(
        self,
        providers: Dict[str, Any],
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        chain = self.get_fallback_chain()
        last_error: Optional[Exception] = None

        for provider_name in chain:
            client = providers.get(provider_name)
            if not client:
                continue

            func = getattr(client, method, None)
            if not func:
                continue

            start = time.time()
            try:
                result = await func(*args, **kwargs)
                latency = time.time() - start
                self.report_success(provider_name, latency)
                log.info(
                    "%s.%s সফল (%.1fms)",
                    provider_name, method, latency * 1000,
                )
                return result
            except Exception as exc:
                self.report_failure(provider_name)
                last_error = exc
                log.warning("%s.%s ব্যর্থ: %s", provider_name, method, exc)

        if last_error:
            raise last_error
        raise ConnectionError("কোনো প্রোভাইডার কাজ করেনি")
