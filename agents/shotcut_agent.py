"""
ব্রো (Bro) — Shotcut ভিডিও এডিটিং এজেন্ট
Shotcut (melt) ও FFmpeg দিয়ে ভিডিও ট্রিম, কাট, কনভার্ট, রেন্ডার।
"""

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("shotcut_agent")


class ShotcutAgent:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.shotcut_path = os.getenv("SHOTCUT_PATH", cfg.get("shotcut_path", "shotcut"))
        self.melt_path = os.getenv("MELT_PATH", cfg.get("melt_path", "melt"))
        self.output_dir = cfg.get("output_dir", "data/video_output")
        self._ffmpeg = shutil.which("ffmpeg")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        cmd_lower = command.lower()
        steps = []

        if any(w in cmd_lower for w in ["ট্রিম", "trim", "কাট", "cut"]):
            steps.append({
                "description": "ভিডিও ট্রিম/কাট",
                "action": "trim",
                "risky": False,
            })
        elif any(w in cmd_lower for w in ["কনভার্ট", "convert", "ফরম্যাট"]):
            steps.append({
                "description": "ভিডিও ফরম্যাট কনভার্ট",
                "action": "convert",
                "risky": False,
            })
        elif any(w in cmd_lower for w in ["রেন্ডার", "render", "এক্সপোর্ট"]):
            steps.append({
                "description": "ভিডিও রেন্ডার/এক্সপোর্ট",
                "action": "render",
                "risky": False,
            })
        else:
            steps.append({
                "description": command,
                "action": "execute",
                "risky": False,
            })

        return steps

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "ffmpeg": self._ffmpeg is not None}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        action = step.get("action", "")
        params = step.get("params", {})

        if action == "trim":
            return await self.trim(**params)
        elif action == "convert":
            return await self.convert(**params)
        elif action == "render":
            return await self.render_mlt(**params)
        return {"status": "unknown_action"}

    async def trim(
        self,
        input_file: str = "",
        output_file: str = "",
        start: str = "00:00:00",
        end: str = "00:00:10",
    ) -> Dict[str, Any]:
        if not self._ffmpeg:
            return {"status": "error", "error": "FFmpeg অনুপলব্ধ"}

        if not output_file:
            name = Path(input_file).stem
            output_file = str(Path(self.output_dir) / f"{name}_trimmed.mp4")

        cmd = [
            self._ffmpeg, "-y",
            "-i", input_file,
            "-ss", start,
            "-to", end,
            "-c", "copy",
            output_file,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                log.info("ভিডিও ট্রিম সফল: %s", output_file)
                return {"status": "success", "output": output_file}
            return {"status": "error", "error": stderr.decode()[:500]}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def convert(
        self,
        input_file: str = "",
        output_format: str = "mp4",
        output_file: str = "",
    ) -> Dict[str, Any]:
        if not self._ffmpeg:
            return {"status": "error", "error": "FFmpeg অনুপলব্ধ"}

        if not output_file:
            name = Path(input_file).stem
            output_file = str(Path(self.output_dir) / f"{name}.{output_format}")

        cmd = [self._ffmpeg, "-y", "-i", input_file, output_file]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode == 0:
                log.info("ভিডিও কনভার্ট সফল: %s", output_file)
                return {"status": "success", "output": output_file}
            return {"status": "error", "error": stderr.decode()[:500]}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def render_mlt(
        self,
        mlt_file: str = "",
        output_file: str = "",
    ) -> Dict[str, Any]:
        melt = shutil.which(self.melt_path) or shutil.which("melt")
        if not melt:
            return {"status": "error", "error": "melt অনুপলব্ধ"}

        if not output_file:
            output_file = str(Path(self.output_dir) / "rendered_output.mp4")

        cmd = [melt, mlt_file, "-consumer", f"avformat:{output_file}"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode == 0:
                return {"status": "success", "output": output_file}
            return {"status": "error", "error": stderr.decode()[:500]}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def get_video_info(self, input_file: str) -> Dict[str, Any]:
        if not self._ffmpeg:
            return {"status": "error"}

        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return {"status": "error", "error": "ffprobe অনুপলব্ধ"}

        cmd = [
            ffprobe, "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            input_file,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            import json
            return {"status": "success", "info": json.loads(stdout.decode())}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        log.info("Shotcut ফলব্যাক — সরল FFmpeg কমান্ড চেষ্টা")
        return {"status": "fallback", "message": "বিকল্প পদ্ধতি ব্যবহার করুন"}
