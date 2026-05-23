"""
ব্রো (Bro) — টেক্সট-টু-স্পিচ ইঞ্জিন
Piper TTS / Kokoro ব্যবহার করে লোকাল TTS।
"""

import io
import os
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict, Optional

from utils.logger import get_logger

log = get_logger("tts")

try:
    import sounddevice as sd
    import numpy as np

    _HAS_SD = True
except ImportError:
    _HAS_SD = False


class TTSEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.engine = cfg.get("engine", "piper")
        self.voice = cfg.get("voice", "bn_BD-male-medium")
        self.fallback_voice = cfg.get("fallback_voice", "en_US-lessac-medium")
        self.rate = cfg.get("rate", 1.0)
        self.volume = cfg.get("volume", 0.8)
        self._piper_available: Optional[bool] = None

    def _check_piper(self) -> bool:
        if self._piper_available is None:
            try:
                result = subprocess.run(
                    ["piper", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                self._piper_available = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._piper_available = False
                log.warning("Piper TTS অনুপলব্ধ — ফলব্যাক মোড")
        return self._piper_available

    def speak(self, text: str, voice: Optional[str] = None, blocking: bool = True) -> bool:
        if not text.strip():
            return False

        voice = voice or self.voice

        if self.engine == "piper" and self._check_piper():
            return self._speak_piper(text, voice, blocking)

        return self._speak_fallback(text, blocking)

    def _speak_piper(self, text: str, voice: str, blocking: bool) -> bool:
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            cmd = [
                "piper",
                "--model", voice,
                "--output_file", tmp_path,
                "--length_scale", str(1.0 / self.rate),
            ]

            proc = subprocess.run(
                cmd,
                input=text,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if proc.returncode != 0:
                log.error("Piper ত্রুটি: %s", proc.stderr)
                return self._speak_fallback(text, blocking)

            self._play_wav(tmp_path, blocking)
            return True

        except Exception as exc:
            log.error("Piper TTS ব্যর্থ: %s", exc)
            return self._speak_fallback(text, blocking)
        finally:
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _speak_fallback(self, text: str, blocking: bool) -> bool:
        for cmd_template in [
            ["espeak-ng", "-v", "bn", "{text}"],
            ["espeak", "-v", "bn", "{text}"],
            ["say", "{text}"],
        ]:
            try:
                cmd = [part.replace("{text}", text) for part in cmd_template]
                if blocking:
                    subprocess.run(cmd, capture_output=True, timeout=30)
                else:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        log.warning("কোনো TTS ইঞ্জিন পাওয়া যায়নি — টেক্সট আউটপুট")
        print(f"[ব্রো বলছে]: {text}")
        return False

    def _play_wav(self, wav_path: str, blocking: bool = True) -> None:
        if not _HAS_SD:
            self._play_wav_subprocess(wav_path, blocking)
            return

        try:
            with wave.open(wav_path, "rb") as wf:
                rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                audio *= self.volume

            if blocking:
                sd.play(audio, samplerate=rate)
                sd.wait()
            else:
                sd.play(audio, samplerate=rate)
        except Exception as exc:
            log.error("WAV প্লে ব্যর্থ: %s", exc)
            self._play_wav_subprocess(wav_path, blocking)

    def _play_wav_subprocess(self, wav_path: str, blocking: bool) -> None:
        for player in ["aplay", "paplay", "ffplay -nodisp -autoexit"]:
            try:
                cmd = player.split() + [wav_path]
                if blocking:
                    subprocess.run(cmd, capture_output=True, timeout=30)
                else:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

    def synthesize_to_file(self, text: str, output_path: str, voice: Optional[str] = None) -> bool:
        voice = voice or self.voice

        if self.engine == "piper" and self._check_piper():
            try:
                cmd = [
                    "piper",
                    "--model", voice,
                    "--output_file", output_path,
                    "--length_scale", str(1.0 / self.rate),
                ]
                proc = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=30)
                if proc.returncode == 0:
                    log.info("TTS ফাইল সেভ: %s", output_path)
                    return True
            except Exception as exc:
                log.error("TTS ফাইল সেভ ব্যর্থ: %s", exc)

        return False
