"""
ব্রো (Bro) — এজেন্ট ম্যানেজার
সকল এজেন্টের রাউটিং, ধাপে ধাপে অনুমতি, কমান্ড ক্লাসিফিকেশন।
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.logger import get_logger

log = get_logger("agent_manager")


class StepApproval:
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


class AgentManager:
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        tts_speak: Optional[Callable[[str], None]] = None,
        stt_listen: Optional[Callable[[], str]] = None,
    ) -> None:
        cfg = config or {}
        self._agents: Dict[str, Any] = {}
        self._tts = tts_speak
        self._stt = stt_listen
        self._permission_enabled = cfg.get("permission", {}).get("enabled", True)
        self._auto_approve_simple = cfg.get("permission", {}).get("auto_approve_simple", True)
        self._timeout = cfg.get("permission", {}).get("timeout_seconds", 30)

        self._command_patterns: Dict[str, List[str]] = {
            "computer_use": ["ক্লিক", "টাইপ", "স্ক্রল", "মাউস", "click", "type", "scroll"],
            "shotcut": ["ভিডিও এডিট", "কাট", "ট্রিম", "রেন্ডার", "video edit"],
            "vscode_cua": ["VS Code", "ভিএস কোড", "কোড লেখো", "vscode"],
            "vscode_agents_hub": ["এজেন্ট", "প্লাগইন চালাও", "agent run"],
            "opencode_autopilot": ["অটোপাইলট", "কোডিং শুরু", "autopilot"],
            "video_agent": ["ভিডিও বোঝো", "ভিডিও সামারি", "video understand"],
            "autovideo": ["ভিডিও বানাও", "ভিডিও তৈরি", "create video"],
            "chromaprint": ["কোন গান", "গান চেনো", "identify song", "music"],
            "alex_core": ["প্লাগইন", "স্কিল", "plugin"],
            "keysersoze": ["মেমোরি", "ফাইল সিস্টেম", "file system"],
            "joshu": ["পরবর্তী কাজ", "সাজেস্ট", "suggest", "predict"],
            "human_bot": ["অ্যান্ড্রয়েড", "ফোন", "android", "phone"],
            "telegram": ["টেলিগ্রাম", "telegram"],
            "bantz": ["শিখো", "learn", "behavior"],
            "miniomni2": ["ওমনি", "omni"],
            "just_agents": ["লোকাল এলএলএম", "local llm"],
        }

    def register_agent(self, name: str, agent: Any) -> None:
        self._agents[name] = agent
        log.info("এজেন্ট নিবন্ধিত: %s", name)

    def classify_command(self, text: str) -> Tuple[str, float]:
        text_lower = text.lower()
        scores: Dict[str, int] = {}

        for agent_name, patterns in self._command_patterns.items():
            score = sum(1 for p in patterns if p.lower() in text_lower)
            if score > 0:
                scores[agent_name] = score

        if not scores:
            return "chat", 0.0

        best = max(scores, key=lambda k: scores[k])
        confidence = min(scores[best] / 3.0, 1.0)
        return best, confidence

    async def request_permission(self, step_description: str) -> str:
        if not self._permission_enabled:
            return StepApproval.APPROVED

        if self._tts:
            self._tts(f"এখন করব: {step_description}। অনুমতি দাও?")

        if self._stt:
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self._stt),
                    timeout=self._timeout,
                )
                response_lower = response.lower()
                if any(w in response_lower for w in ["হ্যাঁ", "yes", "ঠিক", "করো", "ok"]):
                    return StepApproval.APPROVED
                if any(w in response_lower for w in ["না", "no", "বাদ", "skip"]):
                    return StepApproval.DENIED
            except asyncio.TimeoutError:
                log.info("অনুমতির সময়সীমা শেষ — স্কিপ")
                return StepApproval.TIMEOUT

        return StepApproval.APPROVED

    async def execute_task(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        agent_name, confidence = self.classify_command(command)
        log.info("কমান্ড → এজেন্ট: %s (আত্মবিশ্বাস: %.2f)", agent_name, confidence)

        if agent_name == "chat":
            return {"agent": "chat", "status": "passthrough", "command": command}

        agent = self._agents.get(agent_name)
        if not agent:
            log.warning("এজেন্ট পাওয়া যায়নি: %s", agent_name)
            return {"agent": agent_name, "status": "unavailable", "error": f"এজেন্ট '{agent_name}' নিবন্ধিত নেই"}

        try:
            plan = await self._get_plan(agent, command, context)

            results = []
            for i, step in enumerate(plan):
                step_desc = step.get("description", f"ধাপ {i + 1}")

                if not self._auto_approve_simple or step.get("risky", False):
                    approval = await self.request_permission(step_desc)
                    if approval == StepApproval.DENIED:
                        results.append({"step": step_desc, "status": "skipped", "reason": "ব্যবহারকারী বাদ দিয়েছে"})
                        continue
                    if approval == StepApproval.TIMEOUT:
                        results.append({"step": step_desc, "status": "skipped", "reason": "সময়সীমা শেষ"})
                        continue

                try:
                    result = await self._execute_step(agent, step, context)
                    results.append({"step": step_desc, "status": "success", "result": result})
                    log.info("ধাপ সম্পন্ন: %s", step_desc)
                except Exception as exc:
                    log.error("ধাপ ব্যর্থ: %s — %s", step_desc, exc)
                    fallback = await self._try_fallback(agent, step, exc, context)
                    results.append({
                        "step": step_desc,
                        "status": "fallback" if fallback else "failed",
                        "error": str(exc),
                        "fallback_result": fallback,
                    })

            return {"agent": agent_name, "status": "completed", "results": results}

        except Exception as exc:
            log.error("এজেন্ট কার্যকর ব্যর্থ: %s — %s", agent_name, exc)
            return {"agent": agent_name, "status": "error", "error": str(exc)}

    async def _get_plan(self, agent: Any, command: str, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if hasattr(agent, "plan"):
            return await agent.plan(command, context)
        return [{"description": command, "action": "execute", "risky": False}]

    async def _execute_step(self, agent: Any, step: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Any:
        if hasattr(agent, "execute_step"):
            return await agent.execute_step(step, context)
        if hasattr(agent, "execute"):
            return await agent.execute(step.get("description", ""), context)
        raise NotImplementedError("এজেন্টে execute মেথড নেই")

    async def _try_fallback(
        self, agent: Any, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]
    ) -> Optional[Any]:
        if hasattr(agent, "fallback"):
            try:
                return await agent.fallback(step, error, context)
            except Exception:
                pass
        return None

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())

    def get_agent(self, name: str) -> Optional[Any]:
        return self._agents.get(name)
