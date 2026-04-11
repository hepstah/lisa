# Phase 1: Foundation - Research

**Researched:** 2026-04-11
**Domain:** Infrastructure, TP-Link Kasa device control, FastAPI backend, React dashboard, SQLite persistence, systemd orchestration
**Confidence:** HIGH

## Summary

Phase 1 builds the complete non-voice foundation: a FastAPI backend controlling TP-Link Kasa devices via python-kasa, persisting state in SQLite (WAL mode), serving a React+Vite+Tailwind dashboard with real-time WebSocket updates, and running under systemd on the Pi. This is a greenfield project with no existing code.

The stack is well-established and the libraries are mature. python-kasa 0.10.2 provides a clean async interface for TP-Link device discovery and control. FastAPI 0.135.x handles both REST and WebSocket natively. The primary complexity is in the dev-mode path: the developer's Windows machine has no Python installed, and all development targeting a Pi must be testable locally with fake device adapters.

**Primary recommendation:** Build a thin device adapter interface with one real Kasa implementation and one fake/stub implementation. Use pydantic-settings with .env files for configuration (device credentials, dev-mode toggle). Serve the React SPA as static files from FastAPI in production, run Vite dev server separately during development.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** TP-Link Kasa is the v1 device integration (user has Kasa hardware available)
- **D-02:** Use python-kasa library for direct WiFi control -- no hub required
- **D-03:** Dev-mode paths preferred over Pi-specific behavior (per CLAUDE.md)
- **D-04:** Local development and testability without Raspberry Pi hardware is top priority
- **D-05:** Python 3.11+ backend with FastAPI (async, WebSocket support)
- **D-06:** React + Vite + Tailwind CSS for dashboard
- **D-07:** SQLite with WAL mode for state persistence
- **D-08:** systemd for process management on Pi

### Claude's Discretion
- Device adapter interface design (keep narrow -- one integration, not a framework)
- Dashboard layout and visual style
- REST API endpoint structure
- WebSocket event format for real-time updates
- Dev-mode fake device adapter for testing without hardware
- Auth approach for local-network API (likely none for v1)

### Deferred Ideas (OUT OF SCOPE)
- Device adapter specifics -- which Kasa device types, discovery vs manual config, dev-mode stub design (user noted for revisit but deferred)
- Dashboard design -- layout approach, theme, mobile-responsive or desktop-focused
- API surface -- endpoint design, WebSocket format, auth approach
- Dev experience -- testing without hardware, CI approach, hot reload setup
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Run all local services on Raspberry Pi 5 (4GB) within memory budget (~850MB target) | Memory budget analysis shows ~600MB total for Phase 1 components (FastAPI ~100MB, SQLite negligible, python-kasa negligible). Well within budget. |
| INFRA-02 | Auto-start all services on Pi boot via systemd | systemd service file pattern documented with Restart=on-failure, After=network-online.target. Single-process architecture means one service file. |
| INFRA-03 | Use SQLite with WAL mode for crash-resilient state persistence | aiosqlite 0.22.1 provides async SQLite access. WAL mode set via PRAGMA on connection open. |
| INFRA-04 | Isolate audio capture in a dedicated thread to avoid blocking the async event loop | Phase 1 has no audio -- but the architecture must not block the event loop. FastAPI/uvicorn async loop handles this naturally for HTTP/WS. Thread isolation pattern documented for Phase 2 preparation. |
| DEVICE-02 | Validate all LLM intent output against an allowlist of known devices and supported actions before execution | Phase 1 implements the allowlist and validation logic. Dashboard commands go through the same validation path that LLM output will use in Phase 2. |
| DEVICE-03 | Query actual device state before executing commands (not cached state) | python-kasa's `dev.update()` queries live device state. Always call before command execution. |
| DEVICE-04 | Expose REST API endpoints for external tools to trigger device actions | FastAPI REST endpoints documented with patterns. |
| DASH-01 | Display current device status (on/off, reachable/unreachable) with real-time updates via WebSocket | FastAPI WebSocket ConnectionManager pattern documented. Broadcast on state change. |
| DASH-02 | Show command history with success/failure states and timestamps | SQLite command_log table. API endpoint returns paginated history. |
| DASH-03 | Provide device configuration flow for the initial integration without requiring SSH | Dashboard form for Kasa device IP/credentials. Discover endpoint optional. |
| DASH-04 | Accept typed text commands as an alternative to voice input | Text input on dashboard sends to same command processing pipeline (minus STT). Prepares the path Phase 2 voice commands will use. |
| ERR-02 | Log all failures in the dashboard with timestamp, failure stage, and error detail | command_log table includes status, error_message, error_stage columns. |
| ERR-04 | Display clear connectivity status when cloud services are unreachable | Phase 1 has no cloud services, but the pattern (status indicator in dashboard header) should be established for Phase 2. Device reachability is the Phase 1 equivalent. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

