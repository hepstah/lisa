# Architecture Research: Lisa (Voice-Controlled Home Assistant)

**Researched:** 2026-04-11
**Domain:** Raspberry Pi voice assistant with cloud LLM + single device integration

## System Overview

Single-node, event-driven pipeline on Raspberry Pi 5 (4GB). Five layers:

1. **Voice Pipeline** (local, always-on) — wake word + audio capture
2. **Cloud Processing** (per-command) — STT + LLM intent parsing
3. **Device Control** (local) — single integration adapter for v1
4. **State/Persistence** (local) — SQLite for command history, device state, config
5. **Web Dashboard** (local network) — HTTP + WebSocket for real-time status

## Components

### Core Pipeline

| Component | Runs | Role | Talks To |
|-----------|------|------|----------|
| **Wake Word Detector** | Always-on | Listens for "Hey Lisa", triggers capture | Audio Capturer |
| **Audio Capturer / VAD** | On trigger | Records speech until silence (voice activity detection) | STT Service |
| **STT Service** | Per command | Sends audio to cloud STT, returns text | LLM Orchestrator |
| **LLM Orchestrator** | Per command | Sends text + device context to cloud LLM, returns structured intent (JSON) | Device Controller, TTS |
| **TTS Service** | Per command | Converts confirmation/error text to speech via Piper, plays on speaker | Speaker output |
| **Device Controller** | On intent | Routes parsed intent to the configured device integration | Device Adapter |

### Support

| Component | Runs | Role | Talks To |
|-----------|------|------|----------|
| **Device Adapter (v1: single)** | On command | Translates intent into device-specific API call (e.g., Hue REST) | External device |
| **State Store** | Always available | SQLite: command log, device state cache, configuration | All components |
| **API Server** | Always-on | FastAPI: REST endpoints + WebSocket for dashboard | Dashboard, State Store |
| **Web Dashboard** | Client-side | React: status display, command history, device config | API Server via HTTP/WS |

## Data Flow

```
[Microphone]
    │ PCM audio stream
    ▼
[Wake Word Detector] ──(no wake)──► [continue listening]
    │ (wake detected)
    ▼
[Audio Capturer + VAD]
    │ audio clip (until silence)
    ▼
[Cloud STT] ──(timeout/error)──► [TTS: "I couldn't understand that"] + [log failure]
    │ transcribed text
    ▼
[Cloud LLM] ──(bad intent)──► [TTS: "I don't know how to do that"] + [log failure]
    │ structured JSON: {intent, device, params}
    ▼
[Device Controller]
    │ validate against allowlist
    ▼
[Device Adapter] ──(device offline)──► [TTS: "That device isn't responding"] + [log failure]
    │ success
    ▼
[TTS: "Done, bedroom lamp is off"]
    │
    ▼
[State Store: log command + result]
    │
    ▼
[WebSocket push → Dashboard]
```

## Key Architecture Decisions

### Single-process vs multi-process

**Recommended: Single Python process with async (asyncio)**

- Simpler deployment and debugging
- Wake word runs in a dedicated thread (CPU-bound)
- Audio capture runs in a dedicated thread (I/O-bound)
- Everything else is async I/O (network calls, database)
- systemd manages the one process

Alternative: Separate processes per component communicating via IPC. More resilient but overkill for v1.

### LLM intent format

**Recommended: Structured JSON output via tool/function calling**

```json
{
  "intent": "device_control",
  "device": "bedroom_lamp",
  "action": "turn_off",
  "confirmation": "Turning off the bedroom lamp"
}
```

The LLM receives: system prompt with supported intents + device list, user's transcribed text. Returns structured JSON, not free-text to parse.

**Critical:** Intent must be validated against an allowlist before execution. LLM can hallucinate device names or actions that don't exist.

### State management

**Recommended: SQLite**

- Single file, no server process, built into Python
- Tables: commands (log), devices (config + state), settings
- Dashboard reads via API Server
- Voice pipeline writes directly

### Dashboard real-time updates

**Recommended: WebSocket from API Server**

- Dashboard connects via WebSocket on load
- API Server pushes: new command logged, device state changed, pipeline status
- Fallback: polling every 5s if WebSocket disconnects

## Suggested Build Order

Build order follows dependencies. Dashboard can be built and tested before audio hardware.

| Step | Component | Depends On | Why This Order |
|------|-----------|------------|----------------|
| 1 | State Store (SQLite schema) | Nothing | Foundation for everything |
| 2 | Device Adapter (v1 integration) | State Store | Can test device control independently |
| 3 | Device Controller + allowlist | Device Adapter, State Store | Intent → device action routing |
| 4 | API Server (FastAPI + WebSocket) | State Store | REST + WS endpoints for dashboard |
| 5 | Web Dashboard (React) | API Server | Visual status and config UI |
| 6 | Audio pipeline (mic + VAD) | Nothing | Can test recording independently |
| 7 | Wake word detector | Audio pipeline | Triggers capture |
| 8 | STT integration | Audio pipeline | Cloud transcription |
| 9 | LLM Orchestrator | STT, Device Controller | Ties intent parsing to device control |
| 10 | TTS integration (Piper) | LLM Orchestrator | Spoken responses |
| 11 | End-to-end integration | All above | Wire everything together |

### Phase Implications

- **Phase 1 (Foundation):** Steps 1-5 — state, device control, API, dashboard. No voice yet.
- **Phase 2 (Voice Pipeline):** Steps 6-10 — audio, wake word, STT, LLM, TTS.
- **Phase 3 (Integration):** Step 11 — wire pipeline to device control, failure handling, end-to-end testing.

This order means the dashboard is usable for manual device control before voice is wired in.

## Critical Patterns

- **Adapter pattern** for device integration — even with one adapter in v1, the interface should be clean so v2 can add more without refactoring the controller
- **Allowlist validation** — never let LLM output directly control devices without checking against known devices + supported actions
- **Audio thread isolation** — wake word and audio capture must not block network I/O or vice versa
- **Graceful degradation** — every pipeline stage has an explicit failure path with spoken feedback

## Confidence

**Medium** — well-established patterns for voice assistants. Build order is validated by dependency analysis. Specific library CPU benchmarks on Pi 5 should be verified during phase research.

---
*Researched: 2026-04-11*
