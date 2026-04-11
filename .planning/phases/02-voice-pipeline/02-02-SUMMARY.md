---
phase: 02-voice-pipeline
plan: 02
subsystem: voice
tags: [piper-tts, openwakeword, vad, tts, wake-word, audio-capture]

# Dependency graph
requires:
  - phase: 01-dashboard-mvp
    provides: "FastAPI backend, DeviceService, Settings with env_prefix pattern"
provides:
  - "TTSService with Piper TTS wrapper and dev-mode WAV file output"
  - "WakeWordDetector with openwakeWord and mute/unmute echo prevention"
  - "AudioCapture with energy-based VAD and silence detection"
affects: [02-voice-pipeline]

# Tech tracking
tech-stack:
  added: [piper-tts, openwakeword, onnxruntime, numpy, scipy, scikit-learn]
  patterns: ["Graceful import with AVAILABLE flag for Pi-only dependencies", "Async wrapper via run_in_executor for sync Piper calls", "Energy-based VAD with configurable silence threshold"]

key-files:
  created:
    - backend/lisa/services/tts_service.py
    - backend/lisa/voice/__init__.py
    - backend/lisa/voice/wake_word.py
    - backend/lisa/voice/audio_capture.py
    - backend/tests/test_tts_service.py
    - backend/tests/test_wake_word.py
  modified:
    - backend/pyproject.toml
    - backend/uv.lock

key-decisions:
  - "Graceful import pattern for piper-tts and openwakeword with PIPER_AVAILABLE/OPENWAKEWORD_AVAILABLE flags"
  - "hey_jarvis as wake word dev stand-in per research recommendation (custom hey_lisa deferred to v2)"
  - "Energy-based VAD in AudioCapture (no PyAudio import -- audio source injected by caller)"

patterns-established:
  - "Graceful Pi-only import: try/except with AVAILABLE flag, raise in constructor if unavailable"
  - "Async synthesis: run_in_executor wraps sync Piper calls for pipeline compatibility"
  - "Mute/unmute protocol for TTS echo prevention on wake word detector"

requirements-completed: [VOICE-01, VOICE-02, VOICE-05]

# Metrics
duration: 4min
completed: 2026-04-11
---

# Phase 02 Plan 02: TTS, Wake Word, and Audio Capture Summary

**Piper TTS wrapper with dev-mode WAV output, openWakeWord detector with echo prevention, and energy-based audio capture VAD**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-11T18:46:57Z
- **Completed:** 2026-04-11T18:51:31Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- TTSService wraps Piper TTS with async speak() that writes timestamped WAV files in dev mode
- WakeWordDetector wraps openwakeWord with configurable threshold and mute/unmute for TTS echo prevention
- AudioCapture implements frame-by-frame energy-based VAD with silence detection and hard time cap
- All 13 new tests pass alongside 53 existing tests (66 total)

## Task Commits

Each task was committed atomically:

1. **Task 1: TTS service (TDD)** - `9c1b09d` (test: RED) + `eaba467` (feat: GREEN)
2. **Task 2: Wake word and audio capture** - `d72a937` (feat)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `backend/lisa/services/tts_service.py` - Piper TTS wrapper with async speak(), dev-mode WAV output, graceful import
- `backend/lisa/voice/__init__.py` - Voice subpackage init (Pi-only modules)
- `backend/lisa/voice/wake_word.py` - openWakeWord wrapper with threshold, mute/unmute, hey_jarvis default
- `backend/lisa/voice/audio_capture.py` - Frame-by-frame audio capture with energy-based VAD
- `backend/tests/test_tts_service.py` - 5 tests for TTSService with mocked Piper
- `backend/tests/test_wake_word.py` - 8 tests (4 wake word + 4 audio capture) with mocked openwakeword
- `backend/pyproject.toml` - Added piper-tts and openwakeword dependencies
- `backend/uv.lock` - Updated lockfile

## Decisions Made
- Used graceful import pattern (try/except + AVAILABLE flag) for both piper-tts and openwakeword since they are Pi-targeted dependencies that may not always install cleanly on all dev platforms
- Used "hey_jarvis" as the default wake word model since no pre-trained "hey_lisa" model exists; custom training deferred to v2 per ADV-03
- AudioCapture does NOT import PyAudio or sounddevice -- it defines capture logic only, with the audio source injected by the pipeline orchestrator on Pi. This keeps it testable on Windows without audio hardware.
- Energy-based VAD (RMS threshold) chosen over webrtcvad for simplicity; sufficient for close-range microphone per project constraints

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - piper-tts and openwakeword both installed cleanly on Windows via uv.

## Known Stubs

- `backend/lisa/services/tts_service.py:77` - `# TODO: Pi deployment - play audio through speaker instead of saving to file`. Intentional per plan; Pi speaker playback deferred to deployment phase.

## User Setup Required

None - no external service configuration required for these modules. Piper voice model (.onnx file) will be needed at runtime but that is handled by the pipeline orchestrator setup.

## Next Phase Readiness
- TTSService ready for integration into voice pipeline orchestrator (Plan 03)
- WakeWordDetector and AudioCapture ready for Pi deployment wiring
- All modules independently testable per D-16

## Self-Check: PASSED

All 6 created files verified on disk. All 3 commit hashes found in git log.

---
*Phase: 02-voice-pipeline*
*Completed: 2026-04-11*
