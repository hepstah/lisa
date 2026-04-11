---
phase: 02-voice-pipeline
plan: 03
subsystem: api
tags: [fastapi, voice-pipeline, tts, stt, llm]

requires:
  - phase: 02-01
    provides: STTService and LLMIntentService cloud wrappers
  - phase: 02-02
    provides: TTSService Piper wrapper
provides:
  - VoicePipeline orchestrator chaining STT -> LLM -> DeviceService -> TTS
  - Text command API LLM intent parsing path with regex fallback
  - FastAPI lifespan voice service initialization with graceful degradation
affects: [03-integration, dashboard]

tech-stack:
  added: []
  patterns: [pipeline-orchestrator, graceful-degradation, module-injection]

key-files:
  created:
    - backend/lisa/services/voice_pipeline.py
    - backend/tests/test_voice_pipeline.py
    - backend/tests/test_api_voice.py
  modified:
    - backend/lisa/main.py
    - backend/lisa/api/commands.py
    - .env.example

key-decisions:
  - "VoicePipeline takes optional STT (None in dev mode) for text injection per D-13"
  - "Text command API preserves Phase 1 regex parser as fallback when pipeline is not configured"
  - "Pipeline services only created when API keys/model paths are configured -- no startup errors"

patterns-established:
  - "ERR-01 enforcement: every pipeline code path calls TTS.speak() -- silence is never acceptable"
  - "Graceful degradation: voice pipeline is None when deps missing, falls back to Phase 1 behavior"

requirements-completed: [VOICE-03, VOICE-04, VOICE-05, ERR-01, ERR-03]

duration: 5min
completed: 2026-04-11
---

# Plan 03: Voice Pipeline Orchestrator Summary

**Pipeline orchestrator chaining STT -> LLM intent -> DeviceService -> TTS with spoken feedback on every outcome**

## Performance

- **Duration:** 5 min
- **Tasks:** 2
- **Files created:** 3
- **Files modified:** 3

## Accomplishments
- VoicePipeline.process_text() chains LLM -> DeviceService -> TTS with error handling per D-17 through D-20
- VoicePipeline.process_audio() chains STT -> process_text with STT error handling
- Every pipeline outcome (success, unknown intent, timeout, connection error, device error) calls TTS.speak()
- Text command API routes through LLM when pipeline available, falls back to regex when not
- FastAPI lifespan creates voice services with graceful degradation

## Task Commits

1. **Task 1: Voice pipeline orchestrator** - `bcd2d05` (feat)
2. **Task 2: Wire into FastAPI and text API** - `1577c52` (feat)

## Files Created/Modified
- `backend/lisa/services/voice_pipeline.py` - Pipeline orchestrator with all error paths
- `backend/tests/test_voice_pipeline.py` - 9 tests covering every error path, each verifying TTS was called
- `backend/tests/test_api_voice.py` - 3 API integration tests
- `backend/lisa/main.py` - Lifespan creates voice pipeline services
- `backend/lisa/api/commands.py` - LLM intent parsing path with regex fallback
- `.env.example` - Voice pipeline configuration variables

## Decisions Made
- VoicePipeline accepts optional STT (None for dev mode text injection)
- Preserved Phase 1 regex parser as fallback rather than replacing it
- Voice services only instantiated when their config is present (no startup errors)

## Deviations from Plan
None - plan executed as written.

## Issues Encountered
None.

## Next Phase Readiness
- Full voice pipeline ready for Phase 3 integration
- End-to-end: voice command -> STT -> LLM intent -> device control -> spoken confirmation
- Text injection path works in dev mode without API keys (falls back to regex)

---
*Phase: 02-voice-pipeline*
*Completed: 2026-04-11*
