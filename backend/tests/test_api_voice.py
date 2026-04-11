"""API integration tests for voice pipeline text command path."""

import pytest
from unittest.mock import AsyncMock, patch

from lisa.api import commands


@pytest.mark.asyncio
async def test_text_command_with_voice_pipeline_success(client):
    """Text command routes through voice pipeline when available."""
    mock_pipeline = AsyncMock()
    mock_pipeline.process_text = AsyncMock(
        return_value={
            "id": 1,
            "status": "success",
            "device_id": "fake-lamp-1",
            "action": "turn_on",
            "tts_spoken": True,
        }
    )

    original = commands.voice_pipeline
    commands.voice_pipeline = mock_pipeline
    try:
        resp = await client.post(
            "/api/commands/text",
            json={"text": "turn on the bedroom lamp"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["tts_spoken"] is True
        mock_pipeline.process_text.assert_awaited_once_with(
            "turn on the bedroom lamp", source="dashboard"
        )
    finally:
        commands.voice_pipeline = original


@pytest.mark.asyncio
async def test_text_command_falls_back_without_pipeline(client):
    """Without voice pipeline, falls back to Phase 1 regex parser."""
    original = commands.voice_pipeline
    commands.voice_pipeline = None
    try:
        resp = await client.post(
            "/api/commands/text",
            json={"text": "turn on the bedroom lamp"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["device_id"] == "fake-lamp-1"
    finally:
        commands.voice_pipeline = original


@pytest.mark.asyncio
async def test_text_command_with_pipeline_unknown_intent(client):
    """Voice pipeline returns rejected for unknown intent."""
    mock_pipeline = AsyncMock()
    mock_pipeline.process_text = AsyncMock(
        return_value={
            "status": "rejected",
            "error_stage": "intent",
            "error_message": "I didn't understand that.",
            "raw_input": "what is the weather?",
            "tts_spoken": True,
        }
    )

    original = commands.voice_pipeline
    commands.voice_pipeline = mock_pipeline
    try:
        resp = await client.post(
            "/api/commands/text",
            json={"text": "what is the weather?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["tts_spoken"] is True
    finally:
        commands.voice_pipeline = original
