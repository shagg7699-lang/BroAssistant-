"""
ব্রো (Bro) — কেন্দ্রীয় লগিং মডিউল
রোটেটিং ফাইল + কনসোল লগিং, কালার সাপোর্ট সহ।
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

try:
    import colorlog

    _HAS_COLOR = True
except ImportError:
    _HAS_COLOR = False


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
_COLOR_FORMAT = "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_root_configured = False


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_size_mb: int = 50,
    backup_count: int = 5,
    console: bool = True,
) -> None:
    global _root_configured
    if _root_configured:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    if console:
        if _HAS_COLOR:
            handler = colorlog.StreamHandler()
            handler.setFormatter(
                colorlog.ColoredFormatter(
                    _COLOR_FORMAT,
                    datefmt=_DATE_FORMAT,
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "bold_red",
                    },
                )
            )
        else:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            str(log_path),
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(fh)

    _root_configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
