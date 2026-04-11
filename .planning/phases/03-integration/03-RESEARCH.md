# Phase 3: Integration - Research

**Researched:** 2026-04-11
**Domain:** End-to-end voice-to-device pipeline, real-time dashboard pipeline status
**Confidence:** HIGH

## Summary

Phase 3 wires the voice pipeline (Phase 2) to device control (Phase 1) in a continuous audio loop and adds real-time pipeline status to the dashboard. The codebase is well-structured for this: `VoicePipeline.process_audio()` already chains STT -> LLM -> DeviceService -> TTS, and `ConnectionManager.broadcast()` already pushes events over WebSocket. What is missing is (1) a continuous audio loop that listens for the wake word, captures speech, and feeds audio bytes into `VoicePipeline.process_audio()`, (2) pipeline state broadcasting so the dashboard can show what the assistant is doing, and (3) actual audio playback on the Pi so TTS output reaches the speaker.

The existing architecture is clean and narrowly scoped. The voice pipeline is purely functional (audio bytes in, result dict out). The wake word detector and audio capture are both implemented but not yet connected to any loop. The TTS service writes WAV files but does not play them. The dashboard receives WebSocket events for device state and command logs but has no concept of pipeline status.

**Primary recommendation:** Build a `VoiceLoop` class that runs in a background thread, drives wake word detection + audio capture + pipeline execution in a blocking loop, and emits pipeline status events through the existing WebSocket broadcast mechanism. Add a `PipelineStatus` component to the dashboard that subscribes to a new `pipeline_status` WebSocket event type.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEVICE-01 | Control one concrete device integration end-to-end via voice command | Voice loop wiring: wake word -> audio capture -> STT -> LLM -> DeviceService -> TTS -> speaker playback. All components exist individually; the loop and audio playback are the missing pieces. |
| DASH-05 | Show assistant pipeline status (listening, processing, responding, error, offline) during a voice command | New `pipeline_status` WebSocket event type broadcast at each stage transition, consumed by a new dashboard `PipelineStatus` component. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Prefer dev-mode trigger paths over hardware wake-word implementation
- Prefer fake or stub device adapters over broad protocol support
- Prefer typed transcript injection over mandatory live audio
- Prefer explicit contracts over speculative abstractions
- Keep file ownership tight; do not touch unrelated files
- No broad architectural rewrites
- No opportunistic cleanup refactors
- V1 proves one integration end-to-end, not a platform
- Latency target: median successful command under 3 seconds on healthy network
- Typed text commands are a testing aid, not a core product feature
- Device discovery is not required for v1

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.135.0 | API + WebSocket server | Already used; WebSocket broadcast mechanism exists |
| python-kasa | >=0.10.0 | TP-Link Kasa device control | Already used; KasaAdapter is implemented |
| openai (Whisper API) | >=2.31.0 | Speech-to-text | Already used in STTService |
| anthropic | >=0.94.0 | LLM intent parsing | Already used in LLMIntentService |
| piper-tts | >=1.4.2 | Local text-to-speech | Already used in TTSService |
| openwakeword | >=0.6.0 | Wake phrase detection | Already used in WakeWordDetector |
| React 19 + Vite 8 | latest | Dashboard frontend | Already used |
| Tailwind CSS v4 | >=4.2.2 | Dashboard styling | Already used |

### Supporting (may need to add)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyAudio | 0.2.14 | Microphone capture on Pi | Required for the continuous audio loop on Pi hardware. NOT needed in dev mode. |
| sounddevice | 0.5.x | Alternative to PyAudio | Only if PyAudio proves problematic on Pi. PyAudio is more commonly used with openWakeWord examples. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyAudio for mic | sounddevice | sounddevice has nicer API but openWakeWord examples all use PyAudio; stick with ecosystem convention |
| subprocess aplay for TTS playback | sounddevice.play() | aplay is simpler (no extra dependency), available on all Pi installs, and sufficient for playing a single WAV file |
| SSE for pipeline status | WebSocket (existing) | WebSocket is already wired; adding SSE would be a second real-time channel for no benefit |

**Installation (Pi only):**
```bash
# PyAudio requires portaudio on Pi
sudo apt-get install portaudio19-dev
pip install pyaudio
```

No new npm packages needed for the dashboard.

## Architecture Patterns

### What Exists vs. What Phase 3 Builds