These directives from CLAUDE.md constrain all implementation decisions:

- **Dev-mode first:** Local development and testability without Raspberry Pi hardware is priority #1
- **Narrow scope:** One working integration over an extensible framework
- **No premature abstraction:** Do not introduce abstractions before a second real use case exists
- **Simplest solution:** Prefer the simplest solution that satisfies the current requirement
- **Fake adapters:** Prefer fake or stub device adapters over broad protocol support
- **No opportunistic cleanup:** Do not expand scope, do not refactor unrelated code
- **Explicit contracts:** Prefer explicit contracts over speculative abstractions
- **Claim before edit:** Use Claim/Handoff format for work coordination
- **ASCII-only:** Use ASCII-only punctuation in markdown

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.x | Async HTTP + WebSocket backend | De facto Python async web framework. Native WebSocket, dependency injection, Pydantic integration. |
| uvicorn | 0.44.x | ASGI server | Standard production server for FastAPI. Handles HTTP/1.1 and WebSocket. |
| python-kasa | 0.10.2 | TP-Link Kasa device control | Only maintained Python library for TP-Link Kasa local WiFi control. Async-native. |
| aiosqlite | 0.22.1 | Async SQLite access | asyncio bridge to stdlib sqlite3. Enables non-blocking DB access on the event loop. |
| pydantic | 2.12.x | Data validation and serialization | Required by FastAPI. Models for API schemas, device state, command records. |
| pydantic-settings | 2.x | Configuration from .env files | Type-safe settings with environment variable override. Standard FastAPI pattern. |
| React | 19.x | Dashboard UI framework | Current stable. Component model suits device cards and status displays. |
| Vite | 8.x | Frontend build tool | Fast HMR for development, optimized builds for production. |
| Tailwind CSS | 4.x | Utility-first CSS | v4 uses @tailwindcss/vite plugin. No config file needed. |
| TypeScript | 6.x | Frontend type safety | Catches API contract mismatches at build time. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | latest | HTTP client (for tests) | Testing FastAPI endpoints. Also used by FastAPI TestClient. |
| pytest | 9.x | Test framework | All backend tests. |
| pytest-asyncio | 1.3.x | Async test support | Testing async device adapter and API endpoints. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aiosqlite | SQLAlchemy async + aiosqlite | ORM adds complexity not needed for 3 tables. Raw SQL with aiosqlite is simpler for this scale. |
| Raw WebSocket | Socket.IO (python-socketio) | Adds reconnect/rooms for free but another dependency. Raw WS + client reconnect logic is sufficient for single-server. |
| pydantic-settings | python-dotenv alone | Loses type validation. pydantic-settings is already a FastAPI dependency. |

**Backend installation:**
```bash
pip install fastapi uvicorn python-kasa aiosqlite pydantic-settings
pip install httpx pytest pytest-asyncio  # dev dependencies
```

**Frontend installation:**
```bash
npm create vite@latest dashboard -- --template react-ts
cd dashboard
npm install
npm install -D @tailwindcss/vite
```

## Architecture Patterns

### Recommended Project Structure

