# Pre-Hardware Enhancements: Test Isolation + LLM Debug Capture

**Date:** 2026-04-13
**Status:** Approved, pending implementation
**Scope:** Backend (Python/FastAPI) + dashboard (React/TypeScript)
**Gates:** Milestone v1.0 complete, pre hardware bring-up

## Context

Lisa v1.0 shipped in dev mode: fake device adapter, text-injected commands, voice pipeline wired end-to-end but never exercised against real audio or real radios. Before starting the hardware bring-up (Pi 5, real mic, real lamp) we want two targeted software enhancements that make the bring-up loop safer:

1. The test suite currently depends on live Anthropic credits. Four tests in `test_api_commands.py::TestTextCommand::*` fail offline or when the account is out of credits. That's a bad foundation for a phase where remote-ness and CI-ness will matter more.
2. The LLM intent layer is a black box at runtime. When Claude misroutes a command, there's no trail of what it saw or decided -- only the final success/rejected row in `command_log`. On real audio that ambiguity is going to hurt.

This spec addresses both. Neither expands product scope; both sharpen the debugging loop.

## Goals

- Backend tests run green offline with zero real Anthropic calls.
- In dev mode, every LLM intent call records transcribed input, the device list Claude saw, its decision, token usage, and stop reason, surfaced in the dashboard's existing expanded command history row.
- In production (non-dev) deployments, zero new behaviour, zero new data stored.
- No changes to product surface (no new commands, no dimming, no scenes, no alias editing).

## Non-Goals

- Per-stage latency instrumentation (STT / LLM / TTS breakdown). Separate future effort.
- Full reproducibility capture (system prompt + tool schema + raw response). Out of scope per Q2.
- Retention / pruning of debug data. Out of scope per Q3 -- dev mode only, unbounded is acceptable.
- Production-mode capture with auto-prune.
- Refactoring the STT test path (already mocked cleanly).
- Any frontend feature beyond the inline debug block in the existing expanded row.
- Phase-1 fallback parser path (no LLM involved, no debug to capture).

---

## Part A -- Test Isolation from Anthropic

### Problem

`backend/tests/test_api_commands.py::TestTextCommand::*` drives `voice_pipeline.process_text`, which constructs a real `AsyncAnthropic` client and hits the live API. When credits are exhausted or the network is down, four tests fail even though production code is correct. This was surfaced during quick task `260413-jwo` when the user's Anthropic workspace ran out of credit.

### Design

**New fixture** in `backend/tests/conftest.py`:

```python
@pytest.fixture
def mock_llm_intent(monkeypatch):
    """
    Monkeypatches LLMIntentService.parse_intent with an AsyncMock that
    routes responses by input text. Default return is IntentResult(None, {...}).

    Usage:
        def test_foo(mock_llm_intent):
            mock_llm_intent.set_response(
                "turn on the bedroom lamp",
                intent=DeviceIntent(device_id="kasa-1", action="turn_on",
                                    confirmation="Turning on the bedroom lamp"),
            )
    """
```

**Characteristics:**

- Fixture returns a helper object with a `.set_response(text, intent=None, raise_=None)` method.
- Default fallback: unknown intent (`IntentResult(None, {...})`).
- Supports simulating `LLMTimeoutError` / `LLMError` via `raise_` to keep error-path tests covered without real network.
- Matches the existing pattern in `test_stt_service.py` which already uses a fake OpenAI client.

**Session-level safety net** in `conftest.py`:

```python
@pytest.fixture(autouse=True, scope="session")
def _fail_on_live_anthropic_key(monkeypatch_session):
    """
    If any test instantiates AsyncAnthropic with a live key
    (prefix 'sk-ant-'), fail loudly. Dummy keys like 'test-key-123'
    pass through so existing unit tests keep working.
    """
```

- Implemented via monkeypatching `anthropic.AsyncAnthropic.__init__` to inspect the `api_key` argument.
- Dummy keys (anything not starting with `sk-ant-`) are allowed. Live keys raise.
- Does not conflict with `test_llm_intent_service.py` which already uses `"test-key-123"`.
- Belt and suspenders -- this is what would have caught the "credits ran out" failure mode earlier.

### Test migrations

