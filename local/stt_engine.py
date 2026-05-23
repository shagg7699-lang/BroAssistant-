"""
ব্রো (Bro) — স্পিচ-টু-টেক্সট ইঞ্জিন
faster-whisper ব্যবহার করে রিয়েল-টাইম ভয়েস ট্রান্সক্রিপশন।
"""

import io
import queue
import threading
import time
from typing import Any, Callable, Dict, Optional

import numpy as np

from utils.logger import get_logger

log = get_logger("stt")

try:
    from faster_whisper import WhisperModel

    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False
    log.warning("faster-whisper ইনস্টল নেই")

try:
    import sounddevice as sd

    _HAS_SD = True
except ImportError:
    _HAS_SD = False
    log.warning("sounddevice ইনস্টল নেই")


class STTEngine:
    SAMPLE_RATE = 16000
    CHANNELS = 1
    BLOCK_DURATION = 0.5

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.model_size = cfg.get("model_size", "small")
        self.language = cfg.get("language", "bn")
        self.fallback_language = cfg.get("fallback_language", "en")
        self.device = cfg.get("device", "cpu")
        self.compute_type = cfg.get("compute_type", "int8")
        self.beam_size = cfg.get("beam_size", 5)
        self.vad_filter = cfg.get("vad_filter", True)

        self._model: Optional[Any] = None
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._recording = False
        self._stream: Optional[Any] = None

    def _load_model(self) -> None:
        if not _HAS_WHISPER:
            raise RuntimeError("faster-whisper ইনস্টল প্রয়োজন")
        if self._model is None:
            log.info("Whisper মডেল লোড হচ্ছে: %s (%s)", self.model_size, self.device)
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            log.info("Whisper মডেল প্রস্তুত")

    def transcribe(self, audio_data: np.ndarray, language: Optional[str] = None) -> str:
        self._load_model()
        lang = language or self.language
        assert self._model is not None

        segments, info = self._model.transcribe(
            audio_data,
            language=lang,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
        )
        text = " ".join(seg.text.strip() for seg in segments)
        log.debug("ট্রান্সক্রাইব [%s]: %s", info.language, text[:100])
        return text

    def transcribe_file(self, file_path: str, language: Optional[str] = None) -> str:
        self._load_model()
        lang = language or self.language
        assert self._model is not None

        segments, info = self._model.transcribe(
            file_path,
            language=lang,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
        )
        return " ".join(seg.text.strip() for seg in segments)

    def start_recording(self) -> None:
        if not _HAS_SD:
            raise RuntimeError("sounddevice ইনস্টল প্রয়োজন")
        if self._recording:
            return

        self._recording = True
        self._audio_queue = queue.Queue()

        def callback(indata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
            if status:
                log.warning("অডিও স্ট্রিম: %s", status)
            self._audio_queue.put(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="float32",
            blocksize=int(self.SAMPLE_RATE * self.BLOCK_DURATION),
            callback=callback,
        )
        self._stream.start()
        log.info("রেকর্ডিং শুরু")

    def stop_recording(self) -> np.ndarray:
        if not self._recording:
            return np.array([], dtype="float32")

        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        chunks = []
        while not self._audio_queue.empty():
            chunks.append(self._audio_queue.get())

        log.info("রেকর্ডিং শেষ: %d চাঙ্ক", len(chunks))
        if chunks:
            return np.concatenate(chunks, axis=0).flatten()
        return np.array([], dtype="float32")

    def record_and_transcribe(self, duration: float = 5.0, language: Optional[str] = None) -> str:
        if not _HAS_SD:
            raise RuntimeError("sounddevice ইনস্টল প্রয়োজন")

        log.info("রেকর্ডিং: %.1f সেকেন্ড", duration)
        audio = sd.rec(
            int(duration * self.SAMPLE_RATE),
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="float32",
        )
        sd.wait()
        return self.transcribe(audio.flatten(), language)

    def listen_for_wake_word(
        self,
        wake_word: str = "ব্রো",
        callback: Optional[Callable[[str], None]] = None,
        check_interval: float = 2.0,
    ) -> None:
        if not _HAS_SD or not _HAS_WHISPER:
            raise RuntimeError("sounddevice ও faster-whisper ইনস্টল প্রয়োজন")

        self._load_model()
        log.info("ওয়েক ওয়ার্ড শুনছি: '%s'", wake_word)
        wake_lower = wake_word.lower()

        while True:
            try:
                audio = sd.rec(
                    int(check_interval * self.SAMPLE_RATE),
                    samplerate=self.SAMPLE_RATE,
                    channels=self.CHANNELS,
                    dtype="float32",
                )
                sd.wait()
                text = self.transcribe(audio.flatten())

                if wake_lower in text.lower():
                    log.info("ওয়েক ওয়ার্ড শনাক্ত!")
                    if callback:
                        callback(text)
            except KeyboardInterrupt:
                break
            except Exception as exc:
                log.error("ওয়েক ওয়ার্ড ত্রুটি: %s", exc)
                time.sleep(1)
