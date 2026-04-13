# Deferred Items (260413-jwo)

Items discovered during execution that are out of scope for the current quick task.

## Pre-existing test failures in tests/test_api_commands.py (4 tests)

**Failing tests:**
- `test_text_command_turn_on_bedroom_lamp`
- `test_text_command_turn_off`
- `test_text_command_unknown_pattern_rejected`
- `test_text_command_no_matching_device_rejected`

**Root cause:** These integration tests inject the real `VoicePipeline` (with a
real `LLMIntentService`), and the test process loads `ANTHROPIC_API_KEY` from
`backend/.env`. The configured key currently has an insufficient credit
balance, so `parse_intent` raises `LLMError("Intent parsing failed: Error code:
400 - ... credit balance is too low ...")` before the tests can reach their
expected success/rejected branches.

Confirmed pre-existing by stashing this task's changes and running the same
tests against `39db171^` -- failures reproduce identically. Not caused by
db.py or api/commands.py edits in 260413-jwo.

Task 1's log enrichment is what surfaced the actual cause (previously the log
said only "LLM connection error for input: ..." with no detail), which is a
useful side benefit of this quick task.

**Suggested fix (future work, not 260413-jwo scope):**
Either:
1. Replenish Anthropic credits on the key in `backend/.env`, or
2. Mock `LLMIntentService.parse_intent` in `tests/test_api_commands.py` so
   these tests do not hit a live cloud API (preferred for test isolation /
   CI reliability -- they should never have been calling the real API in
   the first place).

Option 2 is the right long-term answer per CLAUDE.md ("reproducible local
dev loop is more important than Pi-only polish") but is beyond the narrow
scope of this quick task.
