"""Tests for voice pipeline orchestrator. Every test verifies TTS.speak() was called (ERR-01)."""

import json

import pytest
from unittest.mock import AsyncMock, Mock

from lisa.services.voice_pipeline import (
    VoicePipeline,
    MSG_STT_TIMEOUT,
    MSG_LLM_TIMEOUT,
    MSG_NO_INTERNET,
    MSG_UNKNOWN_INTENT,
    MSG_DEVICE_ERROR,
    MSG_DEVICE_UNREACHABLE,
)
from lisa.services.llm_intent_service import (
    DeviceIntent,
    IntentResult,
    LLMTimeoutError,
    LLMError,
)
from lisa.services.stt_service import STTTimeoutError, STTError, STTNoSpeechError


def _sample_debug(text="turn on the bedroom lamp", tool_used=True):
    """Build a sample debug dict matching the shape parse_intent now returns."""
    if tool_used:
        decision = {
            "tool_used": True,
            "device_id": "fake-lamp-1",
            "action": "turn_on",
            "confirmation": "Turning on the bedroom lamp",
        }
    else:
        decision = {"tool_used": False, "text": "unknown"}
    return {
        "input_text": text,
        "devices_seen": [
            {"device_id": "fake-lamp-1", "alias": "Bedroom Lamp", "is_on": False}
        ],
        "decision": decision,
        "usage": {"input_tokens": 100, "output_tokens": 25},
        "stop_reason": "tool_use" if tool_used else "end_turn",
    }


@pytest.fixture
def mock_stt():
    stt = AsyncMock()
    stt.transcribe = AsyncMock(return_value="turn on the bedroom lamp")
    return stt


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.parse_intent = AsyncMock(
        return_value=IntentResult(
            intent=DeviceIntent(
                device_id="fake-lamp-1",
                action="turn_on",
                confirmation="Turning on the bedroom lamp",
            ),
            debug=_sample_debug(),
        )
    )
    return llm


@pytest.fixture
def mock_tts():
    tts = AsyncMock()
    tts.speak = AsyncMock(return_value="/tmp/tts_output.wav")
    return tts


@pytest.fixture
def mock_device_service():
    ds = AsyncMock()
    ds.get_all_states = AsyncMock(
        return_value=[
            Mock(
                device_id="fake-lamp-1",
                alias="Bedroom Lamp",
                is_on=False,
                is_reachable=True,
            )
        ]
    )
    ds.execute_command = AsyncMock(
        return_value=(
            Mock(
                device_id="fake-lamp-1",
                alias="Bedroom Lamp",
                is_on=True,
                is_reachable=True,
            ),
            {
                "id": 1,
                "status": "success",
                "device_id": "fake-lamp-1",
                "action": "turn_on",
            },
        )
    )
    return ds


@pytest.fixture
def pipeline(mock_stt, mock_llm, mock_tts, mock_device_service):
    return VoicePipeline(
        stt=mock_stt, llm=mock_llm, tts=mock_tts, device_service=mock_device_service
    )


@pytest.mark.asyncio
async def test_process_text_success(pipeline, mock_llm, mock_tts, mock_device_service):
    """Valid intent -> DeviceService -> TTS(confirmation) -> success."""
    result = await pipeline.process_text("turn on the bedroom lamp")

    mock_llm.parse_intent.assert_awaited_once()
    mock_device_service.execute_command.assert_awaited_once()
    call_kwargs = mock_device_service.execute_command.await_args.kwargs
    assert call_kwargs["device_id"] == "fake-lamp-1"
    assert call_kwargs["action"] == "turn_on"
    assert call_kwargs["source"] == "voice"
    assert call_kwargs["raw_input"] == "turn on the bedroom lamp"
    # llm_debug kwarg is present; dev_mode default is True so it is a string
    assert "llm_debug" in call_kwargs
    mock_tts.speak.assert_awaited_once_with("Turning on the bedroom lamp")
    assert result["status"] == "success"
    assert result["tts_spoken"] is True


@pytest.mark.asyncio
async def test_process_text_unknown_intent(pipeline, mock_llm, mock_tts):
    """LLM returns IntentResult(intent=None) -> TTS(unknown intent) -> rejected."""
    mock_llm.parse_intent = AsyncMock(
        return_value=IntentResult(
            intent=None, debug=_sample_debug(text="what is the weather?", tool_used=False)
        )
    )

    result = await pipeline.process_text("what is the weather?")

    mock_tts.speak.assert_awaited_once_with(MSG_UNKNOWN_INTENT)
    assert result["status"] == "rejected"
    assert result["error_stage"] == "intent"
    assert result["tts_spoken"] is True


@pytest.mark.asyncio
async def test_process_text_llm_timeout(pipeline, mock_llm, mock_tts):
    """LLM timeout -> TTS(timeout message) -> error."""
    mock_llm.parse_intent = AsyncMock(side_effect=LLMTimeoutError("LLM request timed out"))

    result = await pipeline.process_text("turn on the lamp")

    mock_tts.speak.assert_awaited_once_with(MSG_LLM_TIMEOUT)
    assert result["status"] == "error"
    assert result["error_stage"] == "llm"
    assert result["tts_spoken"] is True


