"""
ব্রো (Bro) — স্টার্টআপ ইউটিলিটি
কনফিগ লোড, এনভায়রনমেন্ট ভ্যালিডেশন, ডিপেন্ডেন্সি চেক।
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

from utils.logger import get_logger, setup_logging

log = get_logger("startup")

_BASE_DIR = Path(__file__).resolve().parent.parent
_CONFIG_FILE = _BASE_DIR / "config" / "settings.yaml"
_ENV_FILE = _BASE_DIR / ".env"


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    path = Path(config_path) if config_path else _CONFIG_FILE
    if not path.exists():
        log.warning("কনফিগ ফাইল পাওয়া যায়নি: %s — ডিফল্ট ব্যবহার হবে", path)
        return {}
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    log.info("কনফিগ লোড হয়েছে: %s", path)
    return cfg


def load_env() -> None:
    if _ENV_FILE.exists():
        load_dotenv(_ENV_FILE)
        log.info(".env লোড হয়েছে")
    else:
        log.warning(".env ফাইল নেই — এনভায়রনমেন্ট ভ্যারিয়েবল ব্যবহার হবে")


def check_dependencies() -> Dict[str, bool]:
    deps: Dict[str, bool] = {}
    checks = {
        "faster_whisper": "faster_whisper",
        "pystray": "pystray",
        "pyautogui": "pyautogui",
        "mss": "mss",
        "PIL": "PIL",
        "sounddevice": "sounddevice",
        "piper": "piper",
        "ffmpeg_python": "ffmpeg",
        "httpx": "httpx",
        "aiosqlite": "aiosqlite",
        "telegram": "telegram",
        "acoustid": "acoustid",
    }
    for name, module in checks.items():
        try:
            __import__(module)
            deps[name] = True
        except ImportError:
            deps[name] = False
            log.debug("ঐচ্ছিক ডিপেন্ডেন্সি অনুপলব্ধ: %s", name)
    return deps


def init_data_dirs() -> None:
    dirs = [
        _BASE_DIR / "data",
        _BASE_DIR / "data" / "logs",
        _BASE_DIR / "data" / "plugins",
        _BASE_DIR / "data" / "video_output",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def bootstrap() -> Dict[str, Any]:
    load_env()
    cfg = load_config()

    log_cfg = cfg.get("logging", {})
    setup_logging(
        level=log_cfg.get("level", "INFO"),
        log_file=log_cfg.get("file"),
        max_size_mb=log_cfg.get("max_size_mb", 50),
        backup_count=log_cfg.get("backup_count", 5),
        console=log_cfg.get("console", True),
    )

    init_data_dirs()

    deps = check_dependencies()
    missing_critical = [k for k in ("httpx",) if not deps.get(k)]
    if missing_critical:
        log.error("গুরুত্বপূর্ণ ডিপেন্ডেন্সি অনুপলব্ধ: %s", missing_critical)
        sys.exit(1)

    log.info("ব্রো v%s বুটস্ট্র্যাপ সম্পন্ন", cfg.get("assistant", {}).get("version", "3.0"))
    return cfg
