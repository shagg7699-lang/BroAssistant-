"""
ব্রো (Bro) — মূল অ্যাসিস্ট্যান্ট
কমান্ড রাউটিং, ক্লাউড/লোকাল LLM, ধাপে ধাপে অনুমতি, সম্পূর্ণ অর্কেস্ট্রেশন।
"""

import asyncio
import hashlib
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger
from utils.startup import bootstrap
from utils.memory import BroMemory
from utils.screen import screen_to_base64

from cloud.token_manager import TokenManager
from cloud.google_client import GoogleClient
from cloud.siliconflow_client import SiliconFlowClient
from cloud.github_models_client import GitHubModelsClient
from cloud.groq_client import GroqClient
from cloud.huggingface_client import HuggingFaceClient

from local.ollama_client import OllamaClient
from local.stt_engine import STTEngine
from local.tts_engine import TTSEngine

from optimization.cache import ResponseCache
from optimization.context_compactor import ContextCompactor
from optimization.request_scheduler import RequestScheduler

from agents.agent_manager import AgentManager
from agents.computer_use import ComputerUseAgent
from agents.shotcut_agent import ShotcutAgent
from agents.vscode_cua_agent import VSCodeCUAAgent
from agents.vscode_agents_hub import VSCodeAgentsHub
from agents.opencode_autopilot_daemon import OpenCodeAutopilotDaemon
from agents.video_agent import VideoAgent
from agents.autovideo_generator import AutoVideoGenerator
from agents.chromaprint_listener import ChromaprintListener
from agents.alex_core_plugin import AlexCorePlugin
from agents.keysersoze_framework import KeysersozeFramework
from agents.joshu_predictor import JoshuPredictor
from agents.human_bot_remote import HumanBotRemote
from agents.nova_telegram_bot import NovaTelegramBot
from agents.bantz_behavior_learner import BantzBehaviorLearner
from agents.miniomni2_brain import MiniOmni2Brain
from agents.just_agents_runner import JustAgentsRunner

log = get_logger("assistant")


