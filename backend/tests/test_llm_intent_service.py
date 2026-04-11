"""Tests for LLM intent service with mocked Anthropic client."""

import pytest
from unittest.mock import AsyncMock, Mock

import anthropic

from lisa.services.llm_intent_service import (
    LLMIntentService,
    LLMError,
    LLMTimeoutError,
    DeviceIntent,
)


SAMPLE_DEVICES = [
    {"device_id": "fake-lamp-1", "alias": "Bedroom Lamp", "is_on": False},
    {"device_id": "fake-lamp-2", "alias": "Living Room Lamp", "is_on": True},
]


def test_llm_service_rejects_empty_api_key():
    with pytest.raises(ValueError, match="API key"):
        LLMIntentService(api_key="")


async def test_llm_parse_intent_returns_device_intent():
    svc = LLMIntentService(api_key="test-key-123")

    tool_block = Mock()
    tool_block.type = "tool_use"
    tool_block.name = "control_device"
    tool_block.input = {
        "device_id": "fake-lamp-1",
        "action": "turn_on",
        "confirmation": "Turning on the bedroom lamp",
    }
    response = Mock()
    response.content = [tool_block]

    svc._client.messages.create = AsyncMock(return_value=response)

    result = await svc.parse_intent("turn on the bedroom lamp", SAMPLE_DEVICES)
    assert isinstance(result, DeviceIntent)
    assert result.device_id == "fake-lamp-1"
    assert result.action == "turn_on"
    assert result.confirmation == "Turning on the bedroom lamp"


async def test_llm_parse_intent_unknown_returns_none():
    svc = LLMIntentService(api_key="test-key-123")

    text_block = Mock()
    text_block.type = "text"
    text_block.text = "I can only control smart home devices."
    response = Mock()
    response.content = [text_block]

    svc._client.messages.create = AsyncMock(return_value=response)

    result = await svc.parse_intent("what is the weather?", SAMPLE_DEVICES)
    assert result is None


async def test_llm_parse_intent_timeout():
    svc = LLMIntentService(api_key="test-key-123")
    svc._client.messages.create = AsyncMock(
        side_effect=anthropic.APITimeoutError(request=None)
    )

    with pytest.raises(LLMTimeoutError):
        await svc.parse_intent("turn on the lamp", SAMPLE_DEVICES)


async def test_llm_parse_intent_connection_error():
    svc = LLMIntentService(api_key="test-key-123")
    svc._client.messages.create = AsyncMock(
        side_effect=anthropic.APIConnectionError(request=None)
    )

    with pytest.raises(LLMError, match="Cannot reach"):
        await svc.parse_intent("turn on the lamp", SAMPLE_DEVICES)


async def test_llm_device_context_in_system_prompt():
    svc = LLMIntentService(api_key="test-key-123")

    text_block = Mock()
    text_block.type = "text"
    text_block.text = "OK"
    response = Mock()
    response.content = [text_block]

    svc._client.messages.create = AsyncMock(return_value=response)

    await svc.parse_intent("turn on the lamp", SAMPLE_DEVICES)

    call_kwargs = svc._client.messages.create.call_args[1]
    system_prompt = call_kwargs["system"]
    assert "fake-lamp-1" in system_prompt
    assert "Bedroom Lamp" in system_prompt
    assert "fake-lamp-2" in system_prompt
    assert "Living Room Lamp" in system_prompt
