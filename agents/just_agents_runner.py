"""
ব্রো (Bro) — Just-Agents Runner
লোকাল LLM রানার — Ollama, llama.cpp ইত্যাদির উপর অ্যাবস্ট্র্যাকশন।
Just-Agents ইন্সপায়ার্ড।
"""

import asyncio
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("just_agents")


class AgentConfig:
    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> None:
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens


class JustAgentsRunner:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self._ollama_host = cfg.get("ollama_host", "http://localhost:11434")
        self._agents: Dict[str, AgentConfig] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            AgentConfig("coder", "deepseek-r1:8b", "তুমি একজন দক্ষ কোডার। পাইথনে কোড লেখো।"),
            AgentConfig("writer", "qwen3:8b", "তুমি একজন লেখক। সুন্দর বাংলায় লেখো।"),
            AgentConfig("analyst", "deepseek-r1:8b", "তুমি একজন ডেটা বিশ্লেষক।"),
            AgentConfig("translator", "qwen3:8b", "তুমি একজন অনুবাদক। বাংলা ↔ ইংরেজি অনুবাদ করো।"),
        ]
        for agent in defaults:
            self._agents[agent.name] = agent

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [{"description": command, "action": "run_agent", "risky": False}]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "agents": list(self._agents.keys())}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        return await self.execute(step.get("description", ""), context)

    def register_agent(self, agent: AgentConfig) -> None:
        self._agents[agent.name] = agent
        log.info("এজেন্ট নিবন্ধিত: %s (%s)", agent.name, agent.model)

    async def run(
        self,
        agent_name: str,
        prompt: str,
        ollama_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        agent = self._agents.get(agent_name)
        if not agent:
            return {"status": "error", "error": f"এজেন্ট পাওয়া যায়নি: {agent_name}"}

        messages = []
        if agent.system_prompt:
            messages.append({"role": "system", "content": agent.system_prompt})
        messages.append({"role": "user", "content": prompt})

        if ollama_client:
            try:
                response = await ollama_client.chat(
                    messages, agent.model, agent.temperature
                )
                return {
                    "status": "success",
                    "agent": agent_name,
                    "model": agent.model,
                    "response": response,
                }
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

        return {
            "status": "pending",
            "agent": agent_name,
            "message": "Ollama ক্লায়েন্ট প্রয়োজন",
        }

    async def run_chain(
        self,
        agent_names: List[str],
        initial_prompt: str,
        ollama_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        results = []
        current_input = initial_prompt

        for name in agent_names:
            result = await self.run(name, current_input, ollama_client)
            results.append(result)

            if result["status"] == "success":
                current_input = result["response"]
            else:
                break

        return {
            "status": "completed",
            "chain": agent_names,
            "results": results,
            "final_output": current_input,
        }

    def list_agents(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": a.name,
                "model": a.model,
                "system_prompt": a.system_prompt[:100] + "..." if len(a.system_prompt) > 100 else a.system_prompt,
            }
            for a in self._agents.values()
        ]

    def select_best_agent(self, task: str) -> str:
        task_lower = task.lower()
        if any(w in task_lower for w in ["কোড", "code", "প্রোগ্রাম", "ফাংশন"]):
            return "coder"
        if any(w in task_lower for w in ["লেখো", "write", "আর্টিকেল", "ব্লগ"]):
            return "writer"
        if any(w in task_lower for w in ["বিশ্লেষণ", "analyze", "ডেটা", "data"]):
            return "analyst"
        if any(w in task_lower for w in ["অনুবাদ", "translate", "ট্রান্সলেট"]):
            return "translator"
        return "coder"

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        return None
