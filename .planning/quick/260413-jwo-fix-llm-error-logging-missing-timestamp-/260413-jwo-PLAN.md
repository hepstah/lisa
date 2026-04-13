---
phase: quick
plan: 260413-jwo
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/lisa/services/voice_pipeline.py
  - backend/lisa/api/commands.py
  - backend/lisa/db.py
autonomous: true
requirements:
  - QUICK-260413-JWO-01  # Enrich LLM error log with exception details
  - QUICK-260413-JWO-02  # Add ISO-8601 UTC timestamp to command_logged broadcast dicts
  - QUICK-260413-JWO-03  # Switch SQLite default timestamps to ISO-8601 UTC (strftime)

must_haves:
  truths:
    - "When LLMError is raised during process_text, the warning log line includes the exception's string (not just the raw input)."
    - "Every command result dict returned by /api/commands/text and by _log_unknown / _log_no_match carries a 'timestamp' field formatted as ISO-8601 UTC with trailing 'Z'."
    - "New rows inserted into command_log (and devices, settings) get a default timestamp value in ISO-8601 UTC form matching strftime('%Y-%m-%dT%H:%M:%fZ','now')."
    - "The React CommandHistory component receives a timestamp that new Date() can parse in Chrome, Firefox, and Safari (no 'Invalid Date')."
    - "Existing backend tests in backend/tests/ remain green."
  artifacts:
    - path: "backend/lisa/services/voice_pipeline.py"
      provides: "LLM error branch that logs the exception message alongside the raw input"
      contains: "except LLMError as"
    - path: "backend/lisa/api/commands.py"
      provides: "Text command endpoint + _log_unknown/_log_no_match helpers that stamp each broadcast dict with an ISO-8601 UTC timestamp"
      contains: "datetime.now(timezone.utc).isoformat"
    - path: "backend/lisa/db.py"
      provides: "Schema with ISO-8601 UTC default timestamps for command_log, devices, settings"
      contains: "strftime('%Y-%m-%dT%H:%M:%fZ','now')"
  key_links:
    - from: "backend/lisa/api/commands.py"
      to: "dashboard/src/components/CommandHistory.tsx"
      via: "command_logged WebSocket broadcast dict 'timestamp' field"
      pattern: "\"timestamp\":\\s*datetime\\.now\\(timezone\\.utc\\)\\.isoformat"
    - from: "backend/lisa/db.py"
      to: "backend/lisa/api/commands.py (GET /history reader at lines 22-36)"
      via: "command_log.timestamp column string format"
      pattern: "strftime\\('%Y-%m-%dT%H:%M:%fZ','now'\\)"
---

<objective>
Three targeted bug fixes diagnosed by the user against the current voice pipeline + dashboard flow:

1. LLM errors are being logged without the exception, which hid a real Anthropic 401 AuthenticationError behind a generic "LLM connection error" warning.
2. The /api/commands/text endpoint (and its fallback _log_unknown / _log_no_match helpers) broadcast command_logged WebSocket events whose payload lacks a 'timestamp' field, so the dashboard calls `new Date(undefined)` and renders "Invalid Date NaN:NaN".
3. The SQLite schema defaults timestamps with `datetime('now')`, which yields `"YYYY-MM-DD HH:MM:SS"`. Firefox and Safari's `new Date()` reject that format, so even history reads from the DB render as "Invalid Date" on those browsers.

Purpose: Restore accurate LLM diagnostics and make command history timestamps parseable in all browsers, without expanding scope, touching the frontend, or refactoring adjacent code. The same ISO-8601 UTC format must be used in both the live broadcast path and the DB default so historical reads and live broadcasts look identical to the frontend.

Output: Three small, coherent patches across voice_pipeline.py, api/commands.py, and db.py. Existing tests stay green; no frontend changes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md
@backend/lisa/services/voice_pipeline.py
@backend/lisa/api/commands.py
@backend/lisa/db.py
@dashboard/src/components/CommandHistory.tsx
@backend/tests/test_voice_pipeline.py
@backend/tests/test_api_commands.py

<interfaces>
<!-- Key context the executor needs. Extracted from the target files. -->

