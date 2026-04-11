---
phase: 03-integration
plan: 01
subsystem: voice
tags: [pyaudio, asyncio, threading, aplay, wake-word, voice-loop, tts]

# Dependency graph
requires:
  - phase: 02-voice-pipeline
    provides: "WakeWordDetector, AudioCapture, VoicePipeline, TTSService"
provides:
  - "VoiceLoop: continuous wake word -> capture -> pipeline loop in background thread"
  - "TTSService aplay playback in Pi mode"
  - "Pipeline status WebSocket broadcast (type: pipeline_status)"
  - "Lifespan wiring for VoiceLoop in Pi mode"
affects: [03-integration, dashboard-pipeline-status]

# Tech tracking
tech-stack:
  added: [pyaudio (Pi-only, runtime)]
  patterns: [thread-to-asyncio bridge via run_coroutine_threadsafe, graceful Pi-only import with AVAILABLE flag]

key-files:
  created:
    - backend/lisa/voice/voice_loop.py
    - backend/tests/test_voice_loop.py
  modified:
    - backend/lisa/services/tts_service.py
    - backend/lisa/main.py

key-decisions:
  - "Used subprocess aplay for TTS playback over sounddevice.play() (simpler, no extra dependency, available on all Pi installs)"
  - "VoiceLoop runs in daemon thread with run_coroutine_threadsafe bridge to asyncio (same pattern as openWakeWord examples)"
  - "0.5s cooldown after TTS playback before re-enabling wake detection (echo prevention)"

patterns-established:
  - "Thread-to-async bridge: background thread calls run_coroutine_threadsafe to invoke async pipeline and broadcast status"
  - "Conditional Pi-mode startup: voice loop only starts when dev_mode=False and voice_pipeline is available"
  - "Pipeline status broadcast: type=pipeline_status events at each stage transition (listening, processing, responding, error)"

requirements-completed: [DEVICE-01]

# Metrics
duration: 4min
completed: 2026-04-11
---

# Phase 3 Plan 1: Voice Loop and TTS Playback Summary

**VoiceLoop class drives continuous wake word -> audio capture -> VoicePipeline flow in a background thread with aplay speaker output and pipeline status broadcasting**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-11T20:37:14Z
- **Completed:** 2026-04-11T20:41:23Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- VoiceLoop class that continuously listens for wake word, captures speech, and calls VoicePipeline.process_audio() in a background thread
- TTSService extended with aplay subprocess playback in Pi mode (dev mode unchanged)
- Pipeline status events broadcast via WebSocket at each stage transition (listening, processing, responding, error)
- Lifespan wiring in main.py conditionally starts VoiceLoop when dev_mode=False and voice_pipeline is available
- Wake detector mute/unmute around TTS playback with 0.5s cooldown for echo prevention

## Task Commits

Each task was committed atomically:

1. **Task 1: VoiceLoop class and TTS playback extension** - `bfa4006` (test: RED), `0fa1e40` (feat: GREEN)
2. **Task 2: Lifespan wiring and pipeline status broadcast** - `9971734` (feat)

## Files Created/Modified
- `backend/lisa/voice/voice_loop.py` - VoiceLoop class: continuous wake word -> capture -> pipeline loop in background thread
- `backend/lisa/services/tts_service.py` - Extended with aplay subprocess playback when dev_mode=False
- `backend/lisa/main.py` - Lifespan creates VoiceLoop in Pi mode, broadcasts pipeline_status events via WebSocket
- `backend/tests/test_voice_loop.py` - 7 tests for VoiceLoop logic and TTS aplay extension

## Decisions Made
- Used subprocess aplay for TTS speaker playback rather than sounddevice.play() -- simpler, no extra dependency, available on all Pi installs
- VoiceLoop runs in daemon thread with run_coroutine_threadsafe bridge to asyncio event loop (follows openWakeWord ecosystem convention)
- 0.5s cooldown after TTS playback before re-enabling wake word detection (echo prevention per pitfall 1 from research)
- Pipeline status uses existing WebSocket broadcast mechanism with new event type "pipeline_status" rather than adding a separate channel

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None -- no external service configuration required. PyAudio is only needed on Pi hardware; dev mode bypasses VoiceLoop entirely.

## Next Phase Readiness
- Voice loop is fully wired: wake word -> capture -> STT -> LLM -> device control -> TTS -> speaker playback
- Pipeline status events are broadcasting; dashboard component to display them is needed (plan 02)
- All 100 backend tests pass with zero regressions
- Dev mode continues to work via /api/commands/text without any audio dependencies

---
*Phase: 03-integration*
*Completed: 2026-04-11*
