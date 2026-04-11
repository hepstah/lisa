"""Microphone capture with VAD silence detection.

Pi-only module per D-15. In dev mode this module is never instantiated;
text input bypasses audio capture entirely.

Audio source is NOT imported here -- no PyAudio or sounddevice dependency.
This class defines the capture logic; the actual audio source is injected
by the caller (pipeline orchestrator on Pi).
"""

import logging
import math
import struct

logger = logging.getLogger(__name__)


class AudioCapture:
    """Frame-by-frame audio capture with energy-based voice activity detection.

    Processes 16-bit signed PCM frames and detects end-of-speech via
    consecutive silence frames. Configurable silence threshold, max silence
    duration, and hard time cap.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 80,
        silence_threshold: float = 500.0,
        max_silence_frames: int = 15,
        max_capture_seconds: float = 10.0,
    ) -> None:
        self._sample_rate = sample_rate
        self._frame_duration_ms = frame_duration_ms
        self._silence_threshold = silence_threshold
        self._max_silence_frames = max_silence_frames
        self._max_capture_seconds = max_capture_seconds

        # Derived: samples per frame
        self._samples_per_frame = int(sample_rate * frame_duration_ms / 1000)
        # Derived: max frames before hard cap
        self._max_frames = int(max_capture_seconds * 1000 / frame_duration_ms)

        self._buffer: list[bytes] = []
        self._silence_count = 0
        self._has_speech = False
        self._frame_count = 0

    def _rms_energy(self, frame: bytes) -> float:
        """Calculate RMS energy of a 16-bit signed PCM frame."""
        n_samples = len(frame) // 2
        if n_samples == 0:
            return 0.0
        samples = struct.unpack(f"<{n_samples}h", frame)
        sum_sq = sum(s * s for s in samples)
        return math.sqrt(sum_sq / n_samples)

    def process_frame(self, frame: bytes) -> bool:
        """Process one audio frame.

        Args:
            frame: Raw 16-bit signed PCM audio data.

        Returns:
            True if capture should continue, False if capture is complete
            (enough silence detected or max duration exceeded).
        """
        self._buffer.append(frame)
        self._frame_count += 1

        energy = self._rms_energy(frame)

        if energy < self._silence_threshold:
            self._silence_count += 1
        else:
            self._silence_count = 0
            self._has_speech = True

        # Hard time cap
        if self._frame_count >= self._max_frames:
            logger.info("AudioCapture hit max duration (%ss)", self._max_capture_seconds)
            return False

        # Silence-based end of speech (only after some speech was detected)
        if self._has_speech and self._silence_count >= self._max_silence_frames:
            logger.info(
                "AudioCapture detected end of speech after %d frames",
                self._frame_count,
            )
            return False

        return True

    def get_audio(self) -> bytes:
        """Return all buffered frames as a single bytes object."""
        return b"".join(self._buffer)

    def reset(self) -> None:
        """Clear buffer and reset state for a new capture."""
        self._buffer = []
        self._silence_count = 0
        self._has_speech = False
        self._frame_count = 0

    def has_speech(self) -> bool:
        """Return whether any non-silent frame was detected."""
        return self._has_speech
