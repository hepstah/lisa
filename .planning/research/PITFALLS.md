# Pitfalls Research: Lisa (Voice-Controlled Home Assistant)

**Researched:** 2026-04-11
**Domain:** Raspberry Pi voice assistant with cloud LLM + single device integration

## Critical Pitfalls (Cause Rewrites)

### 1. Wake word model wrong for target environment

**What goes wrong:** openWakeWord models are trained on specific accent/noise profiles. A model that works in a quiet office fails in a kitchen with a running dishwasher. High false-positive rate or low detection rate.

**Warning signs:** Works perfectly in dev, fails in actual room placement.

**Prevention:**
- Test wake word detection in the actual target room early
- Tune detection threshold with real ambient noise
- Log all wake word triggers (true and false) for threshold adjustment

**Phase:** Should be addressed in voice pipeline phase. Don't wait until integration.

### 2. Audio capture blocking the event loop

**What goes wrong:** PyAudio's blocking read calls run on the main thread, freezing the async event loop. Dashboard becomes unresponsive during voice capture. WebSocket connections drop.

**Warning signs:** Dashboard freezes when speaking to Lisa. API requests timeout during voice commands.

**Prevention:**
- Run audio capture in a dedicated thread from day one
- Use `asyncio.run_in_executor()` or a separate thread with a queue
- Never do blocking I/O on the asyncio event loop

**Phase:** Must be designed correctly in foundation phase. Retrofitting thread isolation is painful.

### 3. Microphone echo/feedback loop

**What goes wrong:** TTS plays through speaker, wake word detector picks it up, triggers another capture. Lisa talks to herself in a loop.

**Warning signs:** Lisa responds to her own voice. Random activations after every TTS response.

**Prevention:**
- Mute the wake word detector while TTS is playing
- Add a cooldown period after TTS completes before re-enabling detection
- If using same device for mic+speaker: implement echo suppression or use directional mic

**Phase:** Voice pipeline phase. Critical for demo-readiness.

### 4. Cloud LLM latency blows the 3-second budget

**What goes wrong:** Pipeline is serial: STT (1s) + LLM (1.5s) + TTS generation (0.5s) + device command (0.3s) = 3.3s minimum. Any spike in cloud latency pushes past acceptable response time.

**Warning signs:** End-to-end timing exceeds 3s in testing. User feels like nothing happened.