Four tests in `test_api_commands.py::TestTextCommand::*` take the `mock_llm_intent` fixture and call `.set_response(...)` as needed. No production code changes.

### Surface area

- ~40 lines added to `conftest.py`.
- 4 test functions updated.
- Zero production code touched.

### Acceptance

- `uv run pytest backend/ -x -q` passes with no network access.
- `uv run pytest backend/ -x -q` passes with `LISA_ANTHROPIC_API_KEY` unset.
- A test that forgets the fixture and tries to construct a real `AsyncAnthropic` client fails with a clear message.

---

## Part B -- Dev-Mode LLM Debug Capture

### Problem

When the LLM picks the wrong device or refuses to call the tool, the only evidence in the DB is the final `command_log` row with `raw_input` and `error_stage = "intent"`. Nothing about what Claude saw or decided. Reproducing the issue requires re-running the same request, which is flaky for non-deterministic models.

### Design

In dev mode only (`settings.dev_mode == True`), every LLM intent call records a compact debug blob and stores it as JSON in a new nullable column on `command_log`. The dashboard renders it in the existing expanded row when present.

### Data shape

```json
{
  "input_text": "how are you",
  "devices_seen": [
    {"device_id": "kasa-1", "alias": "Bedroom Lamp", "is_on": false}
  ],
  "decision": { "tool_used": false, "text": "I'm a smart home assistant..." },
  "usage": { "input_tokens": 412, "output_tokens": 23 },
  "stop_reason": "end_turn"
}
```

**Decision variants:**

- Tool-use: `{ "tool_used": true, "device_id": "...", "action": "...", "confirmation": "..." }`
- Plain text (no tool): `{ "tool_used": false, "text": "..." }`
- Error: `{ "error": "APIConnectionError: ..." }` -- usage and stop_reason omitted

### Backend changes

#### `backend/lisa/services/llm_intent_service.py`

New dataclass:

```python
@dataclass
class IntentResult:
    intent: Optional[DeviceIntent]
    debug: dict
```

`parse_intent` return type changes from `Optional[DeviceIntent]` to `IntentResult`. Debug is always populated. On `LLMTimeoutError` and `LLMError` the exception still raises -- the voice pipeline catches them and builds a partial debug record (just `input_text` + `error`) itself.

#### `backend/lisa/services/voice_pipeline.py`

- Import `settings` from `lisa.config`.
- After `parse_intent`, unpack `result.intent` / `result.debug`.
- When `settings.dev_mode`, `json.dumps(result.debug)` and thread the string through `execute_command(..., llm_debug=...)` and through the two pipeline-error INSERTs.
- Error paths build their own small debug dict: `{"input_text": text, "error": str(exc)}`.
- Unknown intent path uses `result.debug` as-is.
- When `dev_mode` is false, pass `None` -- column stays null.

#### `backend/lisa/services/device_service.py`

- `execute_command(..., llm_debug: str | None = None)` -- opaque JSON string passthrough.
- `_log_command(..., llm_debug: str | None = None)` -- INSERT gets one more column. DeviceService never inspects the value.

#### `backend/lisa/api/commands.py`

- Pipeline-error INSERT (inside the `if "id" not in result` branch) adds the `llm_debug` column.
- `_log_unknown` and `_log_no_match` stay unchanged (Phase-1 fallback parser, no LLM involved).
- `get_command_history` reads the new column and `json.loads` it into the response dict.

#### `backend/lisa/db.py`

- Add `llm_debug TEXT` to the `command_log` CREATE TABLE.
- Add idempotent migration after the `executescript` block:

```python
try:
    await db.execute("ALTER TABLE command_log ADD COLUMN llm_debug TEXT")
except aiosqlite.OperationalError:
    pass  # column already exists
```

- No migration framework. Single-home dev DB, acceptable.

#### `backend/lisa/models.py`

- `CommandRecord.llm_debug: Optional[dict] = None`. Pydantic serializes/deserializes as a dict on the wire.

### Frontend changes

#### `dashboard/src/api/types.ts`

```typescript
export interface LlmDebug {
  input_text: string;
  devices_seen: Array<{ device_id: string; alias: string; is_on: boolean }>;
  decision:
    | { tool_used: true; device_id: string; action: string; confirmation: string }
    | { tool_used: false; text: string }
    | { error: string };
  usage?: { input_tokens: number; output_tokens: number };
  stop_reason?: string;
}

export interface CommandRecord {
  // ...existing fields...
  llm_debug?: LlmDebug | null;
}
```