```
lisa/
  backend/
    lisa/
      __init__.py
      main.py              # FastAPI app, startup/shutdown, static mount
      config.py             # pydantic-settings: Settings class
      db.py                 # SQLite connection, schema init, WAL pragma
      models.py             # Pydantic models for API request/response
      api/
        __init__.py
        devices.py          # REST endpoints: list, control, status
        commands.py          # REST endpoints: command history, text command
        ws.py               # WebSocket endpoint + ConnectionManager
      device/
        __init__.py
        interface.py        # DeviceAdapter protocol (abstract)
        kasa_adapter.py     # Real Kasa implementation
        fake_adapter.py     # Fake/stub for dev-mode
      services/
        __init__.py
        device_service.py   # Business logic: validate, execute, log
        allowlist.py        # Action allowlist validation
    tests/
      __init__.py
      conftest.py           # Fixtures: test client, fake adapter, test db
      test_devices.py
      test_commands.py
      test_ws.py
      test_kasa_adapter.py
    pyproject.toml
    .env.example
  dashboard/
    src/
      App.tsx
      main.tsx
      components/
        DeviceCard.tsx       # Single device status + toggle
        DeviceList.tsx       # Grid of device cards
        CommandHistory.tsx   # Command log table
        TextCommand.tsx      # Text input for commands
        StatusBar.tsx        # Connection status indicator
        DeviceConfig.tsx     # Add/configure device form
      hooks/
        useWebSocket.ts      # WS connection with auto-reconnect
        useDevices.ts        # Device state from REST + WS updates
        useCommands.ts       # Command history
      api/
        client.ts            # fetch wrapper for REST endpoints
        types.ts             # TypeScript types matching backend models
      index.css              # @import "tailwindcss"
    vite.config.ts
    tsconfig.json
    package.json
  systemd/
    lisa-backend.service     # systemd unit file
  .env.example               # LISA_DEV_MODE, KASA_USERNAME, KASA_PASSWORD, etc.
```

### Pattern 1: Device Adapter Interface

**What:** A minimal Python Protocol class that both KasaAdapter and FakeAdapter implement.
**When to use:** Always -- this is the boundary between business logic and hardware.

```python
# backend/lisa/device/interface.py
from typing import Protocol

class DeviceState:
    """Immutable snapshot of device state."""
    device_id: str
    alias: str
    is_on: bool
    is_reachable: bool

class DeviceAdapter(Protocol):
    """Minimal interface for device control. NOT a framework -- just a contract."""

    async def discover(self) -> list[DeviceState]:
        """Find devices on the network."""
        ...

    async def get_state(self, device_id: str) -> DeviceState:
        """Query live device state. Never cached."""
        ...

    async def turn_on(self, device_id: str) -> DeviceState:
        """Turn device on. Returns new state."""
        ...

    async def turn_off(self, device_id: str) -> DeviceState:
        """Turn device off. Returns new state."""
        ...
```

**Key design choice:** The interface is intentionally small. No brightness, no color, no scenes. V1 is on/off only. Expand only when a second use case demands it.

### Pattern 2: WebSocket ConnectionManager

**What:** In-memory manager that tracks connected dashboard clients and broadcasts state changes.
**When to use:** Single-process FastAPI server (no multi-worker needed for Pi).

```python
# backend/lisa/api/ws.py
from fastapi import WebSocket
import json

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, event: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)
```

### Pattern 3: SQLite WAL Mode Setup

**What:** Configure SQLite for crash resilience on first connection.

```python
# backend/lisa/db.py
import aiosqlite

DB_PATH = "lisa.db"

async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA foreign_keys=ON")
    db.row_factory = aiosqlite.Row
    return db
```

### Pattern 4: pydantic-settings Configuration

**What:** Type-safe configuration with .env file support and environment variable override.

```python
# backend/lisa/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    dev_mode: bool = True
    db_path: str = "lisa.db"
    kasa_username: str = ""
    kasa_password: str = ""
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "LISA_", "env_file": ".env"}
```

### Pattern 5: Serving React SPA from FastAPI

**What:** In production, FastAPI serves the Vite build output as static files. In development, Vite dev server runs separately with proxy to backend.

```python
# backend/lisa/main.py (production static serving)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI()

# Mount API routes first, then catch-all for SPA
# ...register API routers...

dashboard_dir = Path(__file__).parent.parent.parent / "dashboard" / "dist"
if dashboard_dir.exists():
    app.mount("/", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")
```

```typescript
// dashboard/vite.config.ts (development proxy)
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
```

### Anti-Patterns to Avoid

