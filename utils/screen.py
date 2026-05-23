"""
ব্রো (Bro) — স্ক্রিন ক্যাপচার ইউটিলিটি
mss ব্যবহার করে দ্রুত স্ক্রিনশট, ঐচ্ছিক রিসাইজ ও base64 এনকোডিং।
"""

import base64
import io
from typing import Optional, Tuple

from utils.logger import get_logger

log = get_logger("screen")

try:
    import mss
    import mss.tools
    from PIL import Image

    _HAS_MSS = True
except ImportError:
    _HAS_MSS = False
    log.warning("mss/Pillow ইনস্টল নেই — স্ক্রিন ক্যাপচার অনুপলব্ধ")


def capture_screen(
    monitor: int = 0,
    region: Optional[Tuple[int, int, int, int]] = None,
    resize: Optional[Tuple[int, int]] = None,
) -> Optional[bytes]:
    if not _HAS_MSS:
        return None
    try:
        with mss.mss() as sct:
            if region:
                mon = {"left": region[0], "top": region[1], "width": region[2], "height": region[3]}
            else:
                mon = sct.monitors[monitor] if monitor < len(sct.monitors) else sct.monitors[0]
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            if resize:
                img = img.resize(resize, Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
    except Exception as exc:
        log.error("স্ক্রিনশট ব্যর্থ: %s", exc)
        return None


def screen_to_base64(
    monitor: int = 0,
    region: Optional[Tuple[int, int, int, int]] = None,
    resize: Optional[Tuple[int, int]] = None,
) -> Optional[str]:
    raw = capture_screen(monitor, region, resize)
    if raw:
        return base64.b64encode(raw).decode("ascii")
    return None


def save_screenshot(
    path: str,
    monitor: int = 0,
    region: Optional[Tuple[int, int, int, int]] = None,
) -> bool:
    raw = capture_screen(monitor, region)
    if raw:
        with open(path, "wb") as f:
            f.write(raw)
        log.info("স্ক্রিনশট সেভ: %s", path)
        return True
    return False
