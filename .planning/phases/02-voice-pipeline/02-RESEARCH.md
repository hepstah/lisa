# Phase 2: Voice Pipeline - Research

**Researched:** 2026-04-11
**Domain:** Voice pipeline -- wake word detection, cloud STT, cloud LLM intent parsing, local TTS
**Confidence:** HIGH

## Summary

Phase 2 builds the voice pipeline: wake word detection (openWakeWord), audio capture with VAD, cloud STT (OpenAI Whisper API), cloud LLM intent parsing (Anthropic Claude Haiku 4.5 via tool_use), and local TTS (Piper). The pipeline must produce spoken feedback for every outcome including all error paths. Because this is a Windows dev machine with no microphone, the entire pipeline must be testable via text injection -- wake word and audio capture are Pi-only; dev mode starts at the STT/LLM stage.

The existing codebase already has the downstream integration target: `DeviceService.execute_command()` accepts `(device_id, action, source, raw_input)` and handles validation, execution, and logging. The text command parser in `commands.py` is a simple regex-based parser that Phase 2's LLM intent parser will eventually supplement (both feeding into the same DeviceService).

**Primary recommendation:** Build four independent service modules (STT, LLM intent, TTS, pipeline orchestrator) that are individually testable, then wire them together in a pipeline orchestrator. Dev mode bypasses wake word and audio capture entirely -- text goes straight to LLM intent parsing. All cloud calls use httpx/SDK async clients with 3-second timeouts and explicit error responses.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-09:** Claude API (claude-haiku-4-5) is the LLM for intent parsing -- fast, cheap, excellent structured output via tool_use
- **D-10:** OpenAI Whisper API is the STT provider -- $0.006/min, best accuracy (per research recommendation)
- **D-11:** Intent response format is structured JSON via tool_use -- LLM returns {device_id, action}, no parsing needed
- **D-12:** API keys configured as LISA_OPENAI_API_KEY and LISA_ANTHROPIC_API_KEY env vars (same LISA_ prefix pattern as Phase 1)
- **D-13:** Text injection via existing DASH-04 bypasses wake word + STT -- text commands go directly to LLM intent parsing in dev mode
- **D-14:** TTS output saves to .wav file in dev mode -- log what would be spoken, save audio for manual playback
- **D-15:** Wake word skipped in dev mode -- command injection starts at STT/LLM stage. Wake word only runs on Pi with real mic
- **D-16:** Each pipeline stage testable independently -- STT with .wav file, LLM with text, TTS with text. Integration test chains with mocked inputs
- **D-17:** Cloud STT timeout is 3 seconds -- immediate spoken fallback: "Sorry, I could not understand that. Please try again."
- **D-18:** Cloud LLM timeout is 3 seconds -- spoken fallback: "I'm having trouble processing that right now."
- **D-19:** No internet response: "Voice understanding is temporarily unavailable" -- honest about cloud dependency
- **D-20:** Unknown intent response: "I didn't understand that. Try saying something like: turn on the bedroom lamp" -- gives example

### Claude's Discretion
- Wake word model selection and threshold tuning for openWakeWord
- Audio capture buffer size and VAD silence threshold
- Piper TTS voice model selection
- Pipeline threading/async architecture (audio in dedicated thread per INFRA-04)
- Retry strategy for transient cloud failures (if any)

