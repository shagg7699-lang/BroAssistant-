"""
ব্রো (Bro) — সর্বক্ষণ ওয়েক-ওয়ার্ড ডিটেক্টর
মাইক্রোফোন মনিটর করে "ব্রো" শব্দ শনাক্ত হলে bro_assistant চালু করে।
"""

import asyncio
import signal
import sys
import time
from typing import Any, Callable, Dict, Optional

from utils.logger import get_logger, setup_logging
from utils.startup import bootstrap

log = get_logger("listener")

try:
    from local.stt_engine import STTEngine

    _HAS_STT = True
except ImportError:
    _HAS_STT = False


class BroListener:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        wake_cfg = cfg.get("wake_word", {})
        self.wake_word = wake_cfg.get("keyword", "ব্রো")
        self.wake_word_en = wake_cfg.get("keyword_en", "bro")
        self.activation_phrase = wake_cfg.get("activation_phrase", "ব্রো স্টার্ট")
        self.deactivation_phrase = wake_cfg.get("deactivation_phrase", "ব্রো অফ")
        self.sensitivity = wake_cfg.get("sensitivity", 0.7)

        stt_cfg = cfg.get("stt", {})
        stt_cfg["model_size"] = "tiny"
        self._stt = STTEngine(stt_cfg) if _HAS_STT else None

        self._on_activate: Optional[Callable[[str], None]] = None
        self._on_deactivate: Optional[Callable[[], None]] = None
        self._running = False
        self._active = False

    def on_activate(self, callback: Callable[[str], None]) -> None:
        self._on_activate = callback

    def on_deactivate(self, callback: Callable[[], None]) -> None:
        self._on_deactivate = callback

    def start(self) -> None:
        if not self._stt:
            log.error("STT ইঞ্জিন অনুপলব্ধ — listener শুরু করা যাচ্ছে না")
            return

        self._running = True
        log.info("ওয়েক ওয়ার্ড লিসেনার শুরু: '%s'", self.wake_word)

        try:
            self._stt.listen_for_wake_word(
                wake_word=self.wake_word,
                callback=self._on_wake_word,
                check_interval=2.0,
            )
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        self._running = False
        log.info("লিসেনার বন্ধ")

    def _on_wake_word(self, text: str) -> None:
        text_lower = text.lower()

        if self.deactivation_phrase.lower() in text_lower:
            log.info("ডিঅ্যাক্টিভেশন শনাক্ত: '%s'", text)
            self._active = False
            if self._on_deactivate:
                self._on_deactivate()
            return

        if (
            self.wake_word.lower() in text_lower
            or self.wake_word_en.lower() in text_lower
        ):
            log.info("ওয়েক ওয়ার্ড শনাক্ত: '%s'", text)
            self._active = True
            if self._on_activate:
                self._on_activate(text)

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def is_running(self) -> bool:
        return self._running


def main() -> None:
    cfg = bootstrap()
    listener = BroListener(cfg)

    def on_activate(text: str) -> None:
        log.info("ব্রো অ্যাক্টিভেট হয়েছে! কমান্ড: %s", text)
        # bro_assistant ইম্পোর্ট ও চালু
        try:
            from bro_assistant import BroAssistant

            assistant = BroAssistant(cfg)
            asyncio.run(assistant.handle_command(text))
        except Exception as exc:
            log.error("অ্যাসিস্ট্যান্ট ত্রুটি: %s", exc)

    def on_deactivate() -> None:
        log.info("ব্রো ডিঅ্যাক্টিভেট হয়েছে")

    listener.on_activate(on_activate)
    listener.on_deactivate(on_deactivate)

    signal.signal(signal.SIGINT, lambda s, f: listener.stop())
    listener.start()


if __name__ == "__main__":
    main()
