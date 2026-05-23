"""
ব্রো (Bro) — AutoVideo জেনারেটর
টেক্সট/স্ক্রিপ্ট থেকে ভিডিও তৈরি — FFmpeg + ইমেজ সংশ্লেষণ।
AutoVideo ইন্সপায়ার্ড।
"""

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("autovideo_generator")


class AutoVideoGenerator:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.output_dir = cfg.get("output_dir", "data/video_output")
        self._ffmpeg = shutil.which("ffmpeg")
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [
            {"description": "স্ক্রিপ্ট তৈরি", "action": "generate_script", "risky": False},
            {"description": "ইমেজ/ফ্রেম তৈরি", "action": "generate_frames", "risky": False},
            {"description": "ভিডিও কম্পাইল", "action": "compile_video", "risky": False},
        ]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "ffmpeg": self._ffmpeg is not None}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        action = step.get("action", "")
        params = step.get("params", {})

        if action == "generate_script":
            return await self.generate_script(params.get("topic", ""))
        elif action == "generate_frames":
            return await self.generate_frames(params.get("script", []))
        elif action == "compile_video":
            return await self.compile_video(
                params.get("frames_dir", ""),
                params.get("audio", ""),
                params.get("output", ""),
            )
        return {"status": "unknown_action"}

    async def generate_script(self, topic: str) -> Dict[str, Any]:
        script = {
            "title": topic or "Untitled Video",
            "scenes": [
                {
                    "id": 1,
                    "description": f"পরিচিতি: {topic}",
                    "duration": 5,
                    "narration": f"{topic} সম্পর্কে আজ আমরা জানব।",
                },
                {
                    "id": 2,
                    "description": "মূল বিষয়বস্তু",
                    "duration": 10,
                    "narration": "এখানে মূল বিষয়বস্তু থাকবে।",
                },
                {
                    "id": 3,
                    "description": "উপসংহার",
                    "duration": 5,
                    "narration": "ধন্যবাদ দেখার জন্য।",
                },
            ],
        }
        return {"status": "success", "script": script}

    async def generate_frames(self, script_scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        frames_dir = Path(self.output_dir) / "autovideo_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        if not self._ffmpeg:
            return {"status": "error", "error": "FFmpeg অনুপলব্ধ"}

        generated = []
        for i, scene in enumerate(script_scenes):
            output = str(frames_dir / f"scene_{i:03d}.png")
            duration = scene.get("duration", 5)
            text = scene.get("description", f"Scene {i + 1}")

            cmd = [
                self._ffmpeg, "-y",
                "-f", "lavfi",
                "-i", f"color=c=black:s=1920x1080:d=1",
                "-vf", f"drawtext=text='{text}':fontsize=48:fontcolor=white:x=(w-tw)/2:y=(h-th)/2",
                "-frames:v", "1",
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
                    generated.append({"scene": i, "file": output, "duration": duration})
            except Exception as exc:
                log.error("ফ্রেম তৈরি ব্যর্থ (scene %d): %s", i, exc)

        return {"status": "success", "frames": generated, "dir": str(frames_dir)}

    async def compile_video(
        self,
        frames_dir: str = "",
        audio_path: str = "",
        output_path: str = "",
    ) -> Dict[str, Any]:
        if not self._ffmpeg:
            return {"status": "error", "error": "FFmpeg অনুপলব্ধ"}

        if not output_path:
            output_path = str(Path(self.output_dir) / "autovideo_output.mp4")

        if not frames_dir:
            frames_dir = str(Path(self.output_dir) / "autovideo_frames")

        concat_file = Path(frames_dir) / "concat.txt"
        frames = sorted(Path(frames_dir).glob("scene_*.png"))

        if not frames:
            return {"status": "error", "error": "কোনো ফ্রেম পাওয়া যায়নি"}

        lines = []
        for frame in frames:
            lines.append(f"file '{frame}'")
            lines.append("duration 5")
        concat_file.write_text("\n".join(lines), encoding="utf-8")

        cmd = [
            self._ffmpeg, "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-vsync", "vfr",
            "-pix_fmt", "yuv420p",
        ]

        if audio_path and Path(audio_path).exists():
            cmd.extend(["-i", audio_path, "-shortest"])

        cmd.append(output_path)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode == 0:
                log.info("ভিডিও তৈরি সফল: %s", output_path)
                return {"status": "success", "output": output_path}
            return {"status": "error", "error": stderr.decode()[:500]}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        return None
