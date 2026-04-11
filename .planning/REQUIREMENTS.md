# Requirements: Lisa

**Defined:** 2026-04-11
**Core Value:** Say "Hey Lisa, turn off the bedroom lamp" and the lamp turns off quickly and predictably.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Voice Pipeline

- [ ] **VOICE-01**: Detect the wake phrase "Hey Lisa" locally on the Pi with acceptable false-trigger rate in a normal home environment
- [ ] **VOICE-02**: Capture a short utterance after wake word detection until silence (voice activity detection)
- [ ] **VOICE-03**: Send captured audio to a cloud STT provider and return transcribed text
- [ ] **VOICE-04**: Send transcribed text with device context to a cloud LLM and receive a structured JSON intent
- [ ] **VOICE-05**: Speak a short confirmation or error response locally via Piper TTS

### Device Control

- [ ] **DEVICE-01**: Control one concrete device integration end-to-end via voice command
- [x] **DEVICE-02**: Validate all LLM intent output against an allowlist of known devices and supported actions before execution
- [x] **DEVICE-03**: Query actual device state before executing commands (not cached state)
- [ ] **DEVICE-04**: Expose REST API endpoints for external tools to trigger device actions

### Dashboard

- [x] **DASH-01**: Display current device status (on/off, reachable/unreachable) with real-time updates via WebSocket
- [x] **DASH-02**: Show command history with success/failure states and timestamps
- [x] **DASH-03**: Provide device configuration flow for the initial integration without requiring SSH or shell access
- [x] **DASH-04**: Accept typed text commands as an alternative to voice input
- [ ] **DASH-05**: Show assistant pipeline status (listening, processing, responding, error, offline)

### Error Handling

- [ ] **ERR-01**: Produce spoken feedback for every failure mode: no speech captured, STT timeout, unknown intent, device offline, no internet
- [x] **ERR-02**: Log all failures in the dashboard with timestamp, failure stage, and error detail
- [ ] **ERR-03**: Set aggressive timeouts (5s) for cloud STT and LLM calls with immediate spoken fallback on timeout
- [x] **ERR-04**: Display clear connectivity status when cloud services are unreachable

### Infrastructure

- [x] **INFRA-01**: Run all local services on Raspberry Pi 5 (4GB) within memory budget (~850MB target)
- [ ] **INFRA-02**: Auto-start all services on Pi boot via systemd
- [x] **INFRA-03**: Use SQLite with WAL mode for crash-resilient state persistence
- [x] **INFRA-04**: Isolate audio capture in a dedicated thread to avoid blocking the async event loop

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Conversational

- **CONV-01**: Support conversational follow-ups with LLM context ("Make them dimmer" after "Turn on the lights")
- **CONV-02**: Provide "working on it" audio cue when total pipeline latency exceeds 2 seconds

### Multi-Device

- **MDEV-01**: Support multiple device protocols (Zigbee, Z-Wave, MQTT)
- **MDEV-02**: Device discovery across protocols
- **MDEV-03**: Scene/group control ("Goodnight" triggers multiple actions)

### Advanced

- **ADV-01**: User-defined automation rules (time-based and trigger-based)
- **ADV-02**: Wake word threshold calibration mode in dashboard
- **ADV-03**: Custom wake word training
- **ADV-04**: Multi-room support with multiple Pis

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Generic multi-protocol abstraction in v1 | Prove one integration before building abstractions |
| Local LLM inference | Pi 5 4GB can't run useful models; cloud API is the right call |
| Mobile app | Web dashboard is accessible from phone browsers |
| Multi-user voice recognition | Speaker identification is a research problem |
| Video or camera features | Different domain entirely |
| Custom hardware enclosure | Pi runs bare or in generic case |
| Internet-facing remote access | Security risk; local network only, use VPN if needed |
| Automation engine in v1 | Adds separate reliability and UX surface; defer |
| Plugin/skill marketplace | REST API provides extensibility without infrastructure |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VOICE-01 | Phase 2 | Pending |
| VOICE-02 | Phase 2 | Pending |
| VOICE-03 | Phase 2 | Pending |
| VOICE-04 | Phase 2 | Pending |
| VOICE-05 | Phase 2 | Pending |
| DEVICE-01 | Phase 3 | Pending |
| DEVICE-02 | Phase 1 | Complete |
| DEVICE-03 | Phase 1 | Complete |
| DEVICE-04 | Phase 1 | Pending |
| DASH-01 | Phase 1 | Complete |
| DASH-02 | Phase 1 | Complete |
| DASH-03 | Phase 1 | Complete |
| DASH-04 | Phase 1 | Complete |
| DASH-05 | Phase 3 | Pending |
| ERR-01 | Phase 2 | Pending |
| ERR-02 | Phase 1 | Complete |
| ERR-03 | Phase 2 | Pending |
| ERR-04 | Phase 1 | Complete |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0

---
*Requirements defined: 2026-04-11*
*Last updated: 2026-04-11 after roadmap creation*