@pytest.mark.asyncio
async def test_process_text_llm_connection_error(pipeline, mock_llm, mock_tts):
    """LLM connection error -> TTS(no internet message) -> error."""
    mock_llm.parse_intent = AsyncMock(
        side_effect=LLMError("Cannot reach intent processing service")
    )

    result = await pipeline.process_text("turn on the lamp")

    mock_tts.speak.assert_awaited_once_with(MSG_NO_INTERNET)
    assert result["status"] == "error"
    assert result["error_stage"] == "llm"
    assert result["tts_spoken"] is True


@pytest.mark.asyncio
async def test_process_audio_success(pipeline, mock_stt, mock_tts):
    """Audio -> STT -> process_text pipeline (happy path)."""
    result = await pipeline.process_audio(b"fake-audio-bytes")

    mock_stt.transcribe.assert_awaited_once_with(b"fake-audio-bytes")
    mock_tts.speak.assert_awaited_once()
    assert result["status"] == "success"
    assert result["tts_spoken"] is True


@pytest.mark.asyncio
async def test_process_audio_stt_timeout(pipeline, mock_stt, mock_tts):
    """STT timeout -> TTS(stt timeout message) -> error."""
    mock_stt.transcribe = AsyncMock(side_effect=STTTimeoutError("STT request timed out"))

    result = await pipeline.process_audio(b"fake-audio-bytes")

    mock_tts.speak.assert_awaited_once_with(MSG_STT_TIMEOUT)
    assert result["status"] == "error"
    assert result["error_stage"] == "stt"
    assert result["tts_spoken"] is True


@pytest.mark.asyncio
async def test_process_audio_stt_connection_error(pipeline, mock_stt, mock_tts):
    """STT connection error -> TTS(no internet message) -> error."""
    mock_stt.transcribe = AsyncMock(
        side_effect=STTError("Cannot reach speech recognition service")
    )

    result = await pipeline.process_audio(b"fake-audio-bytes")

    mock_tts.speak.assert_awaited_once_with(MSG_NO_INTERNET)
    assert result["status"] == "error"
    assert result["error_stage"] == "stt"
    assert result["tts_spoken"] is True


@pytest.mark.asyncio
async def test_process_text_device_error(
    pipeline, mock_tts, mock_device_service
):
    """Device execution error -> TTS(error message) -> error status."""
    mock_device_service.execute_command = AsyncMock(
        return_value=(
            None,
            {
                "id": 2,
                "status": "error",
                "device_id": "fake-lamp-1",
                "action": "turn_on",
                "error_message": "Device communication failed",
                "error_stage": "execution",
            },
        )
    )

    result = await pipeline.process_text("turn on the bedroom lamp")

    mock_tts.speak.assert_awaited_once_with("Device communication failed")
    assert result["status"] == "error"
    assert result["tts_spoken"] is True


@pytest.mark.asyncio
async def test_process_text_device_unreachable(
    pipeline, mock_tts, mock_device_service
):
    """Device unreachable -> TTS(unreachable message) -> error status."""
    mock_device_service.execute_command = AsyncMock(
        return_value=(
            None,
            {
                "id": 3,
                "status": "error",
                "device_id": "fake-lamp-1",
                "action": "turn_on",
                "error_message": "Connection refused",
                "error_stage": "device_unreachable",
            },
        )
    )

    result = await pipeline.process_text("turn on the bedroom lamp")

    mock_tts.speak.assert_awaited_once_with(MSG_DEVICE_UNREACHABLE)
    assert result["status"] == "error"
    assert result["tts_spoken"] is True


@pytest.mark.asyncio
async def test_process_audio_no_speech(pipeline, mock_stt, mock_tts):
    """No speech in audio -> TTS(no speech message) -> error with stt_no_speech stage."""
    from lisa.services.voice_pipeline import MSG_NO_SPEECH

    mock_stt.transcribe = AsyncMock(
        side_effect=STTNoSpeechError("No speech detected in audio")
    )

    result = await pipeline.process_audio(b"silent-audio-bytes")

    mock_tts.speak.assert_awaited_once_with(MSG_NO_SPEECH)
    assert result["status"] == "error"
    assert result["error_stage"] == "stt_no_speech"
    assert result["error_message"] == "I didn't hear anything. Please try again."
    assert result["tts_spoken"] is True


@pytest.mark.asyncio
async def test_dev_mode_captures_llm_debug(
    pipeline, mock_device_service, monkeypatch
):
    """settings.dev_mode = True -> llm_debug kwarg is a valid JSON string."""
    monkeypatch.setattr("lisa.services.voice_pipeline.settings.dev_mode", True)

    await pipeline.process_text("turn on the bedroom lamp")

    call_kwargs = mock_device_service.execute_command.await_args.kwargs
    llm_debug = call_kwargs["llm_debug"]
    assert isinstance(llm_debug, str)
    parsed = json.loads(llm_debug)
    assert "input_text" in parsed
    assert "devices_seen" in parsed
    assert "decision" in parsed
    assert "usage" in parsed
    assert "stop_reason" in parsed


@pytest.mark.asyncio
async def test_prod_mode_skips_llm_debug(
    pipeline, mock_device_service, monkeypatch
):
    """settings.dev_mode = False -> llm_debug kwarg is None."""
    monkeypatch.setattr("lisa.services.voice_pipeline.settings.dev_mode", False)

    await pipeline.process_text("turn on the bedroom lamp")

    call_kwargs = mock_device_service.execute_command.await_args.kwargs
    assert call_kwargs["llm_debug"] is None
