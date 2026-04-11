---
phase: 01-foundation
plan: 02
subsystem: api
tags: [fastapi, websocket, rest, httpx, async, text-commands]

# Dependency graph
requires:
  - phase: 01-foundation-01
    provides: DeviceAdapter interface, FakeAdapter, DeviceService, models, db, config, allowlist
provides:
  - REST endpoints for device listing, control, discovery, and manual addition
  - REST endpoints for command history and text command parsing
  - WebSocket ConnectionManager for real-time state broadcasts
  - FastAPI app with lifespan-based dependency injection
  - 21 API integration tests covering all endpoints
affects: [01-foundation-03, 02-integration, dashboard]

# Tech tracking
tech-stack:
  added: [asgi-lifespan, httpx-ws]
  patterns: [lifespan-based DI, module-level service injection, LifespanManager test pattern]

key-files:
  created:
    - backend/lisa/api/__init__.py
    - backend/lisa/api/ws.py
    - backend/lisa/api/devices.py
    - backend/lisa/api/commands.py
    - backend/lisa/main.py
    - backend/tests/test_api_devices.py
    - backend/tests/test_api_commands.py
    - backend/tests/test_ws.py
  modified:
    - backend/tests/conftest.py
    - backend/pyproject.toml
    - backend/uv.lock

key-decisions:
  - "Used LifespanManager from asgi-lifespan for test client to properly trigger FastAPI lifespan events"
  - "Used temp file DB instead of :memory: for tests because in-memory SQLite creates independent databases per connection"
  - "Used Starlette TestClient for WebSocket tests (synchronous) since httpx ASGITransport does not support WS upgrade"

patterns-established:
  - "Lifespan DI: services are created in lifespan() and injected as module-level globals into router modules"
  - "Test client pattern: LifespanManager wraps app, ASGITransport wraps manager.app, AsyncClient wraps transport"
  - "Text command parser: simple prefix-matching for Phase 1, replaced by LLM in Phase 2"

requirements-completed: [DEVICE-04, DASH-04, ERR-02]

# Metrics
duration: 6min
completed: 2026-04-11
---

# Phase 01 Plan 02: FastAPI REST API and WebSocket Layer Summary

**FastAPI REST API with device CRUD, text command parsing, WebSocket broadcasting, and 21 integration tests using LifespanManager-backed async client**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-11T17:53:36Z
- **Completed:** 2026-04-11T17:59:34Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- REST API endpoints for device listing, individual device state, control (turn on/off), discovery, and manual addition
- Text command endpoint with simple prefix parser matching "turn on/off [the] {alias}" against known device aliases
- WebSocket ConnectionManager broadcasting device state changes and command log events to all connected clients
- 21 new integration tests (10 device, 7 command, 4 WebSocket) all passing alongside 32 existing Plan 01 tests

## Task Commits

Each task was committed atomically:

1. **Task 1: WebSocket manager, REST endpoints, and FastAPI app wiring** - `f9f55e3` (feat)
2. **Task 2: API integration tests** - `ebfbca3` (test)

## Files Created/Modified
- `backend/lisa/api/__init__.py` - Package init for api module
- `backend/lisa/api/ws.py` - ConnectionManager with connect/disconnect/broadcast
- `backend/lisa/api/devices.py` - REST endpoints: list, get, control, discover, add
- `backend/lisa/api/commands.py` - REST endpoints: command history, text command with parser
- `backend/lisa/main.py` - FastAPI app with lifespan, router mounting, WebSocket endpoint
- `backend/tests/test_api_devices.py` - 10 tests for device endpoints
- `backend/tests/test_api_commands.py` - 7 tests for command endpoints
- `backend/tests/test_ws.py` - 4 tests for WebSocket and ConnectionManager
- `backend/tests/conftest.py` - Updated with async client fixture using LifespanManager
- `backend/pyproject.toml` - Added asgi-lifespan and httpx-ws dev dependencies
- `backend/uv.lock` - Updated lockfile

## Decisions Made
- Used LifespanManager (asgi-lifespan library) for test client because httpx AsyncClient with ASGITransport does not trigger FastAPI lifespan events, so device_service was never initialized
- Used temp file DB instead of :memory: for tests because SQLite in-memory mode creates independent databases per connection, causing "no such table" errors when multiple get_db() calls open separate connections
- Used Starlette's synchronous TestClient for WebSocket integration tests because httpx_ws cannot upgrade WS through ASGITransport properly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed in-memory SQLite test isolation**
- **Found during:** Task 2 (API integration tests)
- **Issue:** Tests using LISA_DB_PATH=:memory: failed with "no such table: command_log" because each aiosqlite.connect(":memory:") opens an independent in-memory database
- **Fix:** Changed test conftest to use a temp file path instead of :memory:, with cleanup before each test
- **Files modified:** backend/tests/conftest.py
- **Verification:** All 53 tests pass
- **Committed in:** ebfbca3 (Task 2 commit)

**2. [Rule 3 - Blocking] Added asgi-lifespan dependency for test client**
- **Found during:** Task 2 (API integration tests)
- **Issue:** httpx AsyncClient with ASGITransport does not trigger FastAPI lifespan events, causing device_service to remain None
- **Fix:** Added asgi-lifespan package and used LifespanManager to properly initialize app before tests
- **Files modified:** backend/pyproject.toml, backend/tests/conftest.py
- **Verification:** All lifespan-dependent endpoints work in tests
- **Committed in:** ebfbca3 (Task 2 commit)

**3. [Rule 3 - Blocking] Added httpx-ws dependency for WebSocket testing**
- **Found during:** Task 2 (API integration tests)
- **Issue:** Plan referenced httpx_ws for WS testing but package was not installed
- **Fix:** Added httpx-ws dev dependency; ultimately used Starlette TestClient for WS tests due to ASGI transport limitations
- **Files modified:** backend/pyproject.toml
- **Verification:** WebSocket connect test passes
- **Committed in:** ebfbca3 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3 blocking)
**Impact on plan:** All fixes were necessary to make tests run. No scope creep. Test patterns are clean and reusable.

## Issues Encountered
None beyond the auto-fixed deviations above.

## Known Stubs
None. All endpoints return real data from FakeAdapter and persist to SQLite.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- API layer complete, ready for dashboard frontend integration (Plan 03)
- WebSocket broadcasting ready for real-time dashboard updates
- Text command endpoint ready for Phase 2 LLM replacement

## Self-Check: PASSED

- All 8 created files exist on disk
- Both task commits (f9f55e3, ebfbca3) verified in git log
- SUMMARY.md created at expected path
- 53 tests passing (32 Plan 01 + 21 Plan 02)

---
*Phase: 01-foundation*
*Completed: 2026-04-11*
