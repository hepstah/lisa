---
phase: 02-voice-pipeline
plan: 04
subsystem: voice-pipeline
tags: [stt, error-handling, sqlite, tdd, voice-pipeline]

# Dependency graph
requires:
  - phase: 02-voice-pipeline/02-03
    provides: Voice pipeline orchestrator with STT/LLM/TTS error handling
provides:
  - STTNoSpeechError subclass for distinct no-speech detection
  - Differentiated spoken feedback for no-speech vs connection errors
  - DB persistence of pipeline-level errors (LLM timeout, STT timeout, unknown intent, connection errors)
affects: [dashboard, error-reporting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subclass exception hierarchy for distinct error handling (STTNoSpeechError < STTError)"
    - "Pipeline error DB persistence with duplicate-insert guard (check for 'id' in result)"

key-files:
  created: []
  modified:
    - backend/lisa/services/stt_service.py
    - backend/lisa/services/voice_pipeline.py
    - backend/lisa/api/commands.py
    - backend/tests/test_voice_pipeline.py
    - backend/tests/test_api_voice.py

key-decisions:
  - "STTNoSpeechError placed before STTError in except chain (subclass-first ordering)"
  - "Pipeline error DB insert guarded by 'id' not in result to avoid double-insert"

patterns-established:
  - "Exception subclass ordering: specific subclass handlers before generic base class handlers"
  - "Pipeline result enrichment: API layer adds DB id to pipeline results that lack one"

requirements-completed: [ERR-01, VOICE-01, VOICE-02, VOICE-03, VOICE-04, VOICE-05, ERR-03]

# Metrics
duration: 3min
completed: 2026-04-11
---

# Phase 02 Plan 04: Gap Closure Summary

**STTNoSpeechError differentiation with correct spoken message and pipeline error DB persistence for command_log dashboard visibility**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-11T19:42:01Z
- **Completed:** 2026-04-11T19:45:25Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- STTNoSpeechError subclass speaks "I didn't hear anything. Please try again." instead of misleading "Voice understanding is temporarily unavailable"
- Pipeline-level errors (LLM timeout, STT timeout, unknown intent, connection errors) now persisted to command_log for dashboard visibility
- All 93 tests pass with zero regressions (10 pipeline + 6 API voice + 77 others)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add STTNoSpeechError and fix pipeline error differentiation**
   - `b0dc3de` (test: RED - failing test for STTNoSpeechError)
   - `72aeab5` (feat: GREEN - pipeline handles STTNoSpeechError distinctly)
2. **Task 2: Persist pipeline-level errors to command_log database**
   - `3b9eb96` (test: RED - failing tests for pipeline error DB persistence)
   - `04e6744` (feat: GREEN - DB insert for pipeline errors in text_command)

## Files Created/Modified
- `backend/lisa/services/stt_service.py` - Added STTNoSpeechError subclass, changed empty transcript to raise it
- `backend/lisa/services/voice_pipeline.py` - Added MSG_NO_SPEECH constant and STTNoSpeechError handler before STTError
- `backend/lisa/api/commands.py` - Added DB insert for pipeline error/rejected results with duplicate guard
- `backend/tests/test_voice_pipeline.py` - Added test_process_audio_no_speech (10 total pipeline tests)
- `backend/tests/test_api_voice.py` - Added 3 tests for DB persistence (6 total API voice tests)

## Decisions Made
- STTNoSpeechError placed before STTError in except chain -- Python catches the first matching handler, so the more specific subclass must come first
- Pipeline error DB insert guarded by checking `"id" not in result` -- results from DeviceService.execute_command already have an id from _log_command, so we skip to avoid double-insert

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None -- no external service configuration required.

## Next Phase Readiness
- Phase 02 gap closure complete -- all verification gaps from 02-VERIFICATION.md addressed
- Error messages are now differentiated per failure mode (ERR-01 satisfied)
- All pipeline outcomes persisted to command_log (ERR-02 dashboard visibility satisfied)
- Ready for Phase 02 final verification pass

---
## Self-Check: PASSED

All 5 modified files verified present. All 4 commit hashes verified in git log.

---
*Phase: 02-voice-pipeline*
*Completed: 2026-04-11*
