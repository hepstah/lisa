---
phase: 03-integration
verified: 2026-04-11T22:30:00Z
status: passed
score: 10/10 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 9/10
  gaps_closed:
    - "Default state on mount is offline; reverts to offline on WebSocket disconnect"
  gaps_remaining: []
  regressions: []
---

# Phase 3: Integration Verification Report

**Phase Goal:** Wire individual voice-pipeline components into a continuous VoiceLoop and surface pipeline status in the dashboard.
**Verified:** 2026-04-11T22:30:00Z
**Status:** passed
**Re-verification:** Yes -- after gap closure (commit 960368d)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | VoiceLoop continuously listens for wake word, captures speech, and calls VoicePipeline.process_audio() | VERIFIED | `backend/lisa/voice/voice_loop.py` lines 87-117: blocking loop reads frames, calls `_wake.detect()`, on detection resets capture, feeds frames, calls `pipeline.process_audio()` via `run_coroutine_threadsafe`. 7/7 tests pass. |
| 2 | TTS audio plays through the speaker on Pi via aplay; dev mode continues writing files only | VERIFIED | `backend/lisa/services/tts_service.py` lines 87-90: `asyncio.to_thread(subprocess.run, ["aplay", "-q", path], check=True, timeout=10)` when `not self._dev_mode`. Tests confirm aplay called in Pi mode, not called in dev mode. |
| 3 | Pipeline status events (listening, processing, responding, error) are broadcast at each stage transition | VERIFIED | `voice_loop.py` calls `_emit_status("listening")` at line 84, `"processing"` at line 97, `"responding"` at line 122, `"error"` at lines 120 and 132. `main.py` line 99 creates `pipeline_status_callback` that calls `manager.broadcast({"type": "pipeline_status", "status": status})`. |
| 4 | VoiceLoop only starts when dev_mode=False and voice_pipeline is available | VERIFIED | `main.py` line 90: `if voice_pipeline and not settings.dev_mode:`. Else branches at lines 113-116 log skip reasons. Backend starts clean in dev mode (verified via test suite). |
| 5 | Wake word detector is muted during TTS playback and unmuted after a cooldown | VERIFIED | `voice_loop.py` line 111: `self._wake.mute()` before pipeline call, line 125: `time.sleep(self.COOLDOWN)` (0.5s), line 127: `self._wake.unmute()`. Test `TestMuteUnmuteSequence` passes. |
| 6 | Dashboard shows current pipeline status (listening, processing, responding, error, offline) with a colored dot and label | VERIFIED | `PipelineStatus.tsx` has all 5 states in `stateConfig` with correct colors (emerald, amber+pulse, blue, red, zinc) and labels. Renders dot + label with sr-only accessibility span. |
| 7 | Pipeline status updates arrive via WebSocket pipeline_status events and replace the current state immediately | VERIFIED | `usePipelineStatus.ts` line 8: `if (event.type === "pipeline_status") { setStatus(event.status); }`. `App.tsx` dispatches to `handlePipelineWsEvent` in `handleWsMessage` callback. |
| 8 | Default state on mount is offline; reverts to offline on WebSocket disconnect | VERIFIED | Default on mount: `useState<PipelineState>("offline")` in usePipelineStatus.ts line 5. Disconnect reset: `usePipelineStatus` exposes `reset` callback (line 13: `useCallback(() => setStatus("offline"), [])`), returned at line 15. `App.tsx` line 35 destructures `reset: resetPipelineStatus`, lines 49-53: `useEffect(() => { if (wsStatus === "disconnected") { resetPipelineStatus(); } }, [wsStatus, resetPipelineStatus]);`. Fix committed in 960368d. |
| 9 | PipelineStatus indicator appears in the StatusBar header, left of the connection indicator | VERIFIED | `StatusBar.tsx` line 28: `<PipelineStatus status={pipelineStatus} />` rendered before the vertical divider (`h-4 w-px bg-border`) and WebSocket connection dot. |
| 10 | All backend tests pass including new VoiceLoop tests | VERIFIED | 100/100 tests pass (`uv run python -m pytest tests/ -x -v` exits 0 in 2.02s). Zero regressions. |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/lisa/voice/voice_loop.py` | VoiceLoop class with start/stop/emit_status, continuous audio loop | VERIFIED | 145 lines, class VoiceLoop with all expected methods, PYAUDIO_AVAILABLE flag, daemon thread pattern |
| `backend/lisa/services/tts_service.py` | Extended with aplay playback in Pi mode | VERIFIED | 94 lines, aplay subprocess call at lines 88-90, asyncio.to_thread wrapping |
| `backend/lisa/main.py` | VoiceLoop started in lifespan when not dev_mode | VERIFIED | 151 lines, voice loop block at lines 88-116, cleanup at lines 121-123, import asyncio present |
| `backend/tests/test_voice_loop.py` | Unit tests for VoiceLoop and TTS aplay | VERIFIED | 304 lines, 7 test classes/methods, all passing |
| `dashboard/src/api/types.ts` | PipelineState type and pipeline_status in WsEvent union | VERIFIED | PipelineState type at line 42, WsEvent union includes pipeline_status variant at line 49 |
| `dashboard/src/hooks/usePipelineStatus.ts` | Hook managing pipeline state from WebSocket events with reset callback | VERIFIED | 16 lines, useState("offline"), handleWsEvent callback filtering pipeline_status events, reset callback returning setStatus("offline") |
| `dashboard/src/components/PipelineStatus.tsx` | Pipeline status dot + label component | VERIFIED | 27 lines, all 5 state configs with colors, sr-only accessibility, motion-safe:animate-pulse on processing |
| `dashboard/src/components/StatusBar.tsx` | Extended with PipelineStatus indicator | VERIFIED | Props include pipelineStatus: PipelineState, renders PipelineStatus left of divider, divider uses h-4 w-px bg-border |
| `dashboard/src/App.tsx` | Wires usePipelineStatus hook and passes to StatusBar, resets on disconnect | VERIFIED | Imports usePipelineStatus, destructures status/handleWsEvent/reset, dispatches in handleWsMessage, useEffect resets on wsStatus "disconnected", passes pipelineStatus to StatusBar |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| voice_loop.py | voice_pipeline.py | `asyncio.run_coroutine_threadsafe(self._pipeline.process_audio(...))` | WIRED | Line 114-115: `run_coroutine_threadsafe` call with pipeline.process_audio |
| voice_loop.py | ws.py | `status_callback broadcasts pipeline_status events` | WIRED | `_emit_status` at line 63 calls `run_coroutine_threadsafe(self._status_cb(status))`, callback defined in main.py calls `manager.broadcast({"type": "pipeline_status"})` |
| main.py | voice_loop.py | `lifespan creates and starts VoiceLoop` | WIRED | Lines 92-108: imports VoiceLoop, creates instance, calls `voice_loop.start()` |
| tts_service.py | aplay subprocess | `asyncio.to_thread(subprocess.run, ["aplay", "-q", path])` | WIRED | Lines 87-90: conditional aplay call in Pi mode |
| usePipelineStatus.ts | types.ts | `import PipelineState and WsEvent types` | WIRED | Line 2: `import type { WsEvent, PipelineState } from "../api/types"` |
| App.tsx | usePipelineStatus.ts | `calls usePipelineStatus() and passes to handleWsMessage; resets on disconnect` | WIRED | Lines 12, 33-36, 43, 49-53: import, hook call with reset destructured, dispatch in handleWsMessage, useEffect reset on disconnect |
| StatusBar.tsx | PipelineStatus.tsx | `renders PipelineStatus component with pipelineStatus prop` | WIRED | Line 2: import, line 28: `<PipelineStatus status={pipelineStatus} />` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| PipelineStatus.tsx | `status` prop | App.tsx -> usePipelineStatus -> WebSocket pipeline_status events | Backend VoiceLoop emits real status strings at each stage transition | FLOWING (in Pi mode) / STATIC (in dev mode -- always "offline" because VoiceLoop never starts) |
| StatusBar.tsx | `pipelineStatus` prop | App.tsx prop pass-through from usePipelineStatus | Same as above | FLOWING (in Pi mode) |

Note: In dev mode, pipeline status is always "offline" which is the correct behavior -- the VoiceLoop does not start in dev mode. On WebSocket disconnect, pipeline status correctly resets to "offline" via the useEffect in App.tsx.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All backend tests pass | `uv run python -m pytest tests/ -x -v` | 100/100 passed in 2.02s | PASS |
| TypeScript compiles clean | `npx tsc --noEmit` | Exit 0, no errors | PASS |
| Dashboard builds | `npm run build` | "built in 202ms", exit 0 | PASS |
| Fix commit exists | `git show --stat 960368d` | 2 files changed (App.tsx, usePipelineStatus.ts) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DEVICE-01 | 03-01-PLAN.md | Control one concrete device integration end-to-end via voice command | SATISFIED | VoiceLoop drives wake word -> capture -> STT -> LLM -> device control -> TTS -> speaker. All components wired in lifespan. |
| DASH-05 | 03-02-PLAN.md | Show assistant pipeline status (listening, processing, responding, error, offline) | SATISFIED | PipelineState type, usePipelineStatus hook with reset, PipelineStatus component with 5 states, wired into StatusBar and App.tsx with disconnect handling. |

No orphaned requirements -- ROADMAP.md maps only DEVICE-01 and DASH-05 to Phase 3, and both are covered by the two plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | No anti-patterns detected in phase 3 files |

No TODOs, FIXMEs, placeholders, empty implementations, or console.log-only handlers found in any phase 3 artifact (including the two files modified in the fix commit).

### Human Verification Required

### 1. Visual Pipeline Status Indicator

**Test:** Start backend (`uv run uvicorn lisa.main:app --host 127.0.0.1 --port 8001`) and dashboard (`npm run dev`). Open http://localhost:5173.
**Expected:** Header shows "Lisa" on the left. On the right: gray dot with "Offline" label, thin vertical divider, green dot with "Connected" label. Labels hidden on small screens, dots remain.
**Why human:** Visual layout, spacing, color rendering, responsive behavior cannot be verified programmatically.

### 2. End-to-End Voice Command on Pi

**Test:** Deploy to Raspberry Pi 5 with Hue bridge configured. Say "Hey Lisa, turn on the bedroom lamp".
**Expected:** Lamp turns on within 3 seconds. Lisa speaks confirmation. Dashboard shows pipeline status cycling: listening -> processing -> responding -> listening.
**Why human:** Requires physical Pi hardware, microphone, speaker, and Hue bridge. Cannot be tested in dev environment.

### 3. WebSocket Disconnect Resets Pipeline Status

**Test:** With dashboard open and connected, stop the backend server.
**Expected:** WebSocket indicator shows "Disconnected" (red). Pipeline status shows "Offline" (gray). Previously this was a gap -- now the useEffect in App.tsx should reset pipeline status on disconnect.
**Why human:** Requires running both servers and observing the visual transition in real time.

### Gaps Summary

No gaps remaining. The single gap from the initial verification ("reverts to offline on WebSocket disconnect") has been fully closed by commit 960368d:

- `usePipelineStatus.ts` now exports a `reset` callback (`useCallback(() => setStatus("offline"), [])`)
- `App.tsx` destructures `reset: resetPipelineStatus` from the hook and calls it via `useEffect` when `wsStatus === "disconnected"`
- The fix is minimal, targeted, and introduces no new dependencies or side effects
- TypeScript compiles clean, dashboard builds, all 100 backend tests pass

---

_Verified: 2026-04-11T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
