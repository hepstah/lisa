"""Tests for TTS service with mocked Piper."""

import asyncio
import os
import struct
import wave
from unittest.mock import Mock, patch, MagicMock

import pytest


def make_mock_voice():
    """Create a mock PiperVoice that writes valid WAV data."""
    mock_voice = Mock()

    def fake_synthesize_wav(text, wav_file):
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(struct.pack("<h", 0) * 22050)  # 1s silence

    mock_voice.synthesize_wav = fake_synthesize_wav
    return mock_voice


@pytest.fixture
def mock_piper():
    """Patch PiperVoice.load to return a mock voice."""
    mock_voice = make_mock_voice()
    with patch("lisa.services.tts_service.PiperVoice") as mock_cls:
        mock_cls.load.return_value = mock_voice
        with patch("lisa.services.tts_service.PIPER_AVAILABLE", True):
            yield mock_cls


@pytest.fixture
def tts_service(mock_piper, tmp_path):
    """Create a TTSService with mocked Piper in dev mode."""
    # Create a fake model file
    model_file = tmp_path / "test_voice.onnx"
    model_file.write_text("fake model")

    from lisa.services.tts_service import TTSService

    return TTSService(
        model_path=str(model_file),
        output_dir=str(tmp_path / "tts_output"),
        dev_mode=True,
    )


async def test_tts_dev_mode_writes_wav(tts_service, tmp_path):
    """TTSService in dev mode writes a WAV file to tts_output_dir when speak() is called."""
    result = await tts_service.speak("Hello world")
    assert result is not None
    assert os.path.exists(result)
    output_dir = str(tmp_path / "tts_output")
    assert result.startswith(output_dir)


async def test_tts_wav_has_valid_headers(tts_service):
    """The WAV file written by speak() has valid WAV headers (starts with RIFF)."""
    result = await tts_service.speak("Test audio")
    assert result is not None
    with open(result, "rb") as f:
        header = f.read(4)
    assert header == b"RIFF"


async def test_tts_empty_text_no_crash(tts_service):
    """TTSService.speak() with empty text does not crash (no-op, returns None)."""
    result = await tts_service.speak("")
    assert result is None
    result2 = await tts_service.speak("   ")
    assert result2 is None


async def test_tts_missing_model_raises_error():
    """TTSError is raised when Piper model file does not exist at given path."""
    with patch("lisa.services.tts_service.PIPER_AVAILABLE", True):
        from lisa.services.tts_service import TTSService, TTSError

        with pytest.raises(TTSError, match="TTS model not found"):
            TTSService(
                model_path="/nonexistent/model.onnx",
                output_dir="/tmp/tts_out",
                dev_mode=True,
            )


async def test_tts_speak_returns_file_path(tts_service, tmp_path):
    """speak() returns the file path of the written WAV in dev mode."""
    result = await tts_service.speak("Return path test")
    assert result is not None
    assert isinstance(result, str)
    assert result.endswith(".wav")
    # Verify the file actually exists and is non-empty
    assert os.path.isfile(result)
    assert os.path.getsize(result) > 0