```
EXISTING (Phase 1 + Phase 2):
  FakeAdapter / KasaAdapter --> DeviceService --> API endpoints --> WebSocket broadcast
  WakeWordDetector (standalone, not connected to any loop)
  AudioCapture (standalone, not connected to any loop)
  STTService, LLMIntentService, TTSService (all standalone)
  VoicePipeline.process_audio(bytes) --> chains STT -> LLM -> Device -> TTS
  VoicePipeline.process_text(str) --> chains LLM -> Device -> TTS
  Dashboard: StatusBar, DeviceList, CommandHistory, TextCommand

PHASE 3 ADDS:
  VoiceLoop (new) -- background thread that continuously:
    1. Reads mic frames via PyAudio
    2. Feeds frames to WakeWordDetector.detect()
    3. On detection: switches to AudioCapture.process_frame() until silence
    4. Calls VoicePipeline.process_audio(captured_bytes)
    5. Emits pipeline_status events at each transition

  PipelineStatusBroadcaster (new or inline) -- emits WebSocket events:
    { type: "pipeline_status", status: "listening" | "processing" | "responding" | "error" | "offline" }

  TTS audio playback (extend TTSService) -- after writing WAV, play it:
    subprocess.run(["aplay", path]) on Pi
    No playback in dev mode (keep writing files only)

  Dashboard PipelineStatus component (new) -- displays current pipeline state
```

### Recommended Project Structure (new/modified files)

```
backend/
  lisa/
    voice/
      voice_loop.py          # NEW: continuous wake word -> capture -> pipeline loop
    services/
      voice_pipeline.py      # MODIFY: add status callback hooks
      tts_service.py          # MODIFY: add aplay playback in Pi mode
    api/
      ws.py                   # MODIFY: add pipeline_status event type constant
    main.py                   # MODIFY: start VoiceLoop in lifespan (Pi mode only)
dashboard/
  src/
    components/
      PipelineStatus.tsx      # NEW: pipeline status indicator
    api/
      types.ts                # MODIFY: add pipeline_status to WsEvent union
    App.tsx                   # MODIFY: wire PipelineStatus into layout
```

### Pattern 1: Background Audio Thread with Async Bridge

**What:** The VoiceLoop runs a blocking PyAudio read loop in a dedicated thread. When it needs to call the async VoicePipeline, it uses `asyncio.run_coroutine_threadsafe()` to bridge from the thread into the main event loop.

**When to use:** Always on Pi. Never in dev mode (dev mode uses text injection via the existing `/api/commands/text` endpoint).

**Example:**
```python
import asyncio
import threading
import logging

logger = logging.getLogger(__name__)


class VoiceLoop:
    """Continuous wake word -> capture -> pipeline loop.

    Runs in a background thread. Uses asyncio.run_coroutine_threadsafe()
    to call the async VoicePipeline from the blocking audio thread.
    """

    def __init__(self, wake_detector, audio_capture, pipeline, event_loop, status_callback):
        self._wake = wake_detector
        self._capture = audio_capture
        self._pipeline = pipeline
        self._loop = event_loop  # main asyncio loop
        self._status_cb = status_callback
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _emit_status(self, status: str):
        """Bridge status update to async broadcast."""
        asyncio.run_coroutine_threadsafe(self._status_cb(status), self._loop)

    def _run(self):
        import pyaudio
        import numpy as np

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1280,  # 80ms at 16kHz
        )

        self._emit_status("listening")

        try:
            while self._running:
                frame = stream.read(1280, exception_on_overflow=False)

                # Phase 1: Wake word detection
                detections = self._wake.detect(frame)
                if not detections:
                    continue

                # Wake word detected -- capture speech
                logger.info("Wake word detected: %s", detections)
                self._emit_status("processing")
                self._capture.reset()

                # Feed the triggering frame and continue capturing
                self._capture.process_frame(frame)
                while self._capture.process_frame(stream.read(1280, exception_on_overflow=False)):
                    pass

                audio_bytes = self._capture.get_audio()

                if not self._capture.has_speech():
                    self._emit_status("error")
                    # Pipeline handles the no-speech case
                    fut = asyncio.run_coroutine_threadsafe(
                        self._pipeline.process_audio(audio_bytes), self._loop
                    )
                    fut.result(timeout=15)
                    self._emit_status("listening")
                    continue

                # Process through pipeline
                self._emit_status("processing")
                fut = asyncio.run_coroutine_threadsafe(
                    self._pipeline.process_audio(audio_bytes), self._loop
                )
                result = fut.result(timeout=15)

                self._emit_status("responding")
                # TTS playback happens inside pipeline.process_audio()
                # Brief pause, then back to listening
                self._emit_status("listening")

        except Exception:
            logger.exception("VoiceLoop crashed")
            self._emit_status("error")
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
```

