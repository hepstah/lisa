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


@dataclass
class IntentResult:
    """Intent parse result plus a dev-mode debug blob.

    debug is always populated, whether intent is present or not. The voice
    pipeline only persists it when settings.dev_mode is True.
    """

    intent: Optional[DeviceIntent]
    debug: dict


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
    ) -> IntentResult:
        """Parse user text into an IntentResult.

        Args:
            text: Transcribed user speech.
            devices: List of dicts with device_id, alias, is_on keys.

        Returns:
            IntentResult with .intent (DeviceIntent or None) and .debug dict.
            The debug dict is always populated; the voice pipeline decides
            whether to persist it based on settings.dev_mode.

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

        intent: Optional[DeviceIntent] = None
        decision: dict = {}
        for block in response.content:
            if block.type == "tool_use" and block.name == "control_device":
                intent = DeviceIntent(
                    device_id=block.input["device_id"],
                    action=block.input["action"],
                    confirmation=block.input["confirmation"],
                )
                decision = {
                    "tool_used": True,
                    "device_id": intent.device_id,
                    "action": intent.action,
                    "confirmation": intent.confirmation,
                }
                break

        if intent is None:
            text_content = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    text_content = getattr(block, "text", "") or ""
                    break
            decision = {"tool_used": False, "text": text_content}

        usage_obj = getattr(response, "usage", None)
        usage = {
            "input_tokens": getattr(usage_obj, "input_tokens", 0) if usage_obj else 0,
            "output_tokens": getattr(usage_obj, "output_tokens", 0) if usage_obj else 0,
        }
        stop_reason = getattr(response, "stop_reason", None)

        debug = {
            "input_text": text,
            "devices_seen": devices,
            "decision": decision,
            "usage": usage,
            "stop_reason": stop_reason,
        }

        return IntentResult(intent=intent, debug=debug)
