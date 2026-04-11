"""Tests for STT service with mocked OpenAI client."""

import pytest
from unittest.mock import AsyncMock

import openai

from lisa.services.stt_service import STTService, STTError, STTTimeoutError


def test_stt_service_rejects_empty_api_key():
    with pytest.raises(ValueError, match="API key"):
        STTService(api_key="")


async def test_stt_transcribe_success():
    svc = STTService(api_key="test-key-123")
    svc._client.audio.transcriptions.create = AsyncMock(
        return_value="turn on the bedroom lamp"
    )

    result = await svc.transcribe(b"fake-audio")
    assert result == "turn on the bedroom lamp"


async def test_stt_transcribe_timeout():
    svc = STTService(api_key="test-key-123")
    svc._client.audio.transcriptions.create = AsyncMock(
        side_effect=openai.APITimeoutError(request=None)
    )

    with pytest.raises(STTTimeoutError):
        await svc.transcribe(b"fake")


async def test_stt_transcribe_connection_error():
    svc = STTService(api_key="test-key-123")
    svc._client.audio.transcriptions.create = AsyncMock(
        side_effect=openai.APIConnectionError(request=None)
    )

    with pytest.raises(STTError, match="Cannot reach"):
        await svc.transcribe(b"fake")


async def test_stt_transcribe_empty_result():
    svc = STTService(api_key="test-key-123")
    svc._client.audio.transcriptions.create = AsyncMock(return_value="   ")

    with pytest.raises(STTError, match="No speech detected"):
        await svc.transcribe(b"fake")