### Pattern 2: Pipeline Status as WebSocket Events

**What:** A thin callback that broadcasts pipeline state transitions via the existing `ConnectionManager.broadcast()`.

**Example:**
```python
from lisa.api.ws import manager

async def broadcast_pipeline_status(status: str):
    """Broadcast pipeline status to all dashboard clients."""
    await manager.broadcast({
        "type": "pipeline_status",
        "status": status,
    })
```

### Pattern 3: TTS Audio Playback via subprocess

**What:** After synthesizing WAV, play it through the speaker using `aplay` (ALSA).

**When to use:** Pi mode only. Dev mode continues writing WAV files without playback.

**Example:**
```python
import subprocess

async def speak(self, text: str) -> str | None:
    path = await self._synthesize(text)
    if path and not self._dev_mode:
        # Mute wake word during playback to prevent echo
        await asyncio.to_thread(
            subprocess.run, ["aplay", "-q", path], check=True, timeout=10
        )
    return path
```

### Pattern 4: Dashboard Pipeline Status Component

**What:** A React component that renders the current pipeline state with visual indicators.

**Example:**
```tsx
// PipelineStatus.tsx
type PipelineState = "listening" | "processing" | "responding" | "error" | "offline";

const stateConfig: Record<PipelineState, { label: string; color: string; icon: string }> = {
  listening:  { label: "Listening",   color: "bg-emerald-500", icon: "Mic" },
  processing: { label: "Processing",  color: "bg-amber-500 animate-pulse", icon: "Loader" },
  responding: { label: "Responding",  color: "bg-blue-500", icon: "Volume2" },
  error:      { label: "Error",       color: "bg-red-500", icon: "AlertCircle" },
  offline:    { label: "Offline",     color: "bg-gray-500", icon: "WifiOff" },
};
```

### Anti-Patterns to Avoid

- **Running PyAudio on the async event loop:** PyAudio's `stream.read()` is blocking. It MUST run in a dedicated thread, never on the event loop. The existing INFRA-04 requirement explicitly mandates this.
- **Polling for pipeline status:** Do not have the dashboard poll an endpoint for status. Use the existing WebSocket push mechanism.
- **Building a generic event bus:** The existing `ConnectionManager.broadcast()` is sufficient. Do not add pub/sub, Redis, or message queuing infrastructure.
- **Abstracting the voice loop:** There is one voice loop. Do not build a framework for multiple listeners or configurable audio sources. Keep it concrete.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio playback on Pi | WAV decoder + ALSA bindings | `subprocess.run(["aplay", path])` | aplay is pre-installed on all Pi OS images, handles ALSA device selection, and is a single line of code |
| Mic capture | Custom PortAudio bindings | PyAudio with standard 16kHz/16-bit/mono config | PyAudio is the standard for openWakeWord, well-tested on Pi |
| Thread-to-async bridge | Custom queue/callback system | `asyncio.run_coroutine_threadsafe()` | Built into Python stdlib, handles the exact pattern needed |
| Real-time dashboard updates | HTTP polling, SSE, or new WebSocket | Existing `ConnectionManager.broadcast()` | Already working, already consumed by dashboard hooks |

**Key insight:** Nearly every component already exists as a tested unit. Phase 3's job is wiring, not building. The temptation will be to "improve" existing components while integrating them. Resist that. Wire first, measure, then tune only if the 3-second latency target is missed.

## Common Pitfalls

### Pitfall 1: Wake Word Echo During TTS Playback

**What goes wrong:** TTS audio plays through the speaker, the microphone picks it up, and the wake word detector triggers on Lisa's own voice.
**Why it happens:** The mic is always hot in the continuous loop.
**How to avoid:** Mute the WakeWordDetector before TTS playback and unmute after playback completes plus a ~500ms cooldown. The `WakeWordDetector.mute()`/`unmute()` methods already exist for this exact purpose.
**Warning signs:** False triggers appearing in logs immediately after TTS responses.

### Pitfall 2: Blocking the Event Loop with Audio Operations

