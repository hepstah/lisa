# Roadmap: Lisa

## Overview

Three phases that match the architecture's natural build order. Phase 1 delivers working device control and a dashboard - no voice, no problem, everything testable manually. Phase 2 adds the full voice pipeline, isolated so each audio stage can be validated independently. Phase 3 wires them together, verifies the end-to-end experience, and tunes latency until the core value - "say a command, the device responds" - is reliably true.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Infrastructure, device control, API, and dashboard working end-to-end without voice
- [ ] **Phase 2: Voice Pipeline** - Wake word, audio capture, STT, LLM intent parsing, and TTS speaking responses
- [ ] **Phase 3: Integration** - Voice wired to device control; full end-to-end pipeline verified and latency-tuned

## Phase Details

### Phase 1: Foundation
**Goal**: Users can control devices and inspect system state via dashboard without touching a terminal
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, DEVICE-02, DEVICE-03, DEVICE-04, DASH-01, DASH-02, DASH-03, DASH-04, ERR-02, ERR-04
**Success Criteria** (what must be TRUE):
  1. A device can be toggled on/off via the dashboard UI and the physical device responds
  2. The dashboard shows real-time device status (on/off, reachable/unreachable) without a page refresh
  3. A user can add and configure the initial device integration through the dashboard without SSH
  4. Command history shows each action with its success or failure state and a timestamp
  5. All services start automatically on Pi boot and remain running under systemd
**Plans:** 5 plans

Plans:
- [x] 01-01-PLAN.md -- Backend core: Python scaffold, config, SQLite, device adapters, device service with allowlist
- [x] 01-02-PLAN.md -- Backend API: FastAPI REST endpoints, WebSocket broadcasting, text command parsing
- [x] 01-03-PLAN.md -- Frontend scaffold: Vite + React + Tailwind v4 + shadcn, types, API client, data hooks
- [x] 01-04-PLAN.md -- Dashboard UI: StatusBar, DeviceCard, DeviceList, CommandHistory, TextCommand, DeviceConfig
- [x] 01-05-PLAN.md -- Integration: systemd service, SPA serving, full visual verification checkpoint
**UI hint**: yes

### Phase 2: Voice Pipeline
**Goal**: A spoken command after the wake word is captured, understood, and answered with spoken feedback
**Depends on**: Phase 1
**Requirements**: VOICE-01, VOICE-02, VOICE-03, VOICE-04, VOICE-05, ERR-01, ERR-03
**Success Criteria** (what must be TRUE):
  1. Saying "Hey Lisa" wakes the assistant reliably in a normal home environment without frequent false triggers
  2. A short spoken command is captured, sent to cloud STT, and returns an accurate transcription
  3. The transcribed text is sent to a cloud LLM and returns a structured JSON intent within the timeout window
  4. Lisa speaks a clear confirmation or error response locally within the latency budget
  5. Every failure mode (no speech detected, STT timeout, unknown intent) produces an audible spoken error
**Plans:** 4 plans

Plans:
- [x] 02-01-PLAN.md -- Cloud services: STT (OpenAI Whisper) and LLM intent parsing (Anthropic Claude Haiku 4.5)
- [x] 02-02-PLAN.md -- TTS (Piper), wake word detection (openWakeWord), audio capture with VAD
- [x] 02-03-PLAN.md -- Voice pipeline orchestrator, FastAPI lifespan wiring, text command LLM path
- [x] 02-04-PLAN.md -- Gap closure: fix no-speech error message, persist pipeline errors to command_log

### Phase 3: Integration
**Goal**: A voice command controls a real device end-to-end and the dashboard reflects the full pipeline state
**Depends on**: Phase 2
**Requirements**: DEVICE-01, DASH-05
**Success Criteria** (what must be TRUE):
  1. Saying "Hey Lisa, turn on the bedroom lamp" causes the lamp to respond within 3 seconds on a healthy network
  2. The dashboard shows live pipeline status (listening, processing, responding, error, offline) during a voice command
  3. All defined failure modes produce correct spoken feedback and appear in the dashboard command log
**Plans:** 2 plans

Plans:
- [ ] 03-01-PLAN.md -- Backend: VoiceLoop continuous audio loop, TTS speaker playback, lifespan wiring with status broadcast
- [ ] 03-02-PLAN.md -- Dashboard: pipeline status types, hook, PipelineStatus component in StatusBar, visual verification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 5/5 | Complete | - |
| 2. Voice Pipeline | 4/4 | Complete | - |
| 3. Integration | 0/2 | Planned | - |
