"""Tests for LLM intent service with mocked Anthropic client."""

import pytest
from unittest.mock import AsyncMock, Mock

import anthropic

from lisa.services.llm_intent_service import (
    LLMIntentService,
    LLMError,
    LLMTimeoutError,
    DeviceIntent,
    IntentResult,
)


SAMPLE_DEVICES = [
    {"device_id": "fake-lamp-1", "alias": "Bedroom Lamp", "is_on": False},
    {"device_id": "fake-lamp-2", "alias": "Living Room Lamp", "is_on": True},
]


def _mock_response(content, stop_reason="end_turn", input_tokens=50, output_tokens=25):
    """Build a Mock response with content blocks + usage + stop_reason."""
    response = Mock()
    response.content = content
    usage = Mock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    response.usage = usage
    response.stop_reason = stop_reason
    return response


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
    response = _mock_response([tool_block])

    svc._client.messages.create = AsyncMock(return_value=response)

    result = await svc.parse_intent("turn on the bedroom lamp", SAMPLE_DEVICES)
    assert isinstance(result, IntentResult)
    assert isinstance(result.intent, DeviceIntent)
    assert result.intent.device_id == "fake-lamp-1"
    assert result.intent.action == "turn_on"
    assert result.intent.confirmation == "Turning on the bedroom lamp"


async def test_llm_parse_intent_unknown_returns_none():
    svc = LLMIntentService(api_key="test-key-123")

    text_block = Mock()
    text_block.type = "text"
    text_block.text = "I can only control smart home devices."
    response = _mock_response([text_block])

    svc._client.messages.create = AsyncMock(return_value=response)

    result = await svc.parse_intent("what is the weather?", SAMPLE_DEVICES)
    assert isinstance(result, IntentResult)
    assert result.intent is None


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
    response = _mock_response([text_block])

    svc._client.messages.create = AsyncMock(return_value=response)

    await svc.parse_intent("turn on the lamp", SAMPLE_DEVICES)

    call_kwargs = svc._client.messages.create.call_args[1]
    system_prompt = call_kwargs["system"]
    assert "fake-lamp-1" in system_prompt
    assert "Bedroom Lamp" in system_prompt
    assert "fake-lamp-2" in system_prompt
    assert "Living Room Lamp" in system_prompt


async def test_parse_intent_returns_debug_on_tool_use():
    """Tool-use response populates decision with tool_used=True + device fields."""
    svc = LLMIntentService(api_key="test-key-123")

    tool_block = Mock()
    tool_block.type = "tool_use"
    tool_block.name = "control_device"
    tool_block.input = {
        "device_id": "fake-lamp-1",
        "action": "turn_on",
        "confirmation": "Turning on the bedroom lamp",
    }
    response = _mock_response(
        [tool_block], stop_reason="tool_use", input_tokens=412, output_tokens=23
    )
    svc._client.messages.create = AsyncMock(return_value=response)

    result = await svc.parse_intent("turn on the bedroom lamp", SAMPLE_DEVICES)

    assert isinstance(result, IntentResult)
    assert isinstance(result.intent, DeviceIntent)
    assert result.debug["input_text"] == "turn on the bedroom lamp"
    assert result.debug["devices_seen"] == SAMPLE_DEVICES
    assert result.debug["decision"]["tool_used"] is True
    assert result.debug["decision"]["device_id"] == "fake-lamp-1"
    assert result.debug["decision"]["action"] == "turn_on"
    assert result.debug["decision"]["confirmation"] == "Turning on the bedroom lamp"
    assert result.debug["usage"]["input_tokens"] == 412
    assert result.debug["usage"]["output_tokens"] == 23
    assert result.debug["stop_reason"] == "tool_use"


async def test_parse_intent_returns_debug_on_text_response():
    """Plain text response populates decision with tool_used=False + text."""
    svc = LLMIntentService(api_key="test-key-123")

    text_block = Mock()
    text_block.type = "text"
    text_block.text = "I'm a smart home assistant and can only control devices."
    response = _mock_response(
        [text_block], stop_reason="end_turn", input_tokens=120, output_tokens=18
    )
    svc._client.messages.create = AsyncMock(return_value=response)

    result = await svc.parse_intent("how are you", SAMPLE_DEVICES)

    assert isinstance(result, IntentResult)
    assert result.intent is None
    assert result.debug["input_text"] == "how are you"
    assert result.debug["devices_seen"] == SAMPLE_DEVICES
    assert result.debug["decision"]["tool_used"] is False
    assert (
        result.debug["decision"]["text"]
        == "I'm a smart home assistant and can only control devices."
    )
    assert result.debug["usage"]["input_tokens"] == 120
    assert result.debug["usage"]["output_tokens"] == 18
    assert result.debug["stop_reason"] == "end_turn"