**What goes wrong:** Calling `stream.read()` or `subprocess.run(["aplay", ...])` on the async event loop freezes the entire FastAPI server.
**Why it happens:** These are blocking I/O calls.
**How to avoid:** All audio I/O runs in a dedicated thread (VoiceLoop thread for mic, `asyncio.to_thread()` for aplay). Per INFRA-04, audio capture must be in a dedicated thread.
**Warning signs:** Dashboard WebSocket disconnects or API timeouts during voice commands.

### Pitfall 3: Pipeline Status Race Conditions

**What goes wrong:** Status updates arrive out of order on the dashboard, or a "listening" update arrives before "responding" finishes displaying.
**Why it happens:** The thread emits status via `run_coroutine_threadsafe()` which is not synchronous with the UI render cycle.
**How to avoid:** The dashboard component should simply display whatever the latest status is. No transitions, no animations that depend on seeing every intermediate state. Each status update replaces the previous one.
**Warning signs:** Dashboard showing "listening" while a command is clearly still being processed.

### Pitfall 4: VoiceLoop Crash Takes Down the Server

**What goes wrong:** An unhandled exception in the audio thread silently kills the voice loop, but the FastAPI server keeps running with no voice capability.
**Why it happens:** Daemon threads die silently.
**How to avoid:** Wrap the entire `_run()` method in try/except, log the error, emit an "error" pipeline status, and optionally attempt a restart after a delay. The systemd service has `Restart=on-failure` but that only catches the process dying, not a thread dying.
**Warning signs:** Dashboard showing "error" or "offline" status but the backend API still responding normally.

### Pitfall 5: Dev Mode Must Still Work Without Audio Hardware

**What goes wrong:** Adding the VoiceLoop initialization to `main.py` causes import errors or crashes on dev machines without PyAudio.
**Why it happens:** PyAudio requires PortAudio C library, which is not installed on Windows/Mac dev machines.
**How to avoid:** The VoiceLoop must ONLY be instantiated when `dev_mode=False`. In dev mode, the text command path (`/api/commands/text`) continues to work exactly as it does today. The existing graceful import pattern (used by wake_word.py and tts_service.py) should be followed.
**Warning signs:** Backend fails to start on dev machines after Phase 3 changes.

### Pitfall 6: Latency Budget Exhaustion

**What goes wrong:** The end-to-end command exceeds the 3-second target.
**Why it happens:** STT (up to 3s) + LLM (up to 3s) + device control + TTS synthesis + TTS playback all add up.
**How to avoid:** The 3-second target is for the "median successful command on a healthy network" which means typical cloud response times (STT ~500ms, LLM ~500ms), not the timeout ceiling. Measure actual latency per stage and log it. If the median exceeds 3 seconds, the issue is likely in TTS synthesis time, which should be profiled. The individual service timeouts (3s each) are aggressive ceilings, not typical latencies.
**Warning signs:** `duration_ms` in command_log consistently exceeding 3000.

## Code Examples

### Lifespan Wiring (main.py modification)

```python
# In main.py lifespan, after voice_pipeline is created:
if voice_pipeline and not settings.dev_mode:
    from lisa.voice.voice_loop import VoiceLoop

    loop = asyncio.get_event_loop()

    async def status_cb(status: str):
        await manager.broadcast({"type": "pipeline_status", "status": status})

    voice_loop = VoiceLoop(
        wake_detector=WakeWordDetector(),
        audio_capture=AudioCapture(),
        pipeline=voice_pipeline,
        event_loop=loop,
        status_callback=status_cb,
    )
    voice_loop.start()
    logger.info("Voice loop started")
else:
    logger.info("Voice loop skipped (dev mode or pipeline unavailable)")
```

### WebSocket Event Type Addition (types.ts)

```typescript
// Add to WsEvent union:
| { type: "pipeline_status"; status: "listening" | "processing" | "responding" | "error" | "offline" }
```

### Pipeline Status Hook (new usePipelineStatus.ts)