### Deferred Ideas (OUT OF SCOPE)
- Wake word threshold calibration UI (ADV-02) -- v2
- Custom wake word training (ADV-03) -- v2
- "Working on it" audio cue for slow responses (CONV-02) -- v2
- Streaming STT for faster response (Deepgram alternative) -- v2
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VOICE-01 | Detect wake phrase "Hey Lisa" locally on Pi with acceptable false-trigger rate | openWakeWord library with custom-trained or "hey_jarvis"-based model; 0.5 threshold default; Pi-only (skipped in dev mode per D-15) |
| VOICE-02 | Capture short utterance after wake word until silence (VAD) | Audio capture in dedicated thread; 16kHz 16-bit PCM; webrtcvad or energy-based silence detection; Pi-only |
| VOICE-03 | Send captured audio to cloud STT and return transcription | OpenAI Whisper API (whisper-1 or gpt-4o-mini-transcribe); WAV format; 3s timeout per D-17 |
| VOICE-04 | Send transcribed text with device context to cloud LLM, receive structured JSON intent | Anthropic claude-haiku-4-5 with tool_use; forced tool_choice; {device_id, action, confirmation} schema |
| VOICE-05 | Speak confirmation or error response locally via Piper TTS | piper-tts Python library; en_US-lessac-medium voice; WAV output; dev mode saves to file per D-14 |
| ERR-01 | Produce spoken feedback for every failure mode | TTS service called on every error path with specific messages per D-17 through D-20 |
| ERR-03 | Set aggressive timeouts (5s) for cloud calls with immediate spoken fallback | 3s timeouts (tighter than 5s requirement) per D-17/D-18; httpx timeout or SDK timeout parameter |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Dev-mode trigger paths preferred over hardware wake-word implementation
- Fake/stub device adapters over broad protocol support
- Typed transcript injection over mandatory live audio
- Explicit contracts over speculative abstractions
- One working integration over an extensible framework
- Straightforward implementations over clever or highly configurable ones
- No broad architectural rewrites or opportunistic cleanup
- No introducing abstractions before a second real use case exists
- Python managed by uv (not system Python); backend on port 8001
- Async Python with FastAPI; pydantic-settings for configuration
- Module-level service injection pattern (lifespan sets service on router modules)

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.94.0 | Claude API client for LLM intent parsing | Official Anthropic Python SDK; async support; tool_use built-in |
| openai | 2.31.0 | OpenAI Whisper API client for STT | Official OpenAI Python SDK; async support; audio transcription |
| piper-tts | 1.4.2 | Local neural TTS engine | Fast, local, no cloud dependency for output; GPL-3.0; Windows + Linux + macOS wheels |
| openwakeword | 0.6.0 | Wake word detection | Open-source; pre-trained models; custom training; ~100MB RAM on Pi |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| onnxruntime | (dep of openwakeword) | ML model inference runtime | Automatically installed with openwakeword |
| httpx | 0.28.0+ | Already in project (test dep) | Used by openai/anthropic SDKs internally; also good for direct HTTP if needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| whisper-1 model | gpt-4o-mini-transcribe | Newer, possibly better quality; same $0.003-0.006/min; worth trying |
| anthropic SDK | Raw httpx calls | SDK handles retries, types, streaming; no reason to go lower-level |
| piper-tts | OpenAI TTS API | Higher quality but adds latency + cost + cloud dependency for output |

**Installation (add to pyproject.toml dependencies):**
```bash
uv add anthropic openai piper-tts openwakeword
```

**Version verification:**
- anthropic: 0.94.0 (verified via uv pip install --dry-run 2026-04-11)
- openai: 2.31.0 (verified via uv pip install --dry-run 2026-04-11)
- piper-tts: 1.4.2 (verified via PyPI 2026-04-02 release)
- openwakeword: 0.6.0 (verified via PyPI/GitHub 2024-02-11 release -- stable, no major updates since)

## Architecture Patterns

### Recommended Project Structure
```
backend/lisa/
  services/
    stt_service.py          # OpenAI Whisper API wrapper
    llm_intent_service.py   # Anthropic Claude tool_use intent parser
    tts_service.py          # Piper TTS wrapper (+ dev-mode file output)
    voice_pipeline.py       # Orchestrator: chains STT -> LLM -> TTS
    device_service.py       # (existing) downstream target
  voice/
    wake_word.py            # openWakeWord wrapper (Pi-only)
    audio_capture.py        # Mic capture + VAD (Pi-only)
  config.py                 # (extend existing Settings with API keys + voice config)
```

### Pattern 1: Service Layer with Protocol/Interface
**What:** Each pipeline stage is a standalone async service class with a clear interface. Services are created in the FastAPI lifespan and injected into the pipeline orchestrator.
**When to use:** Always -- this matches the existing DeviceService pattern.
**Example:**
```python
# Source: Matches existing DeviceService pattern in backend/lisa/services/
class STTService:
    """Transcribe audio bytes to text via OpenAI Whisper API."""

    def __init__(self, api_key: str, timeout: float = 3.0):
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._timeout = timeout

    async def transcribe(self, audio_bytes: bytes, format: str = "wav") -> str:
        """Returns transcribed text. Raises STTError on timeout/failure."""
        ...
```