voice_pipeline.py line 72-73 (current, too opaque):
```python
except LLMError:
    self._log.warning("LLM connection error for input: %s", text)
```
Bug: if Anthropic returns 401 AuthenticationError, the real reason is swallowed.

api/commands.py:
  - text_command() result dicts flow through `voice_pipeline.process_text` (which returns device_service logs WITHOUT a timestamp), and through the local fallback helpers `_log_unknown` (lines 144-162) and `_log_no_match` (lines 165-183). All three paths build result dicts with NO 'timestamp' key, then call:
      await manager.broadcast({"type": "command_logged", "command": result})
  - The pipeline-error insert branch (lines 54-75) also needs to set `result["timestamp"]` before broadcasting, so the broadcast matches what GET /history returns for the same row.
  - GET /history (lines 22-36) reads `r["timestamp"]` straight from the DB column. No code change needed there, but after the db.py fix new rows will come back in ISO-8601 UTC form; the pydantic CommandRecord.timestamp is `str`, so any ISO string is accepted.

db.py current defaults (lines 21, 37, 44):
```sql
timestamp TEXT NOT NULL DEFAULT (datetime('now'))        -- command_log
added_at  TEXT NOT NULL DEFAULT (datetime('now'))        -- devices
updated_at TEXT NOT NULL DEFAULT (datetime('now'))       -- settings
```
Required replacement (all three):
```sql
DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
```
This yields e.g. "2026-04-13T18:22:07.412Z", which `new Date(...)` parses in Chrome, Firefox, and Safari. The 'Z' is a literal character, not a strftime code, so SQLite emits it verbatim.

Frontend consumer (dashboard/src/components/CommandHistory.tsx line 19-34): calls `new Date(timestamp)` then formats hours/minutes. Any valid ISO-8601 string works. No frontend edit required.

Python timestamp builder for the broadcast path (use in api/commands.py):
```python
from datetime import datetime, timezone
# ...
"timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
```
Rationale: `datetime.now(timezone.utc).isoformat()` yields `"2026-04-13T18:22:07.412345+00:00"`. Replacing `+00:00` with `Z` matches the DB column format (`...Z`). Both formats parse identically in every major browser, but using identical shapes avoids subtle rendering drift between a live broadcast row and the same row re-read from /history.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Enrich LLMError log line in voice_pipeline.py</name>
  <files>backend/lisa/services/voice_pipeline.py, backend/tests/test_voice_pipeline.py</files>
  <action>
In backend/lisa/services/voice_pipeline.py, edit the `except LLMError:` branch inside `process_text` (currently lines 72-73). Change the `except` clause to bind the exception and include it in the warning message so Anthropic auth errors and similar are visible in logs. Replace:

```python
except LLMError:
    self._log.warning("LLM connection error for input: %s", text)
```

with:

```python
except LLMError as exc:
    self._log.warning("LLM error for input: %s: %s", text, exc)
```

Do not change any other behavior: still `await self._tts.speak(MSG_NO_INTERNET)` and still return the same error dict (`status="error"`, `error_stage="llm"`, `error_message=MSG_NO_INTERNET`, `raw_input=text`, `tts_spoken=True`). Do not alter the LLMTimeoutError branch -- only the bare LLMError branch is in scope.

Verify that `backend/tests/test_voice_pipeline.py::test_process_text_llm_connection_error` still passes. That test raises `LLMError("Cannot reach intent processing service")` and only asserts on the TTS call and returned dict shape, so the log format change should not break it. If it does break, the fix is to leave the assertions alone and only update the log format -- do NOT weaken test assertions.

No other files touched. Per CLAUDE.md: ASCII-only punctuation, no opportunistic cleanup.
  </action>
  <verify>
    <automated>cd backend && uv run pytest tests/test_voice_pipeline.py -x -q</automated>
  </verify>
  <done>
    - `except LLMError as exc:` binding exists in voice_pipeline.py
    - Warning log line now includes `exc` via `%s` formatter
    - `test_process_text_llm_connection_error` and all other voice_pipeline tests pass
    - No other lines in voice_pipeline.py changed
  </done>
</task>