```typescript
import { useState, useCallback } from "react";
import type { WsEvent } from "../api/types";

export type PipelineState = "listening" | "processing" | "responding" | "error" | "offline";

export function usePipelineStatus() {
  const [status, setStatus] = useState<PipelineState>("offline");

  const handleWsEvent = useCallback((event: WsEvent) => {
    if (event.type === "pipeline_status") {
      setStatus(event.status as PipelineState);
    }
  }, []);

  return { status, handleWsEvent };
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyAudio + callback | PyAudio + blocking read in thread | Stable | Both work; blocking read is simpler for wake-word-then-capture pattern |
| PulseAudio on Pi | ALSA direct | Pi OS default | PulseAudio adds latency and complexity; ALSA is direct and sufficient |
| WebSocket for each feature | Single WebSocket with typed events | Project convention | Already established in Phase 1; Phase 3 adds one more event type |

**Deprecated/outdated:**
- Snowboy: discontinued, do not use
- PulseAudio on Pi for single-mic: unnecessary layer; ALSA works directly

## Open Questions

1. **PyAudio availability on Pi 5 with current Pi OS**
   - What we know: PyAudio works on Pi 4 with `apt-get install portaudio19-dev`. Pi 5 uses the same Debian base.
   - What is unclear: Whether the default Pi 5 64-bit OS has any ALSA configuration differences.
   - Recommendation: Treat as LOW risk. If PyAudio fails on Pi 5, sounddevice is the fallback.

2. **Exact aplay device selection on Pi**
   - What we know: `aplay` uses the default ALSA device. With a USB speaker + USB mic, device names depend on hardware detection order.
   - What is unclear: Whether the user has a specific audio setup.
   - Recommendation: Use `aplay -q <path>` with the default device. If device selection is needed, expose an optional `LISA_AUDIO_OUTPUT_DEVICE` env var, but do not implement this unless the default fails.

3. **Pipeline status "offline" detection**
   - What we know: The voice loop knows its own state (listening, processing, responding, error). The dashboard needs to show "offline" when the voice loop is not running.
   - What is unclear: How the dashboard distinguishes "pipeline not started yet" from "pipeline crashed."
   - Recommendation: On WebSocket connect, the dashboard starts with "offline" as default. The voice loop emits "listening" when it starts. If the connection drops, the dashboard reverts to "offline" via the existing `onclose` handler. No separate heartbeat needed.

## Environment Availability

> This phase's primary target is the Raspberry Pi. Most dev-mode testing uses the existing text command path and does not require audio hardware. The following audit covers Pi deployment dependencies.

| Dependency | Required By | Available (Dev) | Available (Pi) | Fallback |
|------------|------------|-----------------|----------------|----------|
| PyAudio + PortAudio | VoiceLoop mic capture | Not needed (dev mode bypasses) | Install via apt + pip | sounddevice |
| aplay (ALSA utils) | TTS playback | Not needed (dev mode writes files only) | Pre-installed on Pi OS | subprocess with alternative player |
| USB microphone | VoiceLoop audio input | Not needed (text injection) | Hardware requirement | None (Pi deployment requirement) |
| Speaker/audio output | TTS playback | Not needed | Hardware requirement | None (Pi deployment requirement) |
| openwakeword + onnxruntime | Wake word detection | Graceful skip (AVAILABLE flag) | pip install | None |
| piper-tts | TTS synthesis | Graceful skip (AVAILABLE flag) | pip install | None |

**Missing dependencies with no fallback:**
- USB microphone and speaker are hardware requirements for Pi deployment. Cannot be simulated.

**Missing dependencies with fallback:**
- PyAudio: if installation fails on Pi 5, sounddevice is a viable alternative with minor code changes.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: All existing source files read directly
- openWakeWord GitHub examples: detect_from_microphone.py showing PyAudio + continuous loop pattern
- Python asyncio docs: `run_coroutine_threadsafe()` for thread-to-async bridging

### Secondary (MEDIUM confidence)
- [openWakeWord repository](https://github.com/dscripka/openWakeWord) - microphone streaming examples
- [sounddevice PyPI](https://pypi.org/project/sounddevice/) - alternative audio library
- [Python asyncio event loop docs](https://docs.python.org/3/library/asyncio-eventloop.html) - `run_coroutine_threadsafe` documentation
- [FastAPI WebSockets docs](https://fastapi.tiangolo.com/advanced/websockets/) - broadcast patterns

### Tertiary (LOW confidence)
- [Raspberry Pi forum discussions on PyAudio vs sounddevice](https://forums.raspberrypi.com/viewtopic.php?t=269420) - community experience reports

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in the project; no new major dependencies
- Architecture: HIGH - Clean integration of existing components; patterns are standard Python async/threading
- Pitfalls: HIGH - Based on direct codebase analysis and well-documented audio/async anti-patterns
- Dashboard: HIGH - Extends existing WebSocket event pattern established in Phase 1

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable domain; no fast-moving dependencies)
