"""
ব্রো (Bro) — সিস্টেম ট্রে অ্যাপ
pystray ব্যবহার করে সিস্টেম ট্রেতে আইকন, মেনু ও নিয়ন্ত্রণ।
"""

import asyncio
import sys
import threading
from typing import Any, Dict, Optional

from utils.logger import get_logger
from utils.startup import bootstrap

log = get_logger("tray")

try:
    import pystray
    from PIL import Image, ImageDraw

    _HAS_TRAY = True
except ImportError:
    _HAS_TRAY = False
    log.warning("pystray/Pillow ইনস্টল নেই — ট্রে অনুপলব্ধ")


class BroTray:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.cfg = config or {}
        self._icon: Optional[Any] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._assistant_thread: Optional[threading.Thread] = None
        self._running = False

    def _create_icon_image(self) -> "Image.Image":
        """ব্রো আইকন তৈরি (সবুজ বৃত্তের ভিতর B)"""
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill=(46, 204, 113), outline=(39, 174, 96), width=2)
        draw.text((20, 14), "B", fill="white")
        return img

    def _on_activate(self, icon: Any, item: Any) -> None:
        log.info("ট্রে মেনু: অ্যাক্টিভেট")
        self._start_assistant()

    def _on_status(self, icon: Any, item: Any) -> None:
        log.info("ট্রে মেনু: স্ট্যাটাস")

    def _on_interactive(self, icon: Any, item: Any) -> None:
        log.info("ট্রে মেনু: ইন্টারেক্টিভ মোড")
        thread = threading.Thread(target=self._run_interactive, daemon=True)
        thread.start()

    def _on_exit(self, icon: Any, item: Any) -> None:
        log.info("ট্রে মেনু: বন্ধ")
        self._running = False
        if self._icon:
            self._icon.stop()

    def _start_listener(self) -> None:
        try:
            from bro_listener import BroListener

            listener = BroListener(self.cfg)

            def on_activate(text: str) -> None:
                self._start_assistant()

            listener.on_activate(on_activate)
            listener.start()
        except Exception as exc:
            log.error("লিসেনার ত্রুটি: %s", exc)

    def _start_assistant(self) -> None:
        if self._assistant_thread and self._assistant_thread.is_alive():
            return

        def run() -> None:
            try:
                from bro_assistant import BroAssistant

                assistant = BroAssistant(self.cfg)
                asyncio.run(assistant.start())
            except Exception as exc:
                log.error("অ্যাসিস্ট্যান্ট ত্রুটি: %s", exc)

        self._assistant_thread = threading.Thread(target=run, daemon=True)
        self._assistant_thread.start()

    def _run_interactive(self) -> None:
        try:
            from bro_assistant import interactive_mode

            asyncio.run(interactive_mode())
        except Exception as exc:
            log.error("ইন্টারেক্টিভ মোড ত্রুটি: %s", exc)

    def start(self) -> None:
        if not _HAS_TRAY:
            log.warning("pystray অনুপলব্ধ — কনসোল মোডে চালু হচ্ছে")
            self._run_interactive()
            return

        self._running = True

        # লিসেনার ব্যাকগ্রাউন্ডে চালু
        self._listener_thread = threading.Thread(target=self._start_listener, daemon=True)
        self._listener_thread.start()

        # ট্রে আইকন
        menu = pystray.Menu(
            pystray.MenuItem("🟢 ব্রো অ্যাক্টিভেট", self._on_activate),
            pystray.MenuItem("💬 ইন্টারেক্টিভ মোড", self._on_interactive),
            pystray.MenuItem("📊 স্ট্যাটাস", self._on_status),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ বন্ধ করো", self._on_exit),
        )

        self._icon = pystray.Icon(
            "BroAssistant",
            self._create_icon_image(),
            "ব্রো (Bro) v3.0",
            menu,
        )

        log.info("সিস্টেম ট্রে চালু")
        self._icon.run()


def main() -> None:
    cfg = bootstrap()
    tray = BroTray(cfg)
    tray.start()


if __name__ == "__main__":
    main()
