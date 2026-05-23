"""
ব্রো (Bro) — চ্যাট UI (ভবিষ্যত)
সহজ টার্মিনাল-ভিত্তিক চ্যাট ইন্টারফেস — ভবিষ্যতে গ্রাফিক্যাল UI হবে।
"""

import asyncio
import sys
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("bro_ui")


class ChatMessage:
    def __init__(self, role: str, content: str, timestamp: str = "") -> None:
        self.role = role
        self.content = content
        self.timestamp = timestamp


class BroUI:
    def __init__(self) -> None:
        self._history: List[ChatMessage] = []
        self._on_send: Optional[Any] = None

    def set_send_handler(self, handler: Any) -> None:
        self._on_send = handler

    def display_message(self, role: str, content: str) -> None:
        msg = ChatMessage(role, content)
        self._history.append(msg)

        if role == "user":
            prefix = "\033[36mতুমি\033[0m"
        elif role == "assistant":
            prefix = "\033[32mব্রো\033[0m"
        else:
            prefix = "\033[33mসিস্টেম\033[0m"

        print(f"\n{prefix}: {content}")

    def display_status(self, status: str) -> None:
        print(f"\n\033[90m[{status}]\033[0m")

    def display_suggestions(self, suggestions: List[Dict[str, Any]]) -> None:
        if not suggestions:
            return
        print("\n\033[90m💡 সাজেশন:\033[0m")
        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. {s.get('action', '')} ({s.get('confidence', 0):.0%})")

    async def run(self) -> None:
        self._print_header()

        while True:
            try:
                user_input = input("\n\033[36mতুমি: \033[0m").strip()
                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit", "ব্রো অফ"):
                    self.display_status("ব্রো বন্ধ হচ্ছে...")
                    break

                if self._on_send:
                    if asyncio.iscoroutinefunction(self._on_send):
                        response = await self._on_send(user_input)
                    else:
                        response = self._on_send(user_input)

                    if response:
                        self.display_message("assistant", str(response))
                else:
                    self.display_message("system", "কোনো হ্যান্ডলার সংযুক্ত নেই")

            except (KeyboardInterrupt, EOFError):
                print()
                self.display_status("ব্রো বন্ধ")
                break

    def _print_header(self) -> None:
        header = """
╔══════════════════════════════════════════════╗
║           🧠 ব্রো (Bro) v3.0                 ║
║     সুপারচার্জড AI অ্যাসিস্ট্যান্ট             ║
║                                              ║
║  'exit' বা 'ব্রো অফ' লিখে বের হও             ║
╚══════════════════════════════════════════════╝"""
        print(header)

    def get_history(self) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self._history]

    def clear_history(self) -> None:
        self._history.clear()
        print("\033[2J\033[H")
        self._print_header()
