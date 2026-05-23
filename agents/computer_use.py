"""
ব্রো (Bro) — কম্পিউটার ইউজ এজেন্ট
pyautogui দিয়ে মাউস-কিবোর্ড-স্ক্রিন নিয়ন্ত্রণ।
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("computer_use")

try:
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.3
    _HAS_GUI = True
except ImportError:
    _HAS_GUI = False
    log.warning("pyautogui ইনস্টল নেই")

try:
    import pyperclip

    _HAS_CLIP = True
except ImportError:
    _HAS_CLIP = False


class ComputerUseAgent:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.safe_mode = cfg.get("safe_mode", True)
        self.screenshot_interval = cfg.get("screenshot_interval", 0.5)

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [{"description": command, "action": "execute", "risky": True}]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error", "error": "pyautogui অনুপলব্ধ"}
        return {"status": "ready", "message": "কম্পিউটার ইউজ প্রস্তুত"}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        action = step.get("action", "")
        params = step.get("params", {})

        actions = {
            "click": self.click,
            "double_click": self.double_click,
            "right_click": self.right_click,
            "type": self.type_text,
            "hotkey": self.hotkey,
            "move": self.move_to,
            "scroll": self.scroll,
            "screenshot": self.screenshot,
            "locate": self.locate_on_screen,
        }

        func = actions.get(action)
        if func:
            return await func(**params)
        return {"status": "unknown_action", "action": action}

    async def click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error"}
        await asyncio.to_thread(pyautogui.click, x, y, button=button)
        return {"status": "clicked", "x": x, "y": y, "button": button}

    async def double_click(self, x: int, y: int) -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error"}
        await asyncio.to_thread(pyautogui.doubleClick, x, y)
        return {"status": "double_clicked", "x": x, "y": y}

    async def right_click(self, x: int, y: int) -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error"}
        await asyncio.to_thread(pyautogui.rightClick, x, y)
        return {"status": "right_clicked", "x": x, "y": y}

    async def type_text(self, text: str, interval: float = 0.02) -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error"}
        if _HAS_CLIP:
            pyperclip.copy(text)
            await asyncio.to_thread(pyautogui.hotkey, "ctrl", "v")
        else:
            await asyncio.to_thread(pyautogui.typewrite, text, interval=interval)
        return {"status": "typed", "length": len(text)}

    async def hotkey(self, keys: List[str]) -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error"}
        await asyncio.to_thread(pyautogui.hotkey, *keys)
        return {"status": "hotkey", "keys": keys}

    async def move_to(self, x: int, y: int, duration: float = 0.3) -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error"}
        await asyncio.to_thread(pyautogui.moveTo, x, y, duration=duration)
        return {"status": "moved", "x": x, "y": y}

    async def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error"}
        await asyncio.to_thread(pyautogui.scroll, clicks, x=x, y=y)
        return {"status": "scrolled", "clicks": clicks}

    async def screenshot(self, region: Optional[tuple] = None) -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error"}
        img = await asyncio.to_thread(pyautogui.screenshot, region=region)
        return {"status": "captured", "size": img.size}

    async def locate_on_screen(self, image_path: str, confidence: float = 0.8) -> Dict[str, Any]:
        if not _HAS_GUI:
            return {"status": "error"}
        try:
            location = await asyncio.to_thread(
                pyautogui.locateOnScreen, image_path, confidence=confidence
            )
            if location:
                center = pyautogui.center(location)
                return {"status": "found", "x": center.x, "y": center.y, "region": location}
            return {"status": "not_found"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def get_screen_size(self) -> Dict[str, int]:
        if not _HAS_GUI:
            return {"width": 0, "height": 0}
        size = pyautogui.size()
        return {"width": size.width, "height": size.height}

    async def get_mouse_position(self) -> Dict[str, int]:
        if not _HAS_GUI:
            return {"x": 0, "y": 0}
        pos = pyautogui.position()
        return {"x": pos.x, "y": pos.y}
