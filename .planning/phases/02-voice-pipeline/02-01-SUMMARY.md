---
phase: 02-voice-pipeline
plan: 01
subsystem: voice-pipeline
tags: [openai, anthropic, whisper, claude, stt, llm, tool-use, async]

# Dependency graph
requires:
  - phase: 01-dashboard-core
    provides: Settings class with LISA_ env prefix, DeviceService, FakeAdapter
provides:
  - STTService wrapping OpenAI Whisper API with 3s timeout
  - LLMIntentService wrapping Anthropic Claude Haiku 4.5 with tool_use
  - DeviceIntent dataclass for structured intent output
  - Extended Settings with voice pipeline configuration fields
affects: [02-voice-pipeline/02-03, voice-pipeline-orchestrator, text-command-integration]

# Tech tracking
tech-stack:
  added: [openai, anthropic, httpx-timeout]
  patterns: [async-cloud-service-wrapper, tool-use-intent-parsing, construction-time-validation]

key-files:
  created:
    - backend/lisa/services/stt_service.py
    - backend/lisa/services/llm_intent_service.py
    - backend/tests/test_stt_service.py
    - backend/tests/test_llm_intent_service.py
  modified:
    - backend/lisa/config.py
    - backend/pyproject.toml

key-decisions:
  - "Used tool_choice auto (not forced) so Claude can decline tool call for non-device requests, returning None for unknown intents per D-20"
  - "Validate API key presence at construction time, not first call, per pitfall 4"
  - "Used httpx.Timeout(timeout, connect=5.0) for both services -- separate connect vs request timeouts"

patterns-established:
  - "Async cloud service wrapper: class with __init__ validating config, async methods wrapping SDK calls, custom error hierarchy"
  - "Construction-time validation: raise ValueError for missing API keys at __init__, not at first use"
  - "Error re-wrapping: catch SDK-specific exceptions and re-raise as service-specific errors (STTError, LLMError)"

requirements-completed: [VOICE-03, VOICE-04, ERR-03]

# Metrics
duration: 6min
completed: 2026-04-11
---

# Phase 02 Plan 01: Cloud Services (STT + LLM Intent) Summary

**OpenAI Whisper STT and Anthropic Claude Haiku 4.5 tool_use intent parser with 3s timeouts, tested against mocked APIs**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-11T18:46:48Z
- **Completed:** 2026-04-11T18:52:23Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- STTService wraps OpenAI Whisper API with async transcribe(), 3s timeout, and clear error hierarchy (STTError, STTTimeoutError)
- LLMIntentService wraps Anthropic Claude Haiku 4.5 with tool_use for structured device intent parsing, returns DeviceIntent or None for unknown intents
- Settings class extended with 8 new voice pipeline fields (API keys, timeouts, model names, TTS paths)
- Both services validate API keys at construction time, not first call
- 11 new tests (5 STT + 6 LLM), all 77 project tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend config and add STT service with tests** - `9c1b09d` (feat) -- committed by parallel agent as part of 02-02 TDD setup
2. **Task 2: Create LLM intent service with tests (TDD)**
   - RED: `0b8a9cd` (test) -- 6 failing tests for LLM intent service
   - GREEN: `de056b4` (feat) -- LLM intent service implementation passing all tests

## Files Created/Modified
- `backend/lisa/config.py` - Extended Settings with voice pipeline fields (API keys, timeouts, models)
- `backend/lisa/services/stt_service.py` - OpenAI Whisper API async wrapper with STTError hierarchy
- `backend/lisa/services/llm_intent_service.py` - Anthropic Claude tool_use intent parser with DeviceIntent dataclass
- `backend/tests/test_stt_service.py` - 5 unit tests covering success, timeout, connection error, empty result, empty key
- `backend/tests/test_llm_intent_service.py` - 6 unit tests covering intent parsing, unknown intents, timeout, connection error, system prompt
- `backend/pyproject.toml` - Added openai and anthropic SDK dependencies

## Decisions Made
- Used `tool_choice: {"type": "auto"}` instead of forced tool choice per research open question 4. This allows Claude to NOT call the tool for non-device requests ("what's the weather?"), correctly handling unknown intents by returning None (D-20 message).
- Validated API key presence at construction time per pitfall 4 -- raises ValueError immediately rather than failing on first call.
- Used `httpx.Timeout(timeout, connect=5.0)` for both services -- 3s request timeout with a 5s connect timeout, since DNS/TLS setup may take longer than the request itself.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1 already committed by parallel agent**
- **Found during:** Task 1 (commit phase)
- **Issue:** Parallel agent executing 02-02 plan committed config.py, stt_service.py, test_stt_service.py, pyproject.toml, and uv.lock as part of its TDD RED phase (commit 9c1b09d). The files were identical to what this plan specifies.
- **Fix:** Verified the committed files match plan requirements exactly. Adopted commit 9c1b09d as Task 1's commit rather than creating a duplicate.
- **Files affected:** backend/lisa/config.py, backend/lisa/services/stt_service.py, backend/tests/test_stt_service.py, backend/pyproject.toml, backend/uv.lock
- **Verification:** All 5 STT tests pass. Config fields present and correct.
- **Committed in:** 9c1b09d (by parallel 02-02 agent)

---

**Total deviations:** 1 (parallel agent overlap on Task 1 artifacts)
**Impact on plan:** No functional impact. Files were identical. Task 2 proceeded normally with TDD flow.

## Issues Encountered
- Git worktree CWD required explicit `--git-dir` and `--work-tree` flags for all git commands targeting the main repository. Default git operations routed to the worktree, which has a sparse checkout.

## User Setup Required

External services require API keys for integration testing. The test suite mocks all cloud APIs, so keys are not needed for running tests. For live usage:
- `LISA_OPENAI_API_KEY` - OpenAI Dashboard -> API keys -> Create new secret key
- `LISA_ANTHROPIC_API_KEY` - Anthropic Console -> API Keys -> Create Key

## Next Phase Readiness
- STT and LLM intent services are ready for the pipeline orchestrator (02-03) to chain together
- Both services are independently testable with mocked APIs
- Settings class has all fields needed for TTS (tts_model_path, tts_output_dir) and voice pipeline config
- DeviceIntent dataclass provides the structured contract between LLM intent parsing and device execution

## Self-Check: PASSED

- All 6 created/modified files verified on disk
- All 3 commits (9c1b09d, 0b8a9cd, de056b4) verified in git log
- All 77 tests pass

---
*Phase: 02-voice-pipeline*
*Completed: 2026-04-11*
