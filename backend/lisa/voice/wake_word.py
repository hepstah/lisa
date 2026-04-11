"""openWakeWord wrapper for wake phrase detection.

Pi-only module per D-15. In dev mode this module is never instantiated;
command injection starts at the STT/LLM stage.
"""

import logging

logger = logging.getLogger(__name__)


# Graceful import: openwakeword requires onnxruntime and may not
# install cleanly on all platforms.
try:
    import openwakeword
    from openwakeword.model import Model

    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    Model = None  # type: ignore[assignment,misc]
    OPENWAKEWORD_AVAILABLE = False


class WakeWordDetector:
    """Detects wake phrases in audio frames using openWakeWord.

    Uses "hey_jarvis" as a development stand-in. Custom "hey_lisa" model
    training is deferred to v2 per ADV-03.

    Supports mute/unmute for TTS echo prevention (pitfall 1).
    """

    def __init__(
        self,
        model_names: list[str] | None = None,
        threshold: float = 0.5,
    ) -> None:
        if not OPENWAKEWORD_AVAILABLE:
            raise RuntimeError(
                "openwakeword not available -- "
                "wake word detection requires Pi environment"
            )

        if model_names is None:
            model_names = ["hey_jarvis"]

        # Download pre-trained models if not already cached
        openwakeword.utils.download_models()

        self._model = Model(wakeword_models=model_names)
        self._threshold = threshold
        self._muted = False

        logger.info(
            "WakeWordDetector initialized with models=%s threshold=%.2f",
            model_names,
            threshold,
        )

    def detect(self, audio_frame: bytes) -> dict[str, float]:
        """Process an audio frame and return above-threshold detections.

        Args:
            audio_frame: 80ms of 16kHz 16-bit PCM audio (1280 samples = 2560 bytes).

        Returns:
            Dict of model_name -> score for detections above threshold.
            Empty dict if muted or no detections.
        """
        if self._muted:
            return {}

        prediction = self._model.predict(audio_frame)

        return {
            name: score
            for name, score in prediction.items()
            if score > self._threshold
        }

    def mute(self) -> None:
        """Mute detection (call before TTS playback per pitfall 1)."""
        self._muted = True
        logger.debug("Wake word detection muted")

    def unmute(self) -> None:
        """Unmute detection (call after TTS playback + cooldown)."""
        self._muted = False
        logger.debug("Wake word detection unmuted")

    def is_muted(self) -> bool:
        """Return whether detection is currently muted."""
        return self._muted
