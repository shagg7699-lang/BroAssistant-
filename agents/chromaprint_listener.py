"""
ব্রো (Bro) — Chromaprint অডিও ফিঙ্গারপ্রিন্ট
pyacoustid / Chromaprint দিয়ে গান/অডিও শনাক্তকরণ।
"""

import asyncio
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("chromaprint")

try:
    import acoustid

    _HAS_ACOUSTID = True
except ImportError:
    _HAS_ACOUSTID = False
    log.warning("pyacoustid ইনস্টল নেই")


class ChromaprintListener:
    ACOUSTID_API_KEY = "8XaBELgH"  # free test key

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self._fpcalc = shutil.which("fpcalc")

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [{"description": "অডিও ফিঙ্গারপ্রিন্ট ও শনাক্তকরণ", "action": "identify", "risky": False}]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "acoustid": _HAS_ACOUSTID, "fpcalc": self._fpcalc is not None}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        action = step.get("action", "")
        params = step.get("params", {})

        if action == "identify":
            return await self.identify(params.get("audio_file", ""))
        elif action == "fingerprint":
            return await self.fingerprint(params.get("audio_file", ""))
        return {"status": "unknown_action"}

    async def fingerprint(self, audio_file: str) -> Dict[str, Any]:
        if not _HAS_ACOUSTID:
            return {"status": "error", "error": "pyacoustid ইনস্টল প্রয়োজন"}

        if not audio_file or not Path(audio_file).exists():
            return {"status": "error", "error": "অডিও ফাইল পাওয়া যায়নি"}

        try:
            duration, fingerprint = await asyncio.to_thread(
                acoustid.fingerprint_file, audio_file
            )
            return {
                "status": "success",
                "duration": duration,
                "fingerprint": fingerprint[:100] + "..." if len(fingerprint) > 100 else fingerprint,
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def identify(self, audio_file: str) -> Dict[str, Any]:
        if not _HAS_ACOUSTID:
            return {"status": "error", "error": "pyacoustid ইনস্টল প্রয়োজন"}

        if not audio_file or not Path(audio_file).exists():
            return {"status": "error", "error": "অডিও ফাইল পাওয়া যায়নি"}

        try:
            results = []
            matches = await asyncio.to_thread(
                acoustid.match, self.ACOUSTID_API_KEY, audio_file
            )
            for score, recording_id, title, artist in matches:
                results.append({
                    "score": round(score, 3),
                    "recording_id": recording_id,
                    "title": title,
                    "artist": artist,
                })
                if len(results) >= 5:
                    break

            if results:
                best = results[0]
                log.info("গান শনাক্ত: %s — %s (%.1f%%)", best["artist"], best["title"], best["score"] * 100)
                return {"status": "success", "matches": results}
            return {"status": "no_match", "message": "কোনো মিল পাওয়া যায়নি"}

        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def identify_from_recording(self, audio_data: bytes, sample_rate: int = 44100) -> Dict[str, Any]:
        import tempfile
        import wave

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                with wave.open(tmp_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_data)

            result = await self.identify(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)
            return result
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        return None