<task type="auto">
  <name>Task 2: Switch db.py schema defaults to ISO-8601 UTC via strftime</name>
  <files>backend/lisa/db.py, backend/tests/test_config_db.py</files>
  <action>
In backend/lisa/db.py, replace all three occurrences of `DEFAULT (datetime('now'))` with `DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))`. Affects:

  - line 21: `command_log.timestamp`
  - line 37: `devices.added_at`
  - line 44: `settings.updated_at`

Do NOT add a migration for existing rows. Existing rows keep whatever format they were inserted with; the user has confirmed there is very little history. Do NOT touch the PRAGMA lines, `get_db()`, or anything outside the `CREATE TABLE IF NOT EXISTS` blocks.

Rationale: `strftime('%Y-%m-%dT%H:%M:%fZ','now')` emits e.g. `"2026-04-13T18:22:07.412Z"`, which `new Date(...)` parses in Chrome, Firefox, and Safari. The current `datetime('now')` emits `"2026-04-13 18:22:07"` (space separator, no TZ), which Firefox and Safari reject. The literal `Z` in the format string is passed through by SQLite verbatim -- it is not a strftime code.

Compatibility check after edit (no code change needed, just verify manually):
  - backend/lisa/api/commands.py GET /history (lines 22-36) reads `r["timestamp"]` directly into `CommandRecord.timestamp: str`. Any non-empty string is valid.
  - Existing tests that insert via `db.execute(... INSERT INTO command_log ...)` without supplying a timestamp will now get the new format. Tests that only assert `status`, `device_id`, or `raw_input` are unaffected. If any test asserts on the exact timestamp string, narrow the assertion to `isinstance(row["timestamp"], str)` -- but first check; do not preemptively weaken.

Run both the narrow DB test file and the full api/commands integration suite to catch any hidden timestamp assertion.
  </action>
  <verify>
    <automated>cd backend && uv run pytest tests/test_config_db.py tests/test_api_commands.py -x -q</automated>
  </verify>
  <done>
    - All three `DEFAULT (datetime('now'))` clauses replaced with `DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))`
    - No other lines in db.py changed
    - test_config_db.py and test_api_commands.py pass
    - A fresh row inserted into command_log has a `timestamp` string matching `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$` (sanity check: `python -c "import aiosqlite,asyncio; ..."` or inspect via the running app)
  </done>
</task>

<task type="auto">
  <name>Task 3: Stamp command_logged broadcast dicts with ISO-8601 UTC timestamp in api/commands.py</name>
  <files>backend/lisa/api/commands.py, backend/tests/test_api_commands.py</files>
  <action>
In backend/lisa/api/commands.py, ensure every `command_logged` WebSocket broadcast payload has a `timestamp` field formatted as ISO-8601 UTC with trailing `Z`, matching the DB column format from Task 2.

Add imports at the top of the file (keep existing imports):

```python
from datetime import datetime, timezone
```

Define a small module-level helper just below the imports (keep it local; do not export or move to a utils module -- per CLAUDE.md: no premature abstractions):

```python
def _now_iso() -> str:
    """ISO-8601 UTC timestamp with trailing Z, matching db.py defaults."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
```

Then stamp each of the three broadcast paths:

1. Voice-pipeline path (around current lines 54-78 in `text_command`):
   After the `if "id" not in result ...` DB insert block and before `await manager.broadcast(...)`, set:
   ```python
   result.setdefault("timestamp", _now_iso())
   ```
   Use `setdefault` so that if a future voice_pipeline change ever starts returning its own timestamp we do not clobber it. Place this line BEFORE the broadcast call, unconditionally (i.e. outside the `if "id" not in result` block), so BOTH the success path (where device_service logged the row and result already has `id` but no `timestamp`) AND the pipeline-error path get stamped.

2. `_log_unknown` helper (around current lines 144-162):
   Add `"timestamp": _now_iso(),` as the first key of the returned dict (after `"id"` is fine, but stylistically put it at the top so it is obvious). The returned dict currently has keys: id, source, raw_input, status, error_message, error_stage.

3. `_log_no_match` helper (around current lines 165-183):
   Same treatment. Add `"timestamp": _now_iso(),` to the returned dict.