- **Generic device framework:** Do not build a plugin system, device registry, or protocol abstraction layer. One adapter interface, two implementations (real + fake). Period.
- **ORM for 3 tables:** Raw SQL with aiosqlite is clearer and lighter than SQLAlchemy for this scale. Do not introduce an ORM.
- **Global mutable state for device cache:** Always query live state from device. The only state store is SQLite (for command log and config).
- **Polling for real-time updates:** Use WebSocket push from server to dashboard. Do not poll the REST API on a timer for status updates.
- **Auth system for v1:** No authentication for the local-network API. Adding auth adds complexity without value on a LAN-only Pi.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TP-Link device protocol | Custom TCP/HTTP to Kasa devices | python-kasa | KLAP encryption, device discovery, credential handling are all complex. The library handles protocol versions transparently. |
| Async SQLite access | Threading wrapper around sqlite3 | aiosqlite | Correctly bridges blocking sqlite3 to asyncio with proper thread safety. |
| Configuration from env vars | Manual os.environ parsing | pydantic-settings | Type validation, .env file support, nested settings, all for free. |
| WebSocket reconnect (client) | Custom retry logic from scratch | Simple hook with exponential backoff | But do write the hook -- there is no standard React library for raw WS reconnect that is small enough to justify a dependency. Keep it under 50 lines. |
| API request/response validation | Manual dict checking | Pydantic models + FastAPI | FastAPI auto-generates OpenAPI docs and validates all I/O through Pydantic. |

**Key insight:** The only genuinely custom code in Phase 1 is the device service layer (validate intent, execute command, log result, broadcast update) and the dashboard UI. Everything else has a standard library solution.

## Common Pitfalls

### Pitfall 1: python-kasa Authentication Requirements

**What goes wrong:** Newer TP-Link Kasa devices (post-2021 firmware) require TP-Link cloud credentials for local control. Code works with old devices but fails silently or throws AuthenticationError on newer ones.
**Why it happens:** TP-Link switched from static XOR encryption to KLAP protocol, which requires credential handshake even for local control.
**How to avoid:** Always pass username/password to Discover and Device constructors. Store credentials in .env file. Test with the actual hardware early.
**Warning signs:** `AuthenticationError` or `KasaException` on discover/connect. Device found but commands fail.

### Pitfall 2: WebSocket Connections Dropping Silently

**What goes wrong:** Dashboard WebSocket disconnects on network hiccup. No reconnect logic. Dashboard shows stale data with no indication.
**Why it happens:** Browser WebSocket API has no built-in reconnect.
**How to avoid:** Implement auto-reconnect with exponential backoff in the React useWebSocket hook. Show connection status indicator in dashboard header. Use heartbeat ping/pong to detect dead connections.
**Warning signs:** Dashboard data stops updating. No error shown to user.

### Pitfall 3: SQLite Write Contention

**What goes wrong:** Multiple concurrent writes (command log + device state update) cause SQLITE_BUSY errors.
**Why it happens:** SQLite uses a database-level write lock. WAL mode allows concurrent reads but still serializes writes.
**How to avoid:** Use a single aiosqlite connection (or connection pool with max 1 writer). Queue writes through a single async task. Set busy_timeout to avoid immediate failures: `PRAGMA busy_timeout=5000`.
**Warning signs:** Intermittent "database is locked" errors under load.

### Pitfall 4: python-kasa Device State Not Updated After Command

**What goes wrong:** Call `dev.turn_on()` then read `dev.is_on` -- still shows False.
**Why it happens:** python-kasa caches state. Methods that change state do not invalidate the cache.
**How to avoid:** Always call `await dev.update()` after any state-changing operation before reading state.
**Warning signs:** Dashboard shows wrong state after toggle. API returns stale values.

### Pitfall 5: SD Card Corruption on Power Loss

**What goes wrong:** Pi loses power, SQLite database corrupts, command history and device config lost.
**Why it happens:** Writes not flushed to disk before power cut.
**How to avoid:** WAL mode (already required by INFRA-03) + `PRAGMA synchronous=NORMAL` provides good crash resilience. For critical config, consider writing to a separate file with atomic rename.
**Warning signs:** Database errors after unexpected reboot. Missing recent entries.

### Pitfall 6: Vite Dev Server and FastAPI Port Conflict

