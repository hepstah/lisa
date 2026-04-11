"""Piper TTS service with dev-mode file output per D-14."""

import asyncio
import logging
import os
import subprocess
import time
import wave

logger = logging.getLogger(__name__)


class TTSError(Exception):
    """Raised when TTS synthesis fails."""

    pass


# Graceful import: piper-tts may not be available on all platforms
try:
    from piper import PiperVoice

    PIPER_AVAILABLE = True
except ImportError:
    PiperVoice = None  # type: ignore[assignment,misc]
    PIPER_AVAILABLE = False


class TTSService:
    """Wraps Piper TTS with dev-mode WAV file output.

    In dev mode (D-14): saves WAV files to output_dir for manual playback.
    In Pi mode: saves to file (actual speaker playback deferred to Pi deployment).
    """

    def __init__(
        self,
        model_path: str,
        output_dir: str = "tts_output",
        dev_mode: bool = True,
    ) -> None:
        self._dev_mode = dev_mode
        self._output_dir = output_dir

        if not PIPER_AVAILABLE:
            raise TTSError("piper-tts library not available")

        if not model_path or not os.path.isfile(model_path):
            raise TTSError(f"TTS model not found: {model_path}")

        self._voice = PiperVoice.load(model_path)

        if dev_mode:
            os.makedirs(output_dir, exist_ok=True)

    def _synthesize_to_file(self, text: str, path: str) -> None:
        """Sync helper: run Piper synthesis and write WAV to path."""
        with wave.open(path, "wb") as wav_file:
            self._voice.synthesize_wav(text, wav_file)

    async def speak(self, text: str) -> str | None:
        """Synthesize text to speech.

        In dev mode: writes a timestamped WAV file and returns the path.
        Returns None for empty/whitespace text.
        Raises TTSError on synthesis failure.
        """
        if not text or not text.strip():
            logger.warning("TTS speak() called with empty text, skipping")
            return None

        timestamp = int(time.time() * 1000)
        filename = f"tts_{timestamp}.wav"

        if self._dev_mode:
            path = os.path.join(self._output_dir, filename)
        else:
            path = os.path.join(self._output_dir, filename)

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._synthesize_to_file, text, path)
        except Exception as e:
            raise TTSError(f"TTS synthesis failed: {e}") from e

        # Pi mode: play audio through speaker via aplay
        if not self._dev_mode:
            await asyncio.to_thread(
                subprocess.run, ["aplay", "-q", path], check=True, timeout=10
            )

        logger.info("TTS wrote %s", path)
        return path