#### `dashboard/src/components/CommandHistory.tsx`

Inside the existing `isExpanded` detail `TableRow`, when `cmd.llm_debug` is truthy, render a new subsection:

- Header: "LLM Debug" in the same style as "Full command:" etc.
- One-line decision summary:
  - Tool: `Tool: control_device(device=<id>, action=<action>)`
  - No tool: `No tool -- text: "<first 80 chars>"`
  - Error: `Error: <error string>`
- Stats row: `input <N> tok | output <N> tok | stop: <reason>` (hidden on error variant)
- Collapsible `<details>` element titled "Devices seen" containing the full `devices_seen` list as a small table.

Section is hidden entirely when `llm_debug` is null. Production dashboards never see it.

### Testing

- **`test_llm_intent_service.py::test_parse_intent_returns_debug_on_tool_use`** -- mocked Anthropic client returns a tool_use block; `IntentResult.debug.decision.tool_used` is True.
- **`test_llm_intent_service.py::test_parse_intent_returns_debug_on_text_response`** -- mocked client returns plain text; `IntentResult.debug.decision.tool_used` is False.
- **`test_voice_pipeline.py::test_dev_mode_captures_llm_debug`** -- `settings.dev_mode = True`, mock LLM, assert the dict returned by `process_text` contains a non-null `llm_debug` JSON string.
- **`test_voice_pipeline.py::test_prod_mode_skips_llm_debug`** -- `settings.dev_mode = False`, assert the column is null.
- **`test_api_commands.py`** -- the four migrated tests (from Part A) use the new `mock_llm_intent` fixture and assert the `llm_debug` round-trips through the history endpoint as a dict.

### Acceptance

- With `LISA_DEV_MODE=true`, submitting "hello" through the dashboard results in a `command_log` row with a non-null `llm_debug` column.
- Expanding that row in the dashboard shows the debug subsection with decision, token counts, stop reason, and collapsible device list.
- With `LISA_DEV_MODE=false`, the same submission results in `llm_debug = NULL` and the dashboard subsection is absent.
- `uv run pytest backend/` is green offline.

---

## Out of Scope Reminders

- No retention policy. Dev DB grows freely.
- No export / copy-to-clipboard button.
- No per-stage latency fields in the debug blob.
- No system prompt or tool schema capture.
- No impact on `_log_unknown` / `_log_no_match` helpers (Phase-1 parser only).

## Risks

- **Schema migration via try/except ALTER TABLE is informal.** Acceptable for a single-home SQLite DB; would not fly for a managed service. If we ever grow a migration framework we should fold this in.
- **The `_fail_on_real_anthropic` safety net could false-positive** if future code needs a real client for integration tests. Opt-out via a pytest marker is simple to add when needed.
- **`IntentResult` return type change is a backwards-incompatible API break** on `LLMIntentService.parse_intent`, but the only caller is `voice_pipeline.py` and the tests. Both are updated in this spec.

## Files Touched (estimate)

Backend:
- `backend/lisa/services/llm_intent_service.py` (+ ~25 lines)
- `backend/lisa/services/voice_pipeline.py` (+ ~30 lines)
- `backend/lisa/services/device_service.py` (+ ~5 lines, signature changes)
- `backend/lisa/api/commands.py` (+ ~10 lines)
- `backend/lisa/db.py` (+ ~8 lines, CREATE + idempotent ALTER)
- `backend/lisa/models.py` (+ ~3 lines)
- `backend/tests/conftest.py` (+ ~50 lines, new fixture + safety net)
- `backend/tests/test_api_commands.py` (~4 tests migrated)
- `backend/tests/test_llm_intent_service.py` (+ ~40 lines, new tests)
- `backend/tests/test_voice_pipeline.py` (+ ~40 lines, new tests)

Frontend:
- `dashboard/src/api/types.ts` (+ ~15 lines)
- `dashboard/src/components/CommandHistory.tsx` (+ ~40 lines, inline)

Total: ~12 files, ~250 lines added, zero deletions beyond signature changes.