Do NOT change the DB INSERT statements -- they already rely on the column DEFAULT from Task 2, so the stamped broadcast value and the stored row value will be very close (within a few ms) but both ISO-8601 UTC, which is sufficient. Do NOT try to read the DB row back just to recover the exact default value -- that adds a round trip and complexity for no user-visible benefit.

Do NOT add a `timestamp` field to `TextCommandRequest` or any other request model. Do NOT touch `CommandRecord` (its `timestamp: str` already accepts the new format). Do NOT modify GET /history -- it reads the DB column directly and is unaffected.

Do NOT touch the frontend. The dashboard's `CommandHistory.formatTime` already calls `new Date(timestamp)` and will now receive a parseable string.

After the edits, run the full backend test suite. Pay particular attention to `test_api_commands.py` -- its existing assertions do not check for a `timestamp` field, so adding one should be non-breaking. If any test fails due to an unexpected extra key (e.g. strict equality on the whole dict), update that specific assertion to include the new key or switch to per-key asserts; do not weaken the fix.

Per CLAUDE.md: ASCII-only punctuation, narrow scope, no refactors beyond these three broadcast sites.
  </action>
  <verify>
    <automated>cd backend && uv run pytest tests/test_api_commands.py tests/test_ws.py tests/test_api_voice.py -x -q</automated>
  </verify>
  <done>
    - `datetime`/`timezone` imported in api/commands.py
    - `_now_iso()` helper defined once, at module level
    - `text_command` voice-pipeline branch calls `result.setdefault("timestamp", _now_iso())` before `manager.broadcast(...)`
    - `_log_unknown` return dict includes `"timestamp": _now_iso()`
    - `_log_no_match` return dict includes `"timestamp": _now_iso()`
    - All three broadcast payloads, when inspected in a live WebSocket session, carry a `timestamp` key like `"2026-04-13T18:22:07.412345Z"`
    - `test_api_commands.py`, `test_ws.py`, and `test_api_voice.py` all pass
    - Dashboard CommandHistory renders real times (not "Invalid Date NaN:NaN") after triggering an unknown command, a no-match command, and a successful text command (quick manual check once backend restarts)
  </done>
</task>

</tasks>

<verification>
After all three tasks, run the full backend suite to confirm nothing regressed:

```bash
cd backend && uv run pytest -x -q
```

Then do a 60-second live sanity check with the dashboard open:

1. Start backend + dashboard.
2. From the text command box, send: `reboot everything` (should be rejected via `_log_unknown` path).
3. Send: `turn on the nonexistent device` (should be rejected via `_log_no_match` path).
4. Send: `turn on the bedroom lamp` (should succeed via voice pipeline or Phase 1 fallback).
5. In each case, confirm the Command History row shows a real HH:MM time, not "Invalid Date NaN:NaN", in BOTH Chrome and (if available) Firefox.
6. Temporarily set an invalid `ANTHROPIC_API_KEY` and issue a text command. Confirm the backend log now shows a warning line of the form `LLM error for input: <text>: <AuthenticationError details>` rather than the opaque `LLM connection error for input: <text>`.

No frontend edits. No new dependencies. No schema migration.
</verification>

<success_criteria>
- Backend test suite (`cd backend && uv run pytest -x -q`) is green.
- LLM error warning log line includes the exception message.
- `command_logged` WebSocket payloads always carry a `timestamp` string in ISO-8601 UTC form with trailing `Z`.
- New rows in `command_log`, `devices`, and `settings` get ISO-8601 UTC default timestamps.
- Dashboard `CommandHistory` shows real times for both historical rows (after the first new insert) and live-broadcast rows in Chrome and Firefox.
- No changes to: frontend files, CommandRecord model, request models, GET /history reader, voice_pipeline behavior other than the log line, or the three files' surrounding code.
</success_criteria>

<output>
After completion, create `.planning/quick/260413-jwo-fix-llm-error-logging-missing-timestamp-/260413-jwo-SUMMARY.md` with:
  - Exact diffs applied to voice_pipeline.py, api/commands.py, db.py
  - Test command output (pytest summary line)
  - Notes on any test assertions that had to be touched (expected: none)
  - Confirmation that the frontend was NOT modified
</output>
