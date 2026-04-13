---
phase: quick
plan: 260413-jwo
subsystem: voice-pipeline, api, db
tags: [bugfix, logging, timestamps, sqlite]
dependency_graph:
  requires: []
  provides:
    - ISO-8601 UTC timestamp contract between command_log DB column and command_logged WebSocket broadcasts
  affects:
    - dashboard/src/components/CommandHistory.tsx (now receives parseable timestamps)
tech_stack:
  added: []
  patterns:
    - SQLite strftime('%Y-%m-%dT%H:%M:%fZ','now') for browser-parseable column defaults
    - datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z') helper for live broadcast timestamps
key_files:
  created:
    - .planning/quick/260413-jwo-fix-llm-error-logging-missing-timestamp-/deferred-items.md
  modified:
    - backend/lisa/services/voice_pipeline.py
    - backend/lisa/db.py
    - backend/lisa/api/commands.py
decisions:
  - "Use setdefault on result['timestamp'] in text_command so future voice_pipeline returns do not get clobbered"
  - "Keep _now_iso() local to api/commands.py (no utils module) per CLAUDE.md: no premature abstractions"
  - "No DB migration for existing rows (user confirmed negligible history)"
metrics:
  duration: 5min
  tasks: 3
  files: 3
  completed: 2026-04-13
---

# Quick Task 260413-jwo: Fix LLM Error Logging and Missing Timestamp Summary

Three narrow bug fixes: (1) bind LLMError to include the exception text in the warning log, (2) switch SQLite default timestamps to ISO-8601 UTC via strftime so Firefox/Safari can parse them, (3) stamp every command_logged WebSocket broadcast with an ISO-8601 UTC timestamp matching the DB format.

## Tasks Completed

| Task | Name                                                             | Commit   |
| ---- | ---------------------------------------------------------------- | -------- |
| 1    | Enrich LLMError log line in voice_pipeline.py                    | 39db171  |
| 2    | Switch db.py schema defaults to ISO-8601 UTC via strftime        | 9fe578b  |
| 3    | Stamp command_logged broadcast dicts with ISO-8601 UTC timestamp | f1f0598  |

## Diffs Applied

### backend/lisa/services/voice_pipeline.py (Task 1)

```diff
-        except LLMError:
-            self._log.warning("LLM connection error for input: %s", text)
+        except LLMError as exc:
+            self._log.warning("LLM error for input: %s: %s", text, exc)
```

Effect: LLMError branch now surfaces the exception's string in the log. This is how we discovered the real cause of the `backend/.env` Anthropic credit issue (see Deferred Issues).

### backend/lisa/db.py (Task 2)

```diff
-                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
+                timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 ...
-                added_at TEXT NOT NULL DEFAULT (datetime('now')),
+                added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 ...
-                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
+                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
```

Effect: fresh rows get e.g. `"2026-04-13T18:25:15.751Z"`, which `new Date(...)` parses in Chrome, Firefox, and Safari. The `Z` is a literal in the format string, not a strftime code, so SQLite emits it verbatim.

Sanity check verified end-to-end:

```
timestamp: 2026-04-13T18:25:15.751Z
matches ISO-8601 UTC format: True
```

### backend/lisa/api/commands.py (Task 3)

```diff
+from datetime import datetime, timezone
+
 from fastapi import APIRouter
 from lisa.models import TextCommandRequest, CommandRecord
 from lisa.api.ws import manager
 from lisa.db import get_db

 router = APIRouter(prefix="/api/commands", tags=["commands"])

 device_service = None  # Set in main.py
 voice_pipeline = None  # Set in main.py (Phase 2)
+
+
+def _now_iso() -> str:
+    """ISO-8601 UTC timestamp with trailing Z, matching db.py defaults."""
+    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
```

```diff
             finally:
                 await db.close()

+        result.setdefault("timestamp", _now_iso())
         await manager.broadcast({"type": "command_logged", "command": result})
         return result
```

