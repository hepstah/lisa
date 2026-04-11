"""Voice pipeline orchestrator: STT -> LLM intent -> DeviceService -> TTS.

Every code path calls TTS.speak() per ERR-01 (no silent failures).
Cloud calls enforce 3-second timeouts per ERR-03 (via service constructors).
"""

import logging

from lisa.services.stt_service import STTError, STTTimeoutError, STTService
from lisa.services.llm_intent_service import (
    LLMError,
    LLMTimeoutError,
    LLMIntentService,
)
from lisa.services.tts_service import TTSService
from lisa.services.device_service import DeviceService

# Spoken error messages per D-17 through D-20
MSG_STT_TIMEOUT = "Sorry, I could not understand that. Please try again."
MSG_LLM_TIMEOUT = "I'm having trouble processing that right now."
MSG_NO_INTERNET = "Voice understanding is temporarily unavailable."
MSG_UNKNOWN_INTENT = (
    "I didn't understand that. Try saying something like: turn on the bedroom lamp."
)
MSG_DEVICE_ERROR = "I had trouble controlling that device. Please try again."
MSG_DEVICE_UNREACHABLE = "That device doesn't seem to be reachable right now."


class VoicePipeline:
    """Chains STT -> LLM -> DeviceService -> TTS into a single voice command flow."""

    def __init__(
        self,
        stt: STTService | None,
        llm: LLMIntentService,
        tts: TTSService,
        device_service: DeviceService,
    ):
        self._stt = stt
        self._llm = llm
        self._tts = tts
        self._device_service = device_service
        self._log = logging.getLogger("lisa.voice_pipeline")

    async def process_text(self, text: str, source: str = "voice") -> dict:
        """Process transcribed text through LLM -> DeviceService -> TTS.

        Entry point for both voice (after STT) and text injection (D-13).
        Every outcome calls TTS.speak() per ERR-01.
        """
        # Step 1: Get device context
        states = await self._device_service.get_all_states()
        device_context = [
            {"device_id": s.device_id, "alias": s.alias, "is_on": s.is_on}
            for s in states
        ]

        # Step 2: Parse intent via LLM
        try:
            intent = await self._llm.parse_intent(text, device_context)
        except LLMTimeoutError:
            self._log.warning("LLM timeout for input: %s", text)
            await self._tts.speak(MSG_LLM_TIMEOUT)
            return {
                "status": "error",
                "error_stage": "llm",
                "error_message": MSG_LLM_TIMEOUT,
                "raw_input": text,
                "tts_spoken": True,
            }
        except LLMError:
            self._log.warning("LLM connection error for input: %s", text)
            await self._tts.speak(MSG_NO_INTERNET)
            return {
                "status": "error",
                "error_stage": "llm",
                "error_message": MSG_NO_INTERNET,
                "raw_input": text,
                "tts_spoken": True,
            }

        # Step 3: Handle unknown intent
        if intent is None:
            self._log.info("Unknown intent for input: %s", text)
            await self._tts.speak(MSG_UNKNOWN_INTENT)
            return {
                "status": "rejected",
                "error_stage": "intent",
                "error_message": MSG_UNKNOWN_INTENT,
                "raw_input": text,
                "tts_spoken": True,
            }

        # Step 4: Execute device command
        new_state, log = await self._device_service.execute_command(
            device_id=intent.device_id,
            action=intent.action,
            source=source,
            raw_input=text,
        )

        # Step 5: Speak result -- every outcome gets TTS per ERR-01
        if log.get("status") == "success":
            await self._tts.speak(intent.confirmation)
        elif log.get("error_stage") == "device_unreachable":
            await self._tts.speak(MSG_DEVICE_UNREACHABLE)
        else:
            await self._tts.speak(log.get("error_message", MSG_DEVICE_ERROR))

        return {**log, "tts_spoken": True}

    async def process_audio(self, audio_bytes: bytes) -> dict:
        """Process raw audio through STT -> process_text pipeline.

        Entry point for the full voice path (Pi with microphone).
        """
        if self._stt is None:
            raise RuntimeError(
                "STT service not available -- use process_text for dev mode"
            )

        try:
            text = await self._stt.transcribe(audio_bytes)
        except STTTimeoutError:
            self._log.warning("STT timeout")
            await self._tts.speak(MSG_STT_TIMEOUT)
            return {
                "status": "error",
                "error_stage": "stt",
                "error_message": MSG_STT_TIMEOUT,
                "tts_spoken": True,
            }
        except STTError:
            self._log.warning("STT connection error")
            await self._tts.speak(MSG_NO_INTERNET)
            return {
                "status": "error",
                "error_stage": "stt",
                "error_message": MSG_NO_INTERNET,
                "tts_spoken": True,
            }

        return await self.process_text(text, source="voice")
