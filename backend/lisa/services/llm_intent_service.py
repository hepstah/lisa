"""Anthropic Claude tool_use wrapper for intent parsing. Per D-09, D-11, VOICE-04."""

from dataclasses import dataclass
from typing import Optional

import anthropic
import httpx


class LLMError(Exception):
    """Base error for LLM intent failures."""

    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM exceeds timeout. Per D-18."""

    pass


@dataclass
class DeviceIntent:
    """Structured intent extracted from user speech."""

    device_id: str
    action: str  # "turn_on" or "turn_off"
    confirmation: str  # e.g. "Turning on the bedroom lamp"


DEVICE_CONTROL_TOOL = {
    "name": "control_device",
    "description": (
        "Control a smart home device by turning it on or off. "
        "Use this when the user asks to control a device. "
        "Only use device_ids from the provided device list."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "device_id": {
                "type": "string",
                "description": "The exact device_id from the available devices list",
            },
            "action": {
                "type": "string",
                "enum": ["turn_on", "turn_off"],
                "description": "The action to perform",
            },
            "confirmation": {
                "type": "string",
                "description": "A short spoken confirmation message for the user",
            },
        },
        "required": ["device_id", "action", "confirmation"],
    },
}


class LLMIntentService:
    """Parse user text into device control intents via Anthropic Claude."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5",
        timeout: float = 3.0,
    ):
        if not api_key:
            raise ValueError(
                "Anthropic API key is required for LLM intent service"
            )
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=httpx.Timeout(timeout, connect=5.0),
        )
        self._model = model

    async def parse_intent(
        self, text: str, devices: list[dict]
    ) -> Optional[DeviceIntent]:
        """Parse user text into a DeviceIntent or None for unknown intents.

        Args:
            text: Transcribed user speech.
            devices: List of dicts with device_id, alias, is_on keys.

        Returns:
            DeviceIntent if a device control action was identified, None otherwise.

        Raises:
            LLMTimeoutError: If the API call exceeds the configured timeout.
            LLMError: On connection failure or API error.
        """
        device_list = "\n".join(
            f"- device_id: {d['device_id']}, alias: {d['alias']}, is_on: {d['is_on']}"
            for d in devices
        )
        system_prompt = (
            "You are Lisa, a smart home voice assistant. "
            "You control devices for the user. "
            f"Available devices:\n{device_list}\n\n"
            "If the user's request does not match a device control action, "
            "do NOT call the tool."
        )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=200,
                system=system_prompt,
                tools=[DEVICE_CONTROL_TOOL],
                tool_choice={"type": "auto"},
                messages=[{"role": "user", "content": text}],
            )
        except anthropic.APITimeoutError:
            raise LLMTimeoutError("LLM request timed out")
        except anthropic.APIConnectionError:
            raise LLMError("Cannot reach intent processing service")
        except anthropic.APIError as e:
            raise LLMError(f"Intent parsing failed: {e}")

        for block in response.content:
            if block.type == "tool_use" and block.name == "control_device":
                return DeviceIntent(
                    device_id=block.input["device_id"],
                    action=block.input["action"],
                    confirmation=block.input["confirmation"],
                )
        return None