**What goes wrong:** Both try to serve on the same port, or CORS blocks API requests from Vite dev server.
**Why it happens:** During development, frontend runs on Vite (port 5173) and backend on uvicorn (port 8000). Cross-origin requests get blocked.
**How to avoid:** Use Vite proxy configuration (documented in Architecture Patterns above). In production, serve SPA from FastAPI directly -- no CORS needed.
**Warning signs:** Network errors in browser console. CORS policy violations.

### Pitfall 7: No Python on Dev Machine

**What goes wrong:** Developer's Windows machine does not have Python installed. Cannot run backend locally.
**Why it happens:** Windows Store Python stub is present but not a real installation.
**How to avoid:** Install Python 3.11+ (recommend 3.12 or 3.13) via python.org installer or use `uv` which bundles its own Python. Document setup in README.
**Warning signs:** `python --version` fails or returns Windows Store redirect.

## Code Examples

### Kasa Adapter Implementation

```python
# backend/lisa/device/kasa_adapter.py
from kasa import Discover, Credentials
from lisa.device.interface import DeviceAdapter, DeviceState
from lisa.config import Settings

class KasaAdapter:
    def __init__(self, settings: Settings):
        self._credentials = Credentials(
            settings.kasa_username,
            settings.kasa_password
        ) if settings.kasa_username else None
        self._devices: dict[str, object] = {}  # ip -> kasa Device

    async def discover(self) -> list[DeviceState]:
        found = await Discover.discover(credentials=self._credentials)
        states = []
        for ip, dev in found.items():
            await dev.update()
            self._devices[ip] = dev
            states.append(DeviceState(
                device_id=ip,
                alias=dev.alias,
                is_on=dev.is_on,
                is_reachable=True,
            ))
        return states

    async def get_state(self, device_id: str) -> DeviceState:
        dev = self._devices.get(device_id)
        if not dev:
            dev = await Discover.discover_single(
                device_id, credentials=self._credentials
            )
            self._devices[device_id] = dev
        try:
            await dev.update()
            return DeviceState(
                device_id=device_id,
                alias=dev.alias,
                is_on=dev.is_on,
                is_reachable=True,
            )
        except Exception:
            return DeviceState(
                device_id=device_id,
                alias=dev.alias if hasattr(dev, 'alias') else device_id,
                is_on=False,
                is_reachable=False,
            )

    async def turn_on(self, device_id: str) -> DeviceState:
        dev = self._devices[device_id]
        await dev.turn_on()
        await dev.update()
        return DeviceState(
            device_id=device_id,
            alias=dev.alias,
            is_on=dev.is_on,
            is_reachable=True,
        )

    async def turn_off(self, device_id: str) -> DeviceState:
        dev = self._devices[device_id]
        await dev.turn_off()
        await dev.update()
        return DeviceState(
            device_id=device_id,
            alias=dev.alias,
            is_on=dev.is_on,
            is_reachable=True,
        )
```

### Fake Adapter for Dev Mode

```python
# backend/lisa/device/fake_adapter.py
from lisa.device.interface import DeviceAdapter, DeviceState

class FakeAdapter:
    """In-memory fake for development without hardware."""

    def __init__(self):
        self._devices: dict[str, DeviceState] = {
            "fake-lamp-1": DeviceState(
                device_id="fake-lamp-1",
                alias="Bedroom Lamp",
                is_on=False,
                is_reachable=True,
            ),
            "fake-plug-1": DeviceState(
                device_id="fake-plug-1",
                alias="Desk Fan",
                is_on=True,
                is_reachable=True,
            ),
            "fake-offline-1": DeviceState(
                device_id="fake-offline-1",
                alias="Garage Light",
                is_on=False,
                is_reachable=False,
            ),
        }

    async def discover(self) -> list[DeviceState]:
        return list(self._devices.values())

    async def get_state(self, device_id: str) -> DeviceState:
        return self._devices[device_id]

    async def turn_on(self, device_id: str) -> DeviceState:
        dev = self._devices[device_id]
        if not dev.is_reachable:
            raise ConnectionError(f"Device {device_id} is not reachable")
        self._devices[device_id] = DeviceState(
            device_id=dev.device_id,
            alias=dev.alias,
            is_on=True,
            is_reachable=True,
        )
        return self._devices[device_id]

    async def turn_off(self, device_id: str) -> DeviceState:
        dev = self._devices[device_id]
        if not dev.is_reachable:
            raise ConnectionError(f"Device {device_id} is not reachable")
        self._devices[device_id] = DeviceState(
            device_id=dev.device_id,
            alias=dev.alias,
            is_on=False,
            is_reachable=True,
        )
        return self._devices[device_id]
```