### Pattern 2: Dev-Mode Bypass at Pipeline Level
**What:** The pipeline orchestrator checks `settings.dev_mode` and skips wake word + audio capture stages. In dev mode, text input goes directly to the LLM intent stage. TTS writes to file instead of playing audio.
**When to use:** Always in dev mode (D-13, D-14, D-15).
**Example:**
```python
class VoicePipeline:
    async def process_text(self, text: str, source: str = "voice") -> dict:
        """Process text through LLM intent -> device execution -> TTS response.
        Used by both voice (after STT) and dev-mode text injection."""
        intent = await self._llm_intent.parse_intent(text, self._device_context)
        if intent is None:
            await self._tts.speak(UNKNOWN_INTENT_MSG)
            return {"status": "rejected", "error": "unknown_intent"}
        result = await self._device_service.execute_command(
            device_id=intent["device_id"],
            action=intent["action"],
            source=source,
            raw_input=text,
        )
        await self._tts.speak(intent.get("confirmation", "Done."))
        return result
```

### Pattern 3: Forced Tool Use for Reliable Structured Output
**What:** Use Anthropic `tool_choice: {"type": "tool", "name": "control_device"}` to force Claude to always return structured JSON via the tool_use mechanism. No free-text parsing needed.
**When to use:** Every LLM intent call.
**Example:**
```python
# Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
DEVICE_CONTROL_TOOL = {
    "name": "control_device",
    "description": "Control a smart home device. Call this when the user wants to turn a device on or off.",
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
    "strict": True,
}
```

### Pattern 4: Error-First Pipeline Design
**What:** Every pipeline stage has explicit error handling that results in a spoken TTS response. Errors are caught at the orchestrator level and routed to TTS before being logged.
**When to use:** Every cloud call, every device execution.
**Critical insight:** The user hears feedback for EVERY outcome. Silence is never acceptable.

### Anti-Patterns to Avoid
- **Blocking audio on the event loop:** Audio capture and wake word detection MUST run in dedicated threads, never on the asyncio loop. Use `asyncio.run_in_executor()` or a thread with a queue.
- **Parsing LLM free text:** Do NOT ask the LLM to return JSON as text and then parse it. Use tool_use with forced tool_choice. This eliminates JSON parsing errors entirely.
- **Shared mutable state between pipeline stages:** Each service should receive immutable inputs and return results. No shared state between STT, LLM, and TTS services.
- **Swallowing errors silently:** Every except block must either produce a spoken error OR re-raise. Silent failures violate ERR-01.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Speech-to-text | Custom whisper integration | `openai.AsyncOpenAI().audio.transcriptions.create()` | SDK handles auth, retries, file upload, response parsing |
| LLM structured output | JSON response parsing | Anthropic tool_use with `strict: True` | Guaranteed schema conformance; no regex/JSON parsing |
| Text-to-speech | Raw audio synthesis | `piper-tts` PiperVoice.synthesize_wav() | Handles phonemization, ONNX inference, WAV encoding |
| Wake word detection | Custom ML model | openWakeWord pre-trained + custom training | Trained on 100K+ synthetic clips; shared feature backbone |
| Async HTTP timeout | Manual timer + cancel | SDK timeout params or httpx.Timeout | Race conditions in manual timeout code |

**Key insight:** Every pipeline stage has a well-tested library. The value is in the orchestration and error handling between stages, not in reimplementing any individual stage.

## Common Pitfalls

### Pitfall 1: TTS Echo Triggering Wake Word
**What goes wrong:** Piper TTS plays through speaker, openWakeWord hears it, triggers a new capture. Lisa enters a conversation with herself.
**Why it happens:** Microphone picks up speaker output in close physical proximity.
**How to avoid:** Mute wake word detection while TTS is playing. Add a cooldown period (500ms-1s) after TTS completes before re-enabling detection.
**Warning signs:** Random activations after every TTS response in Pi testing.

### Pitfall 2: LLM Hallucinating Device Names
**What goes wrong:** User says "turn on the bedroom lamp" but LLM returns `device_id: "bedroom_light"` (wrong ID) or invents an action like `"dim_to_50"`.
**Why it happens:** LLM generates plausible-sounding but incorrect device identifiers.
**How to avoid:** Pass exact device_ids and aliases in the system prompt. Use `strict: True` on the tool schema with enum constraints where possible. Validate LLM output against known device IDs (existing allowlist) before execution.
**Warning signs:** "Device not found" errors despite correct user speech.

