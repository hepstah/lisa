# Lisa

## What This Is

Lisa is a voice-controlled home assistant running on a Raspberry Pi 5 (4GB). She uses a wake word ("Hey Lisa") to listen for commands, sends them to a cloud LLM API for conversational AI processing, and executes smart home actions. A web dashboard provides visual status and control.

## Core Value

Say "Hey Lisa, turn off the lights" and it works — natural voice control of smart home devices with conversational AI intelligence.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Wake word detection ("Hey Lisa") running locally on the Pi
- [ ] Audio capture and speech-to-text processing
- [ ] Cloud LLM integration for natural language understanding and response generation
- [ ] Text-to-speech for spoken responses
- [ ] Extensible device control framework (lights, plugs, sensors — protocol-agnostic)
- [ ] Web dashboard showing device status and recent interactions
- [ ] Device discovery and configuration through the dashboard
- [ ] Automation rules (e.g., "turn off lights at 11pm")

### Out of Scope

- Mobile app — web dashboard is accessible from phone browsers
- Local LLM inference — cloud API handles all AI processing
- Video/camera integration — v1 focuses on voice + device control
- Multi-user voice recognition — single-user for v1
- Custom hardware enclosure — Pi runs as-is

## Context

- **Platform:** Raspberry Pi 5 (4GB RAM), running headless
- **AI backend:** Cloud LLM API (OpenAI, Claude, or similar) for conversational intelligence
- **Voice pipeline:** Local wake word detection → cloud STT → cloud LLM → local TTS
- **Device protocols:** Needs to support common smart home protocols (Zigbee, Z-Wave, WiFi) — exact devices TBD, framework should be extensible
- **Dashboard:** Browser-based web UI, accessible on local network
- **Name:** "Lisa" — both the project name and the wake word

## Constraints

- **Hardware**: Raspberry Pi 5 with 4GB RAM — all local processing must fit within this
- **Network**: Requires internet for cloud LLM API calls; local network for device communication
- **Audio**: Needs USB microphone and speaker/audio output connected to the Pi
- **Latency**: Voice command → action should feel responsive (target < 3 seconds end-to-end)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Cloud LLM over local model | Pi 5 4GB can't run capable LLMs locally; cloud gives best conversational quality | -- Pending |
| Wake word over push-button | Hands-free is the core UX; wake word enables natural interaction | -- Pending |
| Web dashboard over native app | Browser UI works on any device on the network without installation | -- Pending |
| Extensible device framework | User hasn't decided on specific devices yet; framework should support adding protocols | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-11 after initialization*