### SQLite Schema

```sql
-- Command log
CREATE TABLE IF NOT EXISTS command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    source TEXT NOT NULL,         -- 'dashboard', 'voice', 'api'
    raw_input TEXT,               -- typed text or transcribed speech
    device_id TEXT,
    action TEXT,                  -- 'turn_on', 'turn_off'
    status TEXT NOT NULL,         -- 'success', 'error', 'rejected'
    error_message TEXT,
    error_stage TEXT,             -- 'validation', 'execution', 'device_unreachable'
    duration_ms INTEGER
);

-- Device configuration
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    alias TEXT NOT NULL,
    device_type TEXT,             -- 'plug', 'bulb', 'switch'
    host TEXT,                    -- IP address
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen TEXT
);

-- Application settings
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### WebSocket Event Format

```typescript
// Dashboard receives these events over WebSocket
type WsEvent =
  | { type: "device_state"; device_id: string; is_on: boolean; is_reachable: boolean }
  | { type: "command_logged"; command: CommandRecord }
  | { type: "connection_status"; status: "connected" | "device_unreachable" }

// Dashboard sends these (for text commands)
type WsCommand = { type: "text_command"; text: string }
```

### systemd Service File

```ini
# systemd/lisa-backend.service
[Unit]
Description=Lisa Smart Home Backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/lisa/backend
ExecStart=/home/pi/lisa/backend/.venv/bin/uvicorn lisa.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
Environment=LISA_DEV_MODE=false

[Install]
WantedBy=multi-user.target
```

### React useWebSocket Hook

```typescript
// dashboard/src/hooks/useWebSocket.ts
import { useEffect, useRef, useCallback, useState } from 'react'

type WsStatus = 'connecting' | 'connected' | 'disconnected'

export function useWebSocket(url: string, onMessage: (data: unknown) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const [status, setStatus] = useState<WsStatus>('disconnected')
  const retryRef = useRef(0)

  const connect = useCallback(() => {
    setStatus('connecting')
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('connected')
      retryRef.current = 0
    }
    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)) } catch {}
    }
    ws.onclose = () => {
      setStatus('disconnected')
      const delay = Math.min(1000 * 2 ** retryRef.current, 30000)
      retryRef.current++
      setTimeout(connect, delay)
    }
  }, [url, onMessage])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  return { status }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tailwind CSS v3 with tailwind.config.js | Tailwind v4 with @tailwindcss/vite plugin, no config file | Jan 2025 | Simpler setup. `@import "tailwindcss"` in CSS file, plugin in vite.config.ts. Auto content detection. |
| python-kasa < 0.7 with SmartPlug/SmartBulb classes | python-kasa 0.10.x with generic Device + Features/Modules | 2024-2025 | Unified interface. Use `dev.turn_on()`/`dev.turn_off()` and `dev.modules[Module.Light]` instead of type-specific classes. |
| Pydantic v1 with class Config | Pydantic v2 with model_config dict | 2023 | FastAPI 0.135.x uses Pydantic v2. All models use `model_config` not inner `Config` class. |
| Pi OS Bookworm with Python 3.11 | Pi OS Trixie with Python 3.13 | Late 2025 | Newer Pi installs have Python 3.13. Code should target 3.11+ for compatibility with both. |
| aiosqlite with manual thread pool | aiosqlite 0.22.x with improved async bridge | Dec 2025 | Latest version. No API changes, just stability. |

**Deprecated/outdated:**
- python-kasa SmartPlug, SmartBulb, SmartStrip classes: replaced by generic Device with Features/Modules API
- Tailwind CSS v3 PostCSS setup: replaced by v4 Vite plugin approach
- Pydantic v1 validators: replaced by v2 field_validator/model_validator decorators

## Open Questions

1. **Which Kasa device types does the user have?**
   - What we know: User confirmed they have Kasa hardware
   - What's unclear: Plugs? Bulbs? Switches? Light strips? This affects which features to expose in the dashboard
   - Recommendation: Start with on/off only (works for all types). The adapter interface is the same regardless.

