"""OpenAI Whisper API wrapper for speech-to-text. Per D-10, VOICE-03."""

import io

import httpx
import openai


class STTError(Exception):
    """Base error for STT failures."""

    pass


class STTTimeoutError(STTError):
    """Raised when STT exceeds timeout. Per D-17."""

    pass


class STTNoSpeechError(STTError):
    """Raised when STT detects no speech in audio."""

    pass


class STTService:
    """Transcribe audio bytes to text via OpenAI Whisper API."""

    def __init__(self, api_key: str, model: str = "whisper-1", timeout: float = 3.0):
        if not api_key:
            raise ValueError("OpenAI API key is required for STT service")
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            timeout=httpx.Timeout(timeout, connect=5.0),
        )
        self._model = model

    async def transcribe(self, audio_bytes: bytes, format: str = "wav") -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio data.
            format: Audio format (wav, mp3, etc.).

        Returns:
            Transcribed text string.

        Raises:
            STTTimeoutError: If the API call exceeds the configured timeout.
            STTError: On connection failure, API error, or empty result.
        """
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio.{format}"

        try:
            transcript = await self._client.audio.transcriptions.create(
                model=self._model,
                file=audio_file,
                response_format="text",
            )
        except openai.APITimeoutError:
            raise STTTimeoutError("STT request timed out")
        except openai.APIConnectionError:
            raise STTError("Cannot reach speech recognition service")
        except openai.APIError as e:
            raise STTError(f"STT failed: {e}")

        result = transcript.strip()
        if not result:
            raise STTNoSpeechError("No speech detected in audio")
        return result
