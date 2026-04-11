---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to plan
stopped_at: Completed 02-04-PLAN.md
last_updated: "2026-04-11T19:52:21.032Z"
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 9
  completed_plans: 9
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** Say "Hey Lisa, turn off the bedroom lamp" and the lamp turns off quickly and predictably.
**Current focus:** Phase 02 — voice-pipeline

## Current Position

Phase: 3
Plan: Not started

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P01 | 5min | 2 tasks | 18 files |
| Phase 01 P03 | 6 | 2 tasks | 33 files |
| Phase 01 P04 | 4min | 2 tasks | 7 files |
| Phase 01 P02 | 6min | 2 tasks | 11 files |
| Phase 02 P02 | 4min | 2 tasks | 8 files |
| Phase 02 P01 | 6min | 2 tasks | 6 files |
| Phase 02 P04 | 3min | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Pre-roadmap: Cloud STT (Whisper API), cloud LLM (Claude or GPT-4o-mini), local TTS (Piper), wake word (openWakeWord) - all from research
- Pre-roadmap: Device integration choice (Hue Bridge recommended, user must confirm) - must be decided before Phase 1 planning begins
- Pre-roadmap: Dashboard-first build order - enables testing device control before voice complexity is introduced
- [Phase 01]: Used setuptools.build_meta backend (plan had incorrect _legacy path)
- [Phase 01]: DeviceState as frozen dataclass in interface.py, DeviceStateResponse as Pydantic model in models.py -- separate adapter vs API concerns
- [Phase 01]: TypeScript 6 paths without baseUrl (deprecated); simplified hook wiring with handleWsEvent callbacks
- [Phase 01]: Adapted App.tsx hook wiring to Plan 03 handleWsEvent callback pattern instead of wsHandler/listeners
- [Phase 01]: TextCommand re-throws errors so input retains text on failure; used Lightbulb icon for device cards
- [Phase 01]: Used LifespanManager from asgi-lifespan for test client to properly trigger FastAPI lifespan events
- [Phase 01]: Used temp file DB for tests instead of :memory: (in-memory SQLite creates independent DBs per connection)
- [Phase 01]: Module-level service injection pattern: lifespan sets device_service on router modules directly
- [Phase 02]: Graceful import pattern for Pi-only deps (piper-tts, openwakeword) with AVAILABLE flags
- [Phase 02]: hey_jarvis as wake word dev stand-in (custom hey_lisa deferred to v2 per ADV-03)
- [Phase 02]: Energy-based VAD in AudioCapture with injected audio source (no PyAudio import)
- [Phase 02]: Used tool_choice auto (not forced) for LLM intent parsing so unknown intents return None per D-20
- [Phase 02]: Validate API key presence at construction time (not first call) for STT and LLM services per pitfall 4
- [Phase 02]: STTNoSpeechError placed before STTError in except chain (subclass-first ordering)
- [Phase 02]: Pipeline error DB insert guarded by 'id' not in result to avoid double-insert with DeviceService._log_command

### Pending Todos

None yet.

### Blockers/Concerns

- [Pre-Phase 1]: Initial device integration not yet confirmed (Hue Bridge vs TP-Link Kasa vs Home Assistant). Must be decided before Phase 1 planning.
- [Pre-Phase 1]: LLM provider choice (Claude vs GPT-4o-mini) unresolved. Must be decided before Phase 2 planning.

## Session Continuity

Last session: 2026-04-11T19:46:34.883Z
Stopped at: Completed 02-04-PLAN.md
Resume file: None