**Prevention:**
- Measure each pipeline stage independently from the start
- Use streaming STT if available (start LLM before full transcription)
- Use LLM with fast response times (GPT-4o-mini, Claude Haiku)
- Start TTS as soon as confirmation text is known (don't wait for device response)
- Consider "working on it" audio cue if total latency exceeds 2s

**Phase:** End-to-end integration phase. But measure individual stages during each component build.

### 5. Device state gets out of sync

**What goes wrong:** Lisa thinks the lamp is off but it was turned on via the Hue app or physical switch. LLM generates incorrect confirmation ("turning off" when it's already off). Dashboard shows wrong state.

**Warning signs:** Dashboard shows stale state. Voice confirmations are wrong.

**Prevention:**
- Query actual device state before executing command (not cached state)
- Or: poll device state on a short interval and update cache
- Design confirmations based on action taken, not assumed previous state: "Bedroom lamp is now off" not "Turning off the bedroom lamp"

**Phase:** Device control phase. State sync strategy must be decided when building the adapter.

### 6. LLM hallucinating device commands

**What goes wrong:** User says "turn on the bedroom lamp" but LLM returns `{"device": "bedroom_light"}` (wrong name) or invents an action like `"dim_to_50"` that isn't supported. Command silently fails or hits wrong device.

**Warning signs:** Commands fail with "device not found" despite correct user intent. Unexpected devices respond.

**Prevention:**
- Pass exact device names and supported actions in the LLM system prompt
- Validate LLM output against an allowlist before execution
- Return clear error if LLM output doesn't match known devices/actions
- Keep the intent set small and explicit for v1

**Phase:** LLM orchestrator phase. Allowlist validation is non-negotiable.

## Moderate Pitfalls (Significant Rework)

### 7. Wake word threshold tuned to dev environment

**What goes wrong:** Threshold works in quiet dev setup, too sensitive in noisy room (false triggers) or too strict in echoey room (misses).

**Prevention:**
- Make threshold configurable via dashboard (not code change)
- Log all detection events with confidence scores
- Provide a "calibration mode" in dashboard that shows real-time detection scores

**Phase:** Dashboard config phase.

### 8. Python ARM dependency failures on Pi

**What goes wrong:** Libraries that build fine on x86 (dev machine) fail to compile on ARM64 (Pi). Common with audio libraries, numpy, and ML model loaders.

**Prevention:**
- Set up Pi (or ARM64 VM) as CI target early
- Test every new dependency on ARM64 before committing to it
- Prefer pure Python or pre-built ARM wheels (check PyPI ARM availability)
- Pin exact versions in requirements.txt

**Phase:** Foundation phase. Catch this in initial setup, not after building everything.

### 9. WebSocket connections dropping silently

**What goes wrong:** Dashboard opens WebSocket, network hiccup closes it, no reconnect logic. Dashboard shows stale data with no indication.

**Prevention:**
- Implement automatic reconnect with exponential backoff on client
- Show connection status indicator in dashboard UI
- Heartbeat ping/pong to detect dead connections

**Phase:** Dashboard phase.

### 10. LLM context window bloat

**What goes wrong:** Sending full device state, command history, and system config in every LLM request. Slow, expensive, and unnecessary for v1's small intent set.

**Prevention:**
- System prompt: supported intents + current device list (names + states). Nothing more.
- Don't send command history (no conversational context in v1)
- Keep system prompt under 500 tokens

**Phase:** LLM orchestrator phase.

### 11. No feedback when cloud APIs are down

**What goes wrong:** Internet drops, STT call hangs for 30s timeout, user gets silence. Thinks Lisa is broken.

**Prevention:**
- Set aggressive timeouts: 5s for STT, 5s for LLM
- On timeout: immediate spoken response "I can't reach my cloud services right now"
- Dashboard shows connectivity status
- Log the failure with timestamp

**Phase:** Must be built into each cloud integration. Don't defer to "error handling phase."

### 12. SD card corruption from improper shutdown

**What goes wrong:** Pi loses power, SQLite database corrupts, command history lost, config lost.

**Prevention:**
- Use SQLite WAL mode (write-ahead logging) for crash resilience
- Mount root filesystem read-only where possible
- Keep database on a separate partition or use periodic backups
- Use `fsync` after critical writes

**Phase:** Foundation phase (database setup).

## Minor Pitfalls

### 13. TTS voice quality expectations

**What goes wrong:** Piper TTS is good but not Google/Alexa quality. User expects premium voice.

**Prevention:** Set expectations. Test available Piper voices early. Consider cloud TTS as optional upgrade path.

### 14. Scope creep into automation

**What goes wrong:** "Just add a simple timer" → "What about schedules?" → "What about rules?" → full automation engine.

**Prevention:** PROJECT.md explicitly excludes automation in v1. Enforce the boundary. Voice commands only, no rules.

### 15. USB microphone compatibility

**What goes wrong:** Not all USB mics work well on Pi. Some need extra ALSA config, some have poor gain, some don't support the sample rate.

**Prevention:** Test specific mic model on Pi before writing audio code. Recommend a known-good mic in docs. ReSpeaker or similar Pi-tested USB mic.

## Pitfall Priority by Phase

| Phase | Watch For |
|-------|-----------|
| Foundation (state, device, API, dashboard) | #8 ARM deps, #9 WebSocket drops, #12 SD card corruption |
| Device Control | #5 State sync, #6 LLM hallucination (design allowlist early) |
| Voice Pipeline | #1 Wake word environment, #2 Thread blocking, #3 Echo loop, #15 USB mic |
| Cloud Integration | #4 Latency budget, #10 Context bloat, #11 No offline feedback |
| End-to-End | #4 Latency budget (full pipeline), #7 Threshold tuning |

---
*Researched: 2026-04-11*
