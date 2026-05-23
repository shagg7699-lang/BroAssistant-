"""
ব্রো (Bro) — ভিডিও এজেন্ট
VideoAgent / UniVA ইন্সপায়ার্ড — ভিডিও বোঝা, সামারি, এডিট।
"""

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("video_agent")


class VideoAgent:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.output_dir = cfg.get("output_dir", "data/video_output")
        self._ffmpeg = shutil.which("ffmpeg")
        self._ffprobe = shutil.which("ffprobe")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        cmd_lower = command.lower()
        steps = []

        if any(w in cmd_lower for w in ["সামারি", "summary", "বোঝো", "understand"]):
            steps.append({"description": "ভিডিও বিশ্লেষণ ও সামারি", "action": "summarize", "risky": False})
        elif any(w in cmd_lower for w in ["ফ্রেম", "frame", "extract"]):
            steps.append({"description": "ফ্রেম এক্সট্র্যাক্ট", "action": "extract_frames", "risky": False})
        elif any(w in cmd_lower for w in ["অডিও", "audio"]):
            steps.append({"description": "অডিও এক্সট্র্যাক্ট", "action": "extract_audio", "risky": False})
        else:
            steps.append({"description": command, "action": "analyze", "risky": False})

        return steps

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "ffmpeg": self._ffmpeg is not None}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        action = step.get("action", "")
        params = step.get("params", {})

        if action == "extract_frames":
            return await self.extract_frames(
                params.get("video", ""),
                params.get("interval", 5),
            )
        elif action == "extract_audio":
            return await self.extract_audio(params.get("video", ""))
        elif action in ("summarize", "analyze"):
            return await self.analyze_video(params.get("video", ""))
        return {"status": "unknown_action"}

    async def extract_frames(
        self,
        video_path: str,
        interval_seconds: int = 5,
        max_frames: int = 20,
    ) -> Dict[str, Any]:
        if not self._ffmpeg:
            return {"status": "error", "error": "FFmpeg অনুপলব্ধ"}

        frames_dir = Path(self.output_dir) / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            self._ffmpeg, "-y",
            "-i", video_path,
            "-vf", f"fps=1/{interval_seconds}",
            "-frames:v", str(max_frames),
            str(frames_dir / "frame_%04d.png"),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            frames = sorted(frames_dir.glob("frame_*.png"))
            log.info("ফ্রেম এক্সট্র্যাক্ট: %d", len(frames))
            return {
                "status": "success",
                "frames": [str(f) for f in frames],
                "count": len(frames),
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def extract_audio(self, video_path: str, output_format: str = "wav") -> Dict[str, Any]:
        if not self._ffmpeg:
            return {"status": "error", "error": "FFmpeg অনুপলব্ধ"}

        name = Path(video_path).stem
        output = str(Path(self.output_dir) / f"{name}_audio.{output_format}")

        cmd = [
            self._ffmpeg, "-y",
            "-i", video_path,
            "-vn", "-acodec", "pcm_s16le" if output_format == "wav" else "copy",
            output,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if proc.returncode == 0:
                return {"status": "success", "output": output}
            return {"status": "error", "error": "অডিও এক্সট্র্যাক্ট ব্যর্থ"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def analyze_video(self, video_path: str) -> Dict[str, Any]:
        if not self._ffprobe:
            return {"status": "error", "error": "ffprobe অনুপলব্ধ"}

        cmd = [
            self._ffprobe, "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            info = json.loads(stdout.decode())

            fmt = info.get("format", {})
            streams = info.get("streams", [])

            video_streams = [s for s in streams if s.get("codec_type") == "video"]
            audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

            analysis = {
                "duration": float(fmt.get("duration", 0)),
                "size_mb": round(int(fmt.get("size", 0)) / (1024 * 1024), 2),
                "format": fmt.get("format_name", "unknown"),
                "video_codec": video_streams[0].get("codec_name") if video_streams else None,
                "resolution": f"{video_streams[0].get('width')}x{video_streams[0].get('height')}" if video_streams else None,
                "fps": eval(video_streams[0].get("r_frame_rate", "0/1")) if video_streams else 0,
                "audio_codec": audio_streams[0].get("codec_name") if audio_streams else None,
            }

            return {"status": "success", "analysis": analysis}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        return None
