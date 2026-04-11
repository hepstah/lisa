# Phase 2: Voice Pipeline - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Voice pipeline from wake word detection through spoken response. A spoken command after "Hey Lisa" is captured, transcribed via cloud STT, parsed into a structured intent by a cloud LLM, and answered with local TTS. Every failure mode produces an audible spoken error. Dev-mode paths allow testing without audio hardware.

</domain>

<decisions>
## Implementation Decisions

### Cloud Services & Intent Parsing
- **D-09:** Claude API (claude-haiku-4-5) is the LLM for intent parsing -- fast, cheap, excellent structured output via tool_use
- **D-10:** OpenAI Whisper API is the STT provider -- $0.006/min, best accuracy (per research recommendation)
- **D-11:** Intent response format is structured JSON via tool_use -- LLM returns {device_id, action}, no parsing needed
- **D-12:** API keys configured as LISA_OPENAI_API_KEY and LISA_ANTHROPIC_API_KEY env vars (same LISA_ prefix pattern as Phase 1)

### Dev-Mode Voice Pipeline
- **D-13:** Text injection via existing DASH-04 bypasses wake word + STT -- text commands go directly to LLM intent parsing in dev mode
- **D-14:** TTS output saves to .wav file in dev mode -- log what would be spoken, save audio for manual playback
- **D-15:** Wake word skipped in dev mode -- command injection starts at STT/LLM stage. Wake word only runs on Pi with real mic
- **D-16:** Each pipeline stage testable independently -- STT with .wav file, LLM with text, TTS with text. Integration test chains with mocked inputs

### Error Feedback & Timeouts
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Scope
- `.planning/PROJECT.md` -- V1 product definition, constraints, validation criteria
- `.planning/REQUIREMENTS.md` -- Phase 2 requirements: VOICE-01..05, ERR-01, ERR-03
- `CLAUDE.md` -- Multi-agent rules, default biases, current project constraints

### Prior Phase
- `.planning/phases/01-foundation/01-CONTEXT.md` -- Phase 1 decisions (D-01 through D-08)
- `.planning/phases/01-foundation/01-VERIFICATION.md` -- Phase 1 verification (what exists)

### Research
- `.planning/research/STACK.md` -- Technology recommendations for voice components
- `.planning/research/ARCHITECTURE.md` -- Component boundaries and data flow

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/lisa/services/device_service.py` -- DeviceService.execute_command() is the target for LLM intent output
- `backend/lisa/api/commands.py` -- Text command parsing (POST /api/commands/text) already parses "turn on the bedroom lamp" into device_id + action
- `backend/lisa/models.py` -- TextCommandRequest, DeviceControlRequest models
- `backend/lisa/config.py` -- Settings class with LISA_ env prefix (extend with new API key fields)

### Established Patterns
- Async Python with FastAPI
- pydantic-settings for configuration
- FakeAdapter pattern for dev-mode testing
- SQLite command_log for all command results

### Integration Points
- Voice pipeline output connects to DeviceService.execute_command()
- Voice pipeline status should be broadcastable via existing WebSocket (Phase 3)
- Text command API (/api/commands/text) already does intent parsing -- voice pipeline adds audio capture + STT before the same parsing step

</code_context>

<specifics>
## Specific Ideas

- The existing text command parser in commands.py already does basic "turn on the bedroom lamp" parsing. The LLM intent parser should produce the same output format so both paths (text and voice) feed into DeviceService.execute_command() identically.
- CLAUDE.md emphasizes dev-mode trigger paths over hardware implementation. The voice pipeline should be fully testable via text injection without any audio hardware.
- 3-second timeouts are tighter than the 5-second ERR-03 requirement -- user prefers faster failure feedback.

</specifics>

<deferred>
## Deferred Ideas

- Wake word threshold calibration UI (ADV-02) -- v2
- Custom wake word training (ADV-03) -- v2
- "Working on it" audio cue for slow responses (CONV-02) -- v2
- Streaming STT for faster response (Deepgram alternative) -- v2

</deferred>

---

*Phase: 02-voice-pipeline*
*Context gathered: 2026-04-11*