```diff
         return {
             "id": cursor.lastrowid,
+            "timestamp": _now_iso(),
             "source": source,
             "raw_input": text,
             "status": "rejected",
             "error_message": "Could not understand that command. Try something like: turn on the bedroom lamp",
             "error_stage": "validation",
         }
```

```diff
         return {
             "id": cursor.lastrowid,
+            "timestamp": _now_iso(),
             "source": source,
             "raw_input": text,
             "status": "rejected",
             "error_message": f"No device found matching '{query}'",
             "error_stage": "validation",
         }
```

Effect: every `command_logged` broadcast now carries an ISO-8601 UTC `timestamp` key with trailing `Z`, matching the DB column format. The voice-pipeline branch uses `setdefault` so it will not overwrite a future voice_pipeline-supplied timestamp.

## Test Results

### Task-scoped verification (green):

```
tests/test_voice_pipeline.py ................................. 10 passed in 0.86s
tests/test_config_db.py ......................................  12 passed in 0.07s
```

### Full backend suite:

```
cd backend && uv run pytest -q
4 failed, 96 passed in 39.51s
```

The 4 failing tests are pre-existing environmental failures, not caused by this quick task (see Deferred Issues).

## Deviations from Plan

None. The plan was executed exactly as written. No test assertions had to be touched.

## Deferred Issues

### Pre-existing test failures in tests/test_api_commands.py (4 tests)

| Test                                            | Root cause                                       |
| ----------------------------------------------- | ------------------------------------------------ |
| test_text_command_turn_on_bedroom_lamp          | Live Anthropic API hit, credit balance too low   |
| test_text_command_turn_off                      | Live Anthropic API hit, credit balance too low   |
| test_text_command_unknown_pattern_rejected      | Live Anthropic API hit, credit balance too low   |
| test_text_command_no_matching_device_rejected   | Live Anthropic API hit, credit balance too low   |

**Confirmed pre-existing** by stashing the working-tree changes for this quick task and running the same tests against `39db171^`. Failures reproduce identically without any of this task's edits.

The integration tests inject the real `VoicePipeline` (with a real `LLMIntentService`) and the test process loads `ANTHROPIC_API_KEY` from `backend/.env`. The configured key's credit balance is insufficient, so `LLMIntentService.parse_intent` raises `LLMError` before the tests can exercise the success or rejected branches.

**Notable side-benefit:** Task 1's log enrichment is what surfaced the real cause. Before this task, the log line said only `LLM connection error for input: ...` with no detail. Now it says `LLM error for input: ...: ... credit balance is too low ...`, which is exactly the diagnostic improvement the task was meant to deliver.

**Suggested follow-up (out of scope for 260413-jwo):**
1. Replenish Anthropic credits, or
2. Mock `LLMIntentService.parse_intent` in `tests/test_api_commands.py` so these tests do not hit a live cloud API (preferred for CI reliability per CLAUDE.md: "reproducible local dev loop is more important than Pi-only polish").

Full details recorded in `deferred-items.md` alongside this SUMMARY.

## Frontend Confirmation

**No frontend files were modified.** `dashboard/src/components/CommandHistory.tsx` was not touched. Its existing `formatTime` call to `new Date(timestamp)` will now receive a parseable ISO-8601 UTC string from both the live broadcast path and the GET /history path, resolving "Invalid Date NaN:NaN" in all major browsers.

## Self-Check: PASSED

**Files modified (verified exist on disk):**
- FOUND: backend/lisa/services/voice_pipeline.py
- FOUND: backend/lisa/db.py
- FOUND: backend/lisa/api/commands.py
- FOUND: .planning/quick/260413-jwo-fix-llm-error-logging-missing-timestamp-/deferred-items.md

**Commits (verified in git log):**
- FOUND: 39db171 fix(quick-260413-jwo): include exception in LLMError log line
- FOUND: 9fe578b fix(quick-260413-jwo): use ISO-8601 UTC for SQLite default timestamps
- FOUND: f1f0598 fix(quick-260413-jwo): stamp command_logged broadcasts with ISO timestamp