2. **Do the user's Kasa devices require TP-Link cloud credentials?**
   - What we know: Devices with firmware updated after 2021 require credentials even for local control
   - What's unclear: Whether the user's specific devices need this
   - Recommendation: Build credential input into the configuration flow. Try without first, fall back to credential prompt.

3. **Dashboard: desktop-focused or responsive?**
   - What we know: Dashboard is local-network only, likely accessed from a phone or laptop on the same network
   - What's unclear: User's primary access device
   - Recommendation: Build responsive with Tailwind. Mobile-first is easy with utility classes and costs nothing extra.

4. **Vite dev server vs Python dev server on Windows**
   - What we know: Dev machine is Windows 11. Python is not installed. Node 24 is available.
   - What's unclear: Whether user will install Python on Windows or develop via WSL/SSH to Pi
   - Recommendation: Document both paths. Recommend installing Python via python.org installer on Windows for simplest dev loop.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Backend (FastAPI, python-kasa) | NOT INSTALLED | -- | Install via python.org or uv |
| Node.js | Dashboard (React, Vite) | Yes | 24.13.1 | -- |
| npm | Dashboard package management | Yes | 11.8.0 | -- |
| pip / uv | Python package management | NOT INSTALLED | -- | Installed with Python, or install uv separately |
| Raspberry Pi | Production deployment | Not on dev machine | -- | Dev-mode with fake adapter on Windows |
| TP-Link Kasa devices | Device control | User confirmed available | -- | Fake adapter for dev |

**Missing dependencies with no fallback:**
- Python 3.11+ must be installed on the dev machine before backend development begins. This is a Wave 0 setup task.

**Missing dependencies with fallback:**
- Raspberry Pi is not the dev machine. Fake adapter + dev-mode flag provides full local development.
- Kasa devices not needed for development. Fake adapter simulates all behaviors including unreachable state.

## Sources

### Primary (HIGH confidence)
- [python-kasa PyPI](https://pypi.org/project/python-kasa/) - Version 0.10.2, Python >=3.11 requirement confirmed
- [python-kasa GitHub](https://github.com/python-kasa/python-kasa) - README: auth requirements, KLAP protocol, basic usage, discovery
- [python-kasa tutorial.py](https://github.com/python-kasa/python-kasa/blob/master/docs/tutorial.py) - Official code examples for discovery, modules, features
- [FastAPI PyPI](https://pypi.org/project/fastapi/) - Version 0.135.3, Python >=3.10
- [FastAPI WebSocket docs](https://fastapi.tiangolo.com/advanced/websockets/) - ConnectionManager pattern, broadcast
- [FastAPI Settings docs](https://fastapi.tiangolo.com/advanced/settings/) - pydantic-settings integration
- [Tailwind CSS docs](https://tailwindcss.com/docs) - v4 Vite plugin installation
- [aiosqlite PyPI](https://pypi.org/project/aiosqlite/) - Version 0.22.1, Dec 2025
- npm registry: React 19.2.5, Vite 8.0.8, Tailwind 4.2.2, TypeScript 6.0.2

### Secondary (MEDIUM confidence)
- [Raspberry Pi OS Trixie announcement](https://www.raspberrypi.com/news/trixie-the-new-version-of-raspberry-pi-os/) - Python 3.13 on Trixie
- [python-kasa KLAP auth GitHub issues](https://github.com/python-kasa/python-kasa/issues/1604) - Authentication failure patterns
- Various 2025-2026 FastAPI + WebSocket tutorial articles - ConnectionManager pattern verification

### Tertiary (LOW confidence)
- python-kasa fake/mock testing capabilities - No official documentation found. Custom fake adapter is the right approach.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified on PyPI/npm with current versions. Well-documented, actively maintained.
- Architecture: HIGH - Single-process async FastAPI is a proven pattern. python-kasa async API fits naturally.
- Pitfalls: HIGH - Auth requirement verified against official docs. WAL mode, WebSocket drops, state caching are well-documented gotchas.
- Dev-mode approach: MEDIUM - No built-in fake/mock support in python-kasa. Custom FakeAdapter pattern is straightforward but untested.

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (30 days -- stable ecosystem, no major releases expected)
