"""
ব্রো (Bro) — কনটেক্সট কম্প্যাক্টর
দীর্ঘ কনভার্সেশন হিস্ট্রি সংক্ষিপ্ত করে টোকেন সীমায় রাখে।
"""

from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("context_compactor")


class ContextCompactor:
    def __init__(
        self,
        max_tokens: int = 4096,
        strategy: str = "summarize",
    ) -> None:
        self.max_tokens = max_tokens
        self.strategy = strategy

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 3

    def estimate_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        return sum(self.estimate_tokens(m.get("content", "")) + 4 for m in messages)

    def compact(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        limit = max_tokens or self.max_tokens
        total = self.estimate_messages_tokens(messages)

        if total <= limit:
            return messages

        if self.strategy == "truncate":
            return self._truncate(messages, limit)
        elif self.strategy == "summarize":
            return self._summarize_compact(messages, limit)
        else:
            return self._sliding_window(messages, limit)

    def _truncate(self, messages: List[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
        system_msgs = [m for m in messages if m["role"] == "system"]
        other_msgs = [m for m in messages if m["role"] != "system"]

        result = list(system_msgs)
        used = self.estimate_messages_tokens(result)

        for msg in reversed(other_msgs):
            msg_tokens = self.estimate_tokens(msg.get("content", "")) + 4
            if used + msg_tokens <= limit:
                result.insert(len(system_msgs), msg)
                used += msg_tokens
            else:
                break

        log.info("কনটেক্সট ট্রাঙ্কেট: %d → %d মেসেজ", len(messages), len(result))
        return result

    def _sliding_window(self, messages: List[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
        system_msgs = [m for m in messages if m["role"] == "system"]
        other_msgs = [m for m in messages if m["role"] != "system"]

        result = list(system_msgs)
        used = self.estimate_messages_tokens(result)

        for msg in reversed(other_msgs):
            msg_tokens = self.estimate_tokens(msg.get("content", "")) + 4
            if used + msg_tokens <= limit:
                result.insert(len(system_msgs), msg)
                used += msg_tokens

        return result

    def _summarize_compact(self, messages: List[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
        system_msgs = [m for m in messages if m["role"] == "system"]
        other_msgs = [m for m in messages if m["role"] != "system"]

        if len(other_msgs) <= 4:
            return self._truncate(messages, limit)

        mid = len(other_msgs) // 2
        old_msgs = other_msgs[:mid]
        recent_msgs = other_msgs[mid:]

        summary_parts = []
        for msg in old_msgs:
            role = msg["role"]
            content = msg.get("content", "")
            if len(content) > 200:
                content = content[:200] + "..."
            summary_parts.append(f"[{role}]: {content}")

        summary_text = "পূর্ববর্তী কথোপকথনের সারাংশ:\n" + "\n".join(summary_parts)
        summary_msg = {"role": "system", "content": summary_text}

        result = system_msgs + [summary_msg] + recent_msgs

        if self.estimate_messages_tokens(result) > limit:
            return self._truncate(result, limit)

        log.info("কনটেক্সট সারাংশ: %d → %d মেসেজ", len(messages), len(result))
        return result

    def add_message(
        self,
        messages: List[Dict[str, str]],
        new_message: Dict[str, str],
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        messages.append(new_message)
        return self.compact(messages, max_tokens)
