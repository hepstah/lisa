"""Tests for wake word detector (mocked openwakeword) and audio capture (pure logic)."""

import struct
import sys
from unittest.mock import Mock, MagicMock

import pytest

# Mock openwakeword before importing wake_word module so tests work
# on platforms where openwakeword may not install cleanly.
mock_oww = MagicMock()
mock_model_instance = Mock()
sys.modules["openwakeword"] = mock_oww
sys.modules["openwakeword.model"] = mock_oww.model
sys.modules["openwakeword.utils"] = mock_oww.utils
mock_oww.model.Model.return_value = mock_model_instance

# Now import with mocked dependencies
import importlib
import lisa.voice.wake_word as ww_module

# Force reload to pick up our mocked modules
importlib.reload(ww_module)
from lisa.voice.wake_word import WakeWordDetector

from lisa.voice.audio_capture import AudioCapture


# -- Wake Word Detector Tests --


@pytest.fixture
def detector():
    """Create a WakeWordDetector with mocked openwakeword."""
    return WakeWordDetector(model_names=["hey_jarvis"], threshold=0.5)


def test_wake_word_detect_above_threshold(detector):
    """Detection above threshold returns the score."""
    mock_model_instance.predict.return_value = {"hey_jarvis": 0.85}
    frame = b"\x00" * 2560  # 80ms at 16kHz, 16-bit

    result = detector.detect(frame)

    assert result == {"hey_jarvis": 0.85}
    mock_model_instance.predict.assert_called_once_with(frame)


def test_wake_word_detect_below_threshold(detector):
    """Detection below threshold returns empty dict."""
    mock_model_instance.predict.return_value = {"hey_jarvis": 0.2}
    frame = b"\x00" * 2560

    result = detector.detect(frame)

    assert result == {}


def test_wake_word_mute_blocks_detection(detector):
    """Muted detector returns empty dict without calling predict."""
    mock_model_instance.predict.reset_mock()
    detector.mute()

    frame = b"\x00" * 2560
    result = detector.detect(frame)

    assert result == {}
    mock_model_instance.predict.assert_not_called()
    assert detector.is_muted() is True


def test_wake_word_unmute_resumes_detection(detector):
    """Unmuting resumes detection normally."""
    detector.mute()
    detector.unmute()

    mock_model_instance.predict.return_value = {"hey_jarvis": 0.8}
    frame = b"\x00" * 2560
    result = detector.detect(frame)

    assert result == {"hey_jarvis": 0.8}
    assert detector.is_muted() is False


# -- Audio Capture Tests --


def _make_silent_frame(n_samples: int = 1280) -> bytes:
    """Create a frame of near-silence (very low amplitude)."""
    return struct.pack(f"<{n_samples}h", *([1] * n_samples))


def _make_speech_frame(n_samples: int = 1280, amplitude: int = 5000) -> bytes:
    """Create a frame with speech-like energy."""
    return struct.pack(f"<{n_samples}h", *([amplitude] * n_samples))


def test_audio_capture_silence_ends_capture():
    """Feeding only silence after speech triggers end-of-capture."""
    capture = AudioCapture(
        sample_rate=16000,
        frame_duration_ms=80,
        silence_threshold=500.0,
        max_silence_frames=5,
        max_capture_seconds=10.0,
    )

    # Feed one speech frame so has_speech becomes True
    result = capture.process_frame(_make_speech_frame())
    assert result is True

    # Feed silence frames until capture ends
    for i in range(10):
        result = capture.process_frame(_make_silent_frame())
        if not result:
            break

    assert result is False
    assert capture.has_speech() is True


def test_audio_capture_speech_then_silence():
    """Speech followed by silence: has_speech is True, capture ends after silence."""
    capture = AudioCapture(
        sample_rate=16000,
        frame_duration_ms=80,
        silence_threshold=500.0,
        max_silence_frames=3,
        max_capture_seconds=10.0,
    )

    # Feed several speech frames
    for _ in range(5):
        assert capture.process_frame(_make_speech_frame()) is True

    assert capture.has_speech() is True

    # Feed silence frames
    for _ in range(2):
        assert capture.process_frame(_make_silent_frame()) is True

    # Third silence frame should end capture (max_silence_frames=3)
    assert capture.process_frame(_make_silent_frame()) is False

    # get_audio should return all buffered data
    audio = capture.get_audio()
    assert len(audio) > 0
    # 8 frames total * 1280 samples * 2 bytes = 20480 bytes
    assert len(audio) == 8 * 1280 * 2


def test_audio_capture_reset():
    """Reset clears buffer and state."""
    capture = AudioCapture(max_silence_frames=3)

    capture.process_frame(_make_speech_frame())
    assert capture.has_speech() is True
    assert len(capture.get_audio()) > 0

    capture.reset()

    assert capture.has_speech() is False
    assert capture.get_audio() == b""


def test_audio_capture_max_duration():
    """Hard time cap ends capture even with continuous speech."""
    capture = AudioCapture(
        frame_duration_ms=80,
        max_capture_seconds=0.24,  # 3 frames at 80ms each
    )

    assert capture.process_frame(_make_speech_frame()) is True
    assert capture.process_frame(_make_speech_frame()) is True
    # Third frame hits max_frames (0.24s / 0.08s = 3)
    assert capture.process_frame(_make_speech_frame()) is False