class BroAssistant:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.cfg = config or {}
        self.name = self.cfg.get("assistant", {}).get("name", "ব্রো")
        self.greeting = self.cfg.get("assistant", {}).get("greeting", "হাই, আমি ব্রো। কী করতে বলবেন?")

        # কনভার্সেশন হিস্ট্রি
        self._messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "তুমি ব্রো, একটি সুপারচার্জড AI অ্যাসিস্ট্যান্ট। "
                    "তুমি বাংলা ও ইংরেজি দুটোতেই কথা বলতে পারো। "
                    "তুমি কম্পিউটার নিয়ন্ত্রণ, কোডিং, ভিডিও এডিটিং, "
                    "অডিও প্রসেসিং সহ অনেক কাজ করতে পারো। "
                    "প্রতিটি গুরুত্বপূর্ণ কাজে ব্যবহারকারীর অনুমতি নাও।"
                ),
            }
        ]

        # কম্পোনেন্ট ইনিশিয়ালাইজ
        self._init_components()

    def _init_components(self) -> None:
        # মেমোরি
        mem_cfg = self.cfg.get("memory", {})
        self.memory = BroMemory(mem_cfg.get("file", "data/bro_memory.json"), mem_cfg.get("max_entries", 5000))

        # STT / TTS
        self.stt = STTEngine(self.cfg.get("stt", {}))
        self.tts = TTSEngine(self.cfg.get("tts", {}))

        # টোকেন ম্যানেজার
        self.token_manager = TokenManager()

        # ক্লাউড ক্লায়েন্ট
        cloud_cfg = self.cfg.get("cloud", {}).get("providers", {})
        self.cloud_clients: Dict[str, Any] = {}
        self.cloud_clients["google"] = GoogleClient(self.token_manager, cloud_cfg.get("google"))
        self.cloud_clients["siliconflow"] = SiliconFlowClient(self.token_manager, cloud_cfg.get("siliconflow"))
        self.cloud_clients["github_models"] = GitHubModelsClient(self.token_manager, cloud_cfg.get("github_models"))
        self.cloud_clients["groq"] = GroqClient(self.token_manager, cloud_cfg.get("groq"))
        self.cloud_clients["huggingface"] = HuggingFaceClient(self.token_manager, cloud_cfg.get("huggingface"))

        # লোকাল
        self.ollama = OllamaClient(self.cfg.get("local", {}))
        self.cloud_clients["local"] = self.ollama

        # অপটিমাইজেশন
        cache_cfg = self.cfg.get("optimization", {}).get("cache", {})
        self.cache = ResponseCache(
            cache_cfg.get("db_path", "data/cache.db"),
            cache_cfg.get("ttl_seconds", 3600),
            cache_cfg.get("max_entries", 10000),
        )

        ctx_cfg = self.cfg.get("optimization", {}).get("context", {})
        self.compactor = ContextCompactor(ctx_cfg.get("max_tokens", 4096), ctx_cfg.get("compaction_strategy", "summarize"))

        sched_cfg = self.cfg.get("optimization", {}).get("scheduler", {})
        fallback_order = self.cfg.get("cloud", {}).get("fallback_order", [])
        self.scheduler = RequestScheduler(fallback_order, sched_cfg.get("strategy", "fastest_first"))

        # এজেন্ট ম্যানেজার
        self.agent_manager = AgentManager(
            self.cfg,
            tts_speak=self.tts.speak,
            stt_listen=lambda: self.stt.record_and_transcribe(5.0),
        )

        # এজেন্ট রেজিস্ট্রেশন
        agents_cfg = self.cfg.get("agents", {})
        agent_registry = {
            "computer_use": ComputerUseAgent(agents_cfg.get("computer_use", {})),
            "shotcut": ShotcutAgent(agents_cfg.get("shotcut", {})),
            "vscode_cua": VSCodeCUAAgent(agents_cfg.get("vscode_cua", {})),
            "vscode_agents_hub": VSCodeAgentsHub(agents_cfg.get("vscode_agents_hub", {})),
            "opencode_autopilot": OpenCodeAutopilotDaemon(agents_cfg.get("opencode_autopilot", {})),
            "video_agent": VideoAgent(agents_cfg.get("video_agent", {})),
            "autovideo": AutoVideoGenerator(agents_cfg.get("autovideo", {})),
            "chromaprint": ChromaprintListener(agents_cfg.get("chromaprint", {})),
            "alex_core": AlexCorePlugin(agents_cfg.get("alex_core", {})),
            "keysersoze": KeysersozeFramework(agents_cfg.get("keysersoze", {})),
            "joshu": JoshuPredictor(agents_cfg.get("joshu", {})),
            "human_bot": HumanBotRemote(agents_cfg.get("human_bot", {})),
            "telegram": NovaTelegramBot(agents_cfg.get("telegram", {})),
            "bantz": BantzBehaviorLearner(agents_cfg.get("bantz", {})),
            "miniomni2": MiniOmni2Brain(agents_cfg.get("miniomni2", {})),
            "just_agents": JustAgentsRunner(agents_cfg.get("just_agents", {})),
        }

        for name, agent in agent_registry.items():
            if agents_cfg.get(name, {}).get("enabled", True):
                self.agent_manager.register_agent(name, agent)

        # joshu predictor রেফারেন্স
        self.predictor: JoshuPredictor = agent_registry["joshu"]
        self.behavior_learner: BantzBehaviorLearner = agent_registry["bantz"]

        log.info("ব্রো অ্যাসিস্ট্যান্ট ইনিশিয়ালাইজ সম্পন্ন")

    async def start(self) -> None:
        """অ্যাসিস্ট্যান্ট চালু — গ্রিটিং বাজায়"""
        self.tts.speak(self.greeting)
        log.info("ব্রো চালু: %s", self.greeting)

    async def handle_command(self, text: str) -> str:
        """একটি কমান্ড প্রসেস করে রেসপন্স ফেরত দেয়"""
        log.info("কমান্ড: %s", text[:200])

        # মেমোরি কমান্ড
        if self._is_memory_command(text):
            return self._handle_memory(text)

        # এজেন্ট ক্লাসিফিকেশন
        agent_name, confidence = self.agent_manager.classify_command(text)

        if agent_name != "chat" and confidence > 0.3:
            result = await self.agent_manager.execute_task(text)
            self.predictor.record_action(agent_name, text)
            response = self._format_agent_result(result)
            self.tts.speak(response[:200])
            return response

        # LLM চ্যাট
        return await self._llm_chat(text)

    def _context_hash(self) -> str:
        """সাম্প্রতিক কনভার্সেশন কনটেক্সটের হ্যাশ"""
        recent = self._messages[-5:] if len(self._messages) > 5 else self._messages
        raw = "|".join(f"{m['role']}:{m['content'][:100]}" for m in recent)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    async def _llm_chat(self, text: str) -> str:
        """ক্লাউড/লোকাল LLM দিয়ে চ্যাট"""
        # ক্যাশ চেক
        ctx_hash = self._context_hash()
        cached = await self.cache.get(text, context_hash=ctx_hash)
        if cached:
            log.info("ক্যাশ হিট")
            self.tts.speak(cached[:200])
            return cached

        # কনটেক্সট আপডেট
        self._messages = self.compactor.add_message(
            self._messages,
            {"role": "user", "content": text},
        )

        # ক্লাউড ফেইলওভার
        response = ""
        try:
            response = await self.scheduler.execute_with_fallback(
                self.cloud_clients,
                "chat",
                self._messages,
            )
        except Exception as exc:
            log.error("সকল প্রোভাইডার ব্যর্থ: %s", exc)
            response = "দুঃখিত, এই মুহূর্তে কোনো AI সার্ভিস কাজ করছে না।"

        if response:
            self._messages.append({"role": "assistant", "content": response})
            await self.cache.put(text, response, context_hash=ctx_hash)
            self.predictor.record_action("chat", text)

        self.tts.speak(response[:200] if response else "দুঃখিত, উত্তর পাওয়া যায়নি।")
        return response

    async def handle_vision(self, text: str) -> str:
        """স্ক্রিন/ছবি বিশ্লেষণ"""
        image_b64 = screen_to_base64(resize=(1280, 720))
        if not image_b64:
            return "স্ক্রিনশট নেওয়া যায়নি।"

        prompt = text or "এই স্ক্রিনে কী দেখা যাচ্ছে বর্ণনা করো।"

        try:
            response = await self.scheduler.execute_with_fallback(
                self.cloud_clients,
                "vision",
                prompt,
                image_b64,
            )
            self.tts.speak(response[:200] if response else "বিশ্লেষণ করা যায়নি।")
            return response
        except Exception as exc:
            log.error("ভিশন ব্যর্থ: %s", exc)
            return "দৃশ্য বিশ্লেষণে সমস্যা হয়েছে।"

    def _is_memory_command(self, text: str) -> bool:
        keywords = ["মনে রাখো", "মনে আছে", "ভুলে যাও", "remember", "recall", "forget"]
        return any(k in text.lower() for k in keywords)

    def _handle_memory(self, text: str) -> str:
        text_lower = text.lower()

        if "মনে রাখো" in text_lower or "remember" in text_lower:
            content = text.replace("মনে রাখো", "").replace("remember", "").strip()
            if content:
                key = content[:50]
                self.memory.remember(key, content, "user_fact")
                response = f"মনে রাখলাম: {content[:100]}"
                self.tts.speak(response)
                return response

        if "মনে আছে" in text_lower or "recall" in text_lower:
            query = text.replace("মনে আছে", "").replace("recall", "").strip()
            results = self.memory.search(query)
            if results:
                entries = "\n".join(f"• {r.value}" for r in results[:5])
                response = f"হ্যাঁ, মনে আছে:\n{entries}"
            else:
                response = "দুঃখিত, এটা মনে নেই।"
            self.tts.speak(response[:200])
            return response

        if "ভুলে যাও" in text_lower or "forget" in text_lower:
            query = text.replace("ভুলে যাও", "").replace("forget", "").strip()
            if self.memory.forget(query):
                response = f"ভুলে গেছি: {query}"
            else:
                response = "এটা আমার মেমোরিতে নেই।"
            self.tts.speak(response)
            return response

        return "মেমোরি কমান্ড বোঝা যায়নি।"

    def _format_agent_result(self, result: Dict[str, Any]) -> str:
        status = result.get("status", "unknown")
        agent = result.get("agent", "")

        if status == "completed":
            results = result.get("results", [])
            parts = []
            for r in results:
                step = r.get("step", "")
                s = r.get("status", "")
                if s == "success":
                    parts.append(f"✓ {step}")
                elif s == "skipped":
                    parts.append(f"⊘ {step} (বাদ)")
                else:
                    parts.append(f"✗ {step}")
            return f"[{agent}] কাজ সম্পন্ন:\n" + "\n".join(parts)

        if status == "unavailable":
            return f"এজেন্ট '{agent}' এখন উপলব্ধ নেই।"

        if status == "error":
            return f"ত্রুটি: {result.get('error', 'অজানা')}"

        return f"[{agent}] স্ট্যাটাস: {status}"

    async def get_suggestions(self) -> List[Dict[str, Any]]:
        """পরবর্তী কাজের সাজেশন"""
        return self.predictor.get_suggestions()

    async def shutdown(self) -> None:
        """সব কম্পোনেন্ট বন্ধ"""
        self.tts.speak("ব্রো অফ হচ্ছে। বাই!")
        await self.cache.close()
        for client in self.cloud_clients.values():
            if hasattr(client, "close"):
                await client.close()
        self.memory.save()
        log.info("ব্রো শাটডাউন সম্পন্ন")


async def interactive_mode() -> None:
    """ইন্টারেক্টিভ টেক্সট মোড"""
    cfg = bootstrap()
    assistant = BroAssistant(cfg)
    await assistant.start()

    print("\n" + "=" * 50)
    print("  ব্রো (Bro) v3.0 — ইন্টারেক্টিভ মোড")
    print("  'exit' বা 'ব্রো অফ' লিখে বের হও")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("তুমি: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "ব্রো অফ"):
                await assistant.shutdown()
                break

            response = await assistant.handle_command(user_input)
            print(f"\nব্রো: {response}\n")

        except (KeyboardInterrupt, EOFError):
            await assistant.shutdown()
            break


if __name__ == "__main__":
    asyncio.run(interactive_mode())