### Pitfall 3: Cloud Latency Blowing the Budget
**What goes wrong:** STT takes 1.5s + LLM takes 2s = 3.5s before TTS even starts. User thinks nothing happened.
**Why it happens:** Serial pipeline with variable cloud latency.
**How to avoid:** Measure each stage independently. Use 3s timeouts per D-17/D-18. Choose claude-haiku-4-5 (fast model). Start TTS as soon as confirmation text is available (don't wait for device response).
**Warning signs:** End-to-end > 3s consistently in testing.

### Pitfall 4: API Key Configuration Errors
**What goes wrong:** Service starts but fails on first voice command because API keys are missing or invalid. Error is only visible in logs, not spoken to user.
**Why it happens:** API keys checked only when first used, not at startup.
**How to avoid:** Validate API key presence (not validity) at startup. Log a clear warning if keys are missing. In dev mode, allow operation without keys if only testing TTS or other non-cloud stages.
**Warning signs:** First command after startup always fails.

### Pitfall 5: Piper Voice Model Not Downloaded
**What goes wrong:** TTS service fails because the .onnx voice model file is not present on disk.
**Why it happens:** Piper models must be downloaded separately from the library.
**How to avoid:** Include model download in setup instructions. Check for model file at startup and provide a clear error message if missing. Consider a setup script or first-run download.
**Warning signs:** TTS works in CI (model cached) but fails on fresh install.

### Pitfall 6: openWakeWord Missing "Hey Lisa" Model
**What goes wrong:** There is no pre-trained "hey lisa" model in openWakeWord. Using "hey jarvis" as a placeholder does not detect "hey lisa".
**Why it happens:** openWakeWord ships with ~6 pre-trained models (alexa, hey_mycroft, hey_jarvis, hey_rhasspy, weather, timers). "Hey Lisa" is not among them.
**How to avoid:** For v1 dev/testing, use "hey jarvis" as a stand-in to prove the pipeline works. Training a custom "hey lisa" model requires the openWakeWord training notebook (Google Colab, ~10 min on T4 GPU) and is a separate task. Per CONTEXT.md, custom wake word training is deferred to v2 (ADV-03), but a basic trained model is needed for VOICE-01.
**Warning signs:** Wake word never triggers, or triggers on wrong phrases.

## Code Examples

Verified patterns from official sources:

### OpenAI Whisper API -- Transcribe Audio
```python
# Source: https://developers.openai.com/api/docs/guides/speech-to-text
import io
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="...")

async def transcribe(audio_bytes: bytes) -> str:
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.wav"  # SDK needs a .name attribute
    transcript = await client.audio.transcriptions.create(
        model="whisper-1",  # or "gpt-4o-mini-transcribe" for newer model
        file=audio_file,
        response_format="text",
    )
    return transcript
```

### Anthropic Claude tool_use -- Intent Parsing
```python
# Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key="...")

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
            },
            "confirmation": {
                "type": "string",
                "description": "A short natural-language confirmation for the user, e.g. 'Turning off the bedroom lamp'",
            },
        },
        "required": ["device_id", "action", "confirmation"],
    },
    "strict": True,
}

async def parse_intent(text: str, devices: list[dict]) -> dict | None:
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

    response = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        system=system_prompt,
        tools=[DEVICE_CONTROL_TOOL],
        tool_choice={"type": "tool", "name": "control_device"},
        messages=[{"role": "user", "content": text}],
    )

    # Extract tool_use block
    for block in response.content:
        if block.type == "tool_use":
            return block.input  # {"device_id": ..., "action": ..., "confirmation": ...}
    return None
```

### Piper TTS -- Synthesize to WAV
```python
# Source: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md
import wave
from piper import PiperVoice

voice = PiperVoice.load("/path/to/en_US-lessac-medium.onnx")

def synthesize_to_file(text: str, output_path: str):
    with wave.open(output_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

# For streaming (Pi with speaker):
def synthesize_streaming(text: str):
    for chunk in voice.synthesize(text):
        # chunk.sample_rate, chunk.sample_width, chunk.sample_channels
        # chunk.audio_int16_bytes -- raw PCM data
        play_audio(chunk.audio_int16_bytes)
```

### openWakeWord -- Detection Loop
```python
# Source: https://github.com/dscripka/openWakeWord/blob/main/README.md
import openwakeword
from openwakeword.model import Model

# Download pre-trained models (run once)
openwakeword.utils.download_models()

# Load model(s)
model = Model(
    wakeword_models=["hey_jarvis"],  # or path to custom "hey_lisa" model
    # inference_framework="onnx",  # default
)

# Process 80ms frames of 16kHz 16-bit PCM audio
frame = get_audio_frame()  # 1280 samples = 80ms at 16kHz
prediction = model.predict(frame)

# prediction is dict: {"hey_jarvis": 0.87, ...}
# Threshold: > 0.5 is positive detection (default)
```

### Settings Extension
```python
# Extend existing backend/lisa/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing fields ...
    dev_mode: bool = True
    db_path: str = "lisa.db"
    kasa_username: str = ""
    kasa_password: str = ""
    host: str = "0.0.0.0"
    port: int = 8001

    # Phase 2: Voice pipeline
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5"
    stt_model: str = "whisper-1"
    stt_timeout: float = 3.0
    llm_timeout: float = 3.0
    tts_model_path: str = ""  # Path to Piper .onnx voice model
    tts_output_dir: str = "tts_output"  # Dev mode: save WAV files here

    model_config = {"env_prefix": "LISA_", "env_file": ".env"}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| whisper-1 only | gpt-4o-transcribe and gpt-4o-mini-transcribe available | Late 2025 | Newer models may be faster/more accurate; same pricing ($0.003-0.006/min) |
| JSON text output from LLM | tool_use with strict: True | 2024+ | Guaranteed schema conformance; eliminates JSON parsing errors |
| Piper under rhasspy org | Moved to OHF-Voice/piper1-gpl | Oct 2025 | Same pip package (piper-tts), new GitHub org; looking for maintainers |
| openWakeWord tflite only | ONNX + tflite support | 2024 | ONNX preferred on Windows (no tflite-runtime needed) |

**Deprecated/outdated:**
- Snowboy: Discontinued. Do not use.
- espeak-ng: Robotic quality. Replaced by Piper for neural TTS.
- Free-text JSON parsing from LLM: Use tool_use instead. Eliminates entire class of parsing bugs.

## Open Questions

1. **"Hey Lisa" wake word model**
   - What we know: No pre-trained model exists. Training requires Google Colab with openWakeWord notebook (~10 min on T4 GPU). CONTEXT.md defers custom training (ADV-03) to v2.
   - What's unclear: Whether to train a basic model now for VOICE-01, or use "hey jarvis" as a development stand-in and defer the custom model.
   - Recommendation: Use "hey jarvis" as dev stand-in. Train a basic "hey lisa" model as a separate targeted task for Pi deployment. VOICE-01 requires "Hey Lisa" specifically, so this must be done before the phase is considered complete for Pi, but the pipeline can be built and tested without it.

2. **Piper voice model selection**
   - What we know: en_US-lessac-medium is a well-regarded voice. Models must be downloaded separately (~30-50MB per model).
   - What's unclear: Exact model quality and whether "medium" vs "high" makes a noticeable difference on Pi.
   - Recommendation: Use en_US-lessac-medium. It balances quality and speed. Download mechanism should be documented in setup instructions.

3. **STT model choice: whisper-1 vs gpt-4o-mini-transcribe**
   - What we know: Both are available. gpt-4o-mini-transcribe is newer, potentially better quality. whisper-1 is proven. Both cost $0.003-0.006/min.
   - What's unclear: Real-world latency comparison for short utterances.
   - Recommendation: Start with whisper-1 (proven, stable). Make the model configurable (stt_model setting) so switching is a one-line change.

4. **tool_choice forced vs auto for unknown intents**
   - What we know: Using `tool_choice: {"type": "tool", "name": "control_device"}` forces Claude to always call the tool. This means even for unknown intents ("what's the weather?"), Claude will try to return a device control action.
   - What's unclear: How to handle non-device-control utterances when tool use is forced.
   - Recommendation: Use `tool_choice: {"type": "auto"}` so Claude can choose NOT to call the tool for non-device requests. When no tool_use block is returned, treat it as an unknown intent (D-20 message). This is more natural and handles edge cases better. Alternatively, add a second tool "unknown_request" that Claude can call for non-device intents.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (via uv) | Everything | Yes | 3.13.13 | -- |
| uv | Package management | Yes | 0.11.6 | -- |
| Microphone | VOICE-01, VOICE-02 | No (Windows dev, no mic) | -- | Text injection (D-13, D-15) |
| Speaker | VOICE-05 | No (dev mode) | -- | WAV file output (D-14) |
| LISA_OPENAI_API_KEY | VOICE-03 | Not set (needs .env) | -- | Tests mock the API |
| LISA_ANTHROPIC_API_KEY | VOICE-04 | Not set (needs .env) | -- | Tests mock the API |
| Piper voice model (.onnx) | VOICE-05 | Not downloaded | -- | Download during setup |
| openWakeWord models | VOICE-01 | Not downloaded | -- | Download during setup; Pi-only |

**Missing dependencies with no fallback:**
- None -- all hardware dependencies have dev-mode fallbacks

**Missing dependencies with fallback:**
- Microphone/speaker: text injection + WAV file output in dev mode
- API keys: tests mock cloud APIs; real keys needed only for integration testing
- Piper model: must be downloaded but scriptable

## Existing Code Integration Points

### What exists and stays unchanged
- `DeviceService.execute_command(device_id, action, source, raw_input)` -- the downstream target
- `DeviceAdapter` Protocol + `FakeAdapter` -- device abstraction
- `allowlist.validate_action()` -- action validation (called inside DeviceService)
- `command_log` SQLite table -- all commands logged here
- WebSocket `manager.broadcast()` -- real-time dashboard updates
- `Settings` class with LISA_ env prefix

### What gets extended
- `config.py` Settings -- add API key fields, timeout settings, TTS/STT model paths
- `main.py` lifespan -- create and inject voice pipeline services
- Text command flow -- LLM intent parsing supplements (not replaces) the existing regex parser

### What is new
- `services/stt_service.py` -- OpenAI Whisper wrapper
- `services/llm_intent_service.py` -- Anthropic Claude tool_use wrapper
- `services/tts_service.py` -- Piper TTS wrapper
- `services/voice_pipeline.py` -- orchestrator chaining the above
- `voice/wake_word.py` -- openWakeWord wrapper (Pi-only)
- `voice/audio_capture.py` -- mic + VAD (Pi-only)
- API endpoint for voice pipeline text injection (or reuse existing /api/commands/text with LLM path)

## Anthropic Claude Haiku 4.5 Cost Estimate

Per-command cost for intent parsing:
- System prompt (~200 tokens) + user message (~20 tokens) + tool definition (~150 tokens) + tool_use overhead (346 tokens) = ~716 input tokens
- Output: ~50 tokens (tool_use response)
- Cost per command: (716 * $1 / 1M) + (50 * $5 / 1M) = $0.000716 + $0.000250 = ~$0.001
- At 50 commands/day: ~$0.05/day, ~$1.50/month

## OpenAI Whisper API Cost Estimate

- Average command: 3-5 seconds of audio
- Cost: $0.006/min = $0.0001/second
- Per command (5s): $0.0005
- At 50 commands/day: ~$0.025/day, ~$0.75/month

## Sources

### Primary (HIGH confidence)
- Anthropic tool_use docs: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview -- tool definition, handling, strict mode, pricing
- Anthropic define tools: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools -- schema format, tool_choice, strict: true
- Anthropic handle tool calls: https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls -- response parsing, error handling
- Anthropic pricing: https://platform.claude.com/docs/en/about-claude/pricing -- Haiku 4.5: $1/MTok input, $5/MTok output
- OpenAI STT docs: https://developers.openai.com/api/docs/guides/speech-to-text -- whisper-1, gpt-4o-transcribe, formats, limits
- Piper TTS Python API: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md -- PiperVoice.load(), synthesize_wav(), streaming
- openWakeWord GitHub: https://github.com/dscripka/openWakeWord -- pre-trained models, prediction API, audio format requirements
- PyPI piper-tts: https://pypi.org/project/piper-tts/ -- v1.4.2, Python 3.9-3.13, Windows wheels available

### Secondary (MEDIUM confidence)
- openWakeWord custom training: https://github.com/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb -- ~10 min on Colab T4
- uv pip install --dry-run: anthropic 0.94.0, openai 2.31.0 (verified 2026-04-11)

### Tertiary (LOW confidence)
- gpt-4o-mini-transcribe quality vs whisper-1: Newer model available but no direct comparison data found for short-utterance latency
- Piper maintainer status: OHF-Voice "looking for maintainers" -- package still actively updated (v1.4.2 released 2026-04-02) but long-term status uncertain

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries verified on PyPI, APIs verified from official docs, versions confirmed
- Architecture: HIGH - matches existing codebase patterns (DeviceService, FakeAdapter, Settings), clear integration points
- Pitfalls: HIGH - well-documented in prior research (PITFALLS.md) and confirmed against official library constraints
- Cloud API usage: HIGH - verified from official Anthropic and OpenAI documentation with current pricing
- Wake word: MEDIUM - no pre-trained "hey lisa" model; training path documented but not tested

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (30 days -- stable libraries, APIs unlikely to change)
