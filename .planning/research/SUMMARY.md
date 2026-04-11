# Project Research Summary

**Project:** Lisa (Voice-Controlled Home Assistant)
**Domain:** Raspberry Pi voice assistant with cloud LLM + smart home control
**Researched:** 2026-04-11
**Confidence:** MEDIUM

## Executive Summary

Lisa is a voice-controlled home assistant running on Raspberry Pi 5 (4GB) that combines local wake word detection with cloud LLM intelligence to control smart home devices via natural conversation. The recommended approach is a Python-first, single-process async architecture: openWakeWord for wake word detection, Whisper API for speech-to-text, Claude or GPT-4o-mini for intent parsing via structured JSON output, Piper TTS for local spoken responses, and a FastAPI + React dashboard for status and configuration. This hybrid local/cloud design balances privacy (audio stays local except during commands), cost (cloud only when needed), and quality (cloud STT/LLM outperform anything that fits on 4GB RAM).

The critical product constraint is that v1 supports exactly one device integration end-to-end. Attempting to build a multi-protocol abstraction layer in v1 is the most common failure mode in open-source voice assistant projects — they over-engineer device support and never finish the conversational layer that makes Lisa actually useful. The right order is: prove the full pipeline with one real device, then generalize. Philips Hue Bridge API is the recommended first integration (REST, well-documented, lowest friction), though this is a user choice to confirm.

The top risks are latency (cloud pipeline must stay under 3 seconds), audio thread management (blocking PyAudio calls on the event loop kill the dashboard), and microphone echo (TTS must mute the wake word detector while speaking). All three are architectural — they must be designed correctly from the start, not patched later. LLM hallucination of device names is a real reliability risk that an allowlist validation step eliminates entirely.

## Key Findings

### Recommended Stack

The stack is Python 3.11+ throughout the voice pipeline, device control, and API backend, with TypeScript + React for the dashboard. This single-language backend removes friction between components that need to share data. The audio stack uses PyAudio over ALSA — the standard approach for USB microphones on Pi. Piper TTS runs locally to avoid adding another cloud round-trip to the response path.

**Core technologies:**

- **openWakeWord:** Wake word detection — open-source, runs on Pi, customizable, actively maintained
- **OpenAI Whisper API:** Speech-to-text — best price/quality ratio at ~$0.006/min; local Whisper is too slow/inaccurate on Pi 5 4GB
- **Anthropic Claude API (or GPT-4o-mini):** LLM intent parsing — strong structured JSON output via tool/function calling; both are valid choices
- **Piper TTS:** Text-to-speech — local, natural-sounding, no latency penalty from cloud round-trip
- **FastAPI:** API backend — async, lightweight, built-in WebSocket support, same language as voice pipeline
- **React + Vite + Tailwind:** Dashboard — fast builds, component model suits device status cards
- **SQLite:** State store — single file, no server process, crash-resilient via WAL mode
- **systemd:** Process orchestration — native to Pi OS, lighter than Docker (~200-400MB RAM saved)
- **PyAudio / sounddevice over ALSA:** Audio I/O — standard on Pi, direct USB mic access

Memory budget is comfortable: approximately 850MB used (OS + wake word + audio + TTS + FastAPI), leaving ~3.1GB headroom on 4GB Pi.

See `.planning/research/STACK.md` for full comparison tables and "what not to use."

### Expected Features

V1 delivers a working voice-controlled device assistant, not a general platform. The LLM-backed conversational interface is the differentiating feature — most DIY voice assistants use rigid intent matching. Natural language with contextual follow-ups is what makes Lisa worth building.

**Must have (table stakes):**
- Wake word detection ("Hey Lisa") with acceptable false-trigger rate in ambient noise
- Speech capture + cloud STT with natural accuracy
- LLM intent parsing that handles natural phrasing, not keyword matching
- Local TTS spoken responses — natural-sounding, not robotic
- Device on/off control for one chosen integration (e.g., Hue lights)
- Explicit spoken feedback for every failure mode (no speech, timeout, device offline, no internet)
- Web dashboard: device status, command history, device configuration
- Dashboard configuration without requiring SSH or shell access

**Should have (differentiators):**
- Conversational follow-ups with LLM context ("Make them dimmer")
- Command history and audit log (debugging + trust)
- Text/typed fallback in dashboard
- REST API endpoints for external extensibility
- Local-first privacy architecture (audio not stored, only commands hit cloud)

**Defer to v2+:**
- Automation rules and schedules
- Multi-room / multi-Pi support
- Voice identification / multi-user
- Scene/group control ("Goodnight" mode)
- Custom wake word training pipeline
- Proactive suggestions based on usage patterns
- Internet-facing remote access (security risk, VPN is the right answer)
- Multi-protocol abstraction layer (Zigbee, Z-Wave, MQTT)

See `.planning/research/FEATURES.md` for full feature dependency graph and anti-features.

### Architecture Approach

Single-node, event-driven pipeline on Pi 5. The voice pipeline runs as a single Python async process: wake word and audio capture run in dedicated threads (CPU/I/O bound), everything else uses asyncio for network calls and database operations. SQLite stores command history, device state cache, and configuration. FastAPI serves the dashboard and pushes real-time updates via WebSocket.

**Major components:**

1. **Wake Word Detector** — always-on listener, triggers audio capture when "Hey Lisa" detected
2. **Audio Capturer + VAD** — captures speech until silence, passes audio clip to STT
3. **STT Service** — sends clip to cloud STT, returns transcribed text
4. **LLM Orchestrator** — sends text + device context to cloud LLM, receives structured JSON intent
5. **Device Controller + Allowlist** — validates LLM output against known devices/actions, rejects hallucinations
6. **Device Adapter (v1: single)** — translates validated intent to device-specific API call (e.g., Hue REST)
7. **TTS Service** — converts confirmation/error text to speech via Piper, plays on speaker
8. **State Store (SQLite)** — command log, device state cache, configuration
9. **API Server (FastAPI)** — REST + WebSocket endpoints consumed by dashboard
10. **Web Dashboard (React)** — status, command history, device config UI

Key patterns: adapter pattern for device integration (clean interface enables v2 additions), allowlist validation before any device command, audio thread isolation, graceful degradation with spoken feedback at every failure point.

See `.planning/research/ARCHITECTURE.md` for the full data flow diagram and build order table.

### Critical Pitfalls

Five critical pitfalls that can cause rewrites if not designed for from the start:

1. **Wake word model wrong for target environment** — test in the actual room with actual ambient noise early; tune threshold against real conditions, not dev-machine quiet
2. **Audio capture blocking the event loop** — run PyAudio in a dedicated thread with a queue from day one; retrofitting thread isolation after everything is wired together is painful
3. **Microphone echo/feedback loop** — mute wake word detector while TTS is playing; add cooldown after TTS completes; without this Lisa will respond to her own voice
4. **Cloud LLM latency blows the 3-second budget** — serial pipeline stages (STT ~1s + LLM ~1.5s + TTS ~0.5s + device ~0.3s) already push the limit; measure each stage independently; use fast model variants (Claude Haiku, GPT-4o-mini); consider an "I'm working on it" cue if total exceeds 2s
5. **LLM hallucinating device commands** — always validate LLM output against an allowlist of known device names and supported actions before execution; never pass LLM output directly to device APIs

Additional moderate pitfalls: ARM64 dependency failures (test every new library on Pi early), WebSocket reconnect logic needed on dashboard client, SD card corruption mitigated by SQLite WAL mode, LLM context bloat (keep system prompt under 500 tokens), and silent failure when cloud APIs are down (set 5s timeouts, always speak an error).

See `.planning/research/PITFALLS.md` for full pitfall list organized by phase.

## Implications for Roadmap

Research strongly supports a 3-phase structure that matches the architecture's build order. The dashboard and device control layer should exist before voice is wired in — this enables testing device control independently and avoids the situation where everything is built simultaneously and the first test of "does it work end to end" happens at the very end.

### Phase 1: Foundation — State, Device Control, API, Dashboard

**Rationale:** Every other component depends on the state store, device adapter, and API server. Building these first enables independent testing of device control before voice is introduced. The dashboard becomes a manual device control interface, proving the device integration works before voice adds complexity.

**Delivers:** Working device control via dashboard UI; SQLite schema with WAL mode; FastAPI with REST + WebSocket; React dashboard showing device status, configuration, and command history; a single device integration (Hue or chosen alternative) working end-to-end from HTTP request to device action; device allowlist and intent routing logic.

**Addresses features:** Device on/off control, device status visibility, configuration without shell, command history, REST API, text/typed fallback in dashboard.

**Avoids pitfalls:** ARM64 dependency failures (catch early), SD card corruption (WAL mode from day one), WebSocket drops (reconnect logic in dashboard), device state sync strategy (decide at adapter-build time).

**Research flag:** NEEDS RESEARCH — specific Hue Bridge API details, authentication flow, available actions, and state polling mechanism should be verified. Also confirm PyPI ARM64 wheel availability for key dependencies.

### Phase 2: Voice Pipeline — Audio, Wake Word, STT, LLM, TTS

**Rationale:** Voice is isolated here so it can be developed and tested without touching the device control layer. Each stage (mic, VAD, STT, LLM, TTS) can be validated independently before wiring to the pipeline. Audio threading architecture must be established here.

**Delivers:** Working voice capture pipeline; openWakeWord detecting "Hey Lisa" in target room with tuned threshold; cloud STT returning accurate transcriptions; LLM Orchestrator producing structured JSON intents with allowlist validation; Piper TTS speaking responses locally; all error paths producing spoken feedback.

**Addresses features:** Wake word detection, speech-to-text, natural language understanding (LLM), text-to-speech response, local-first privacy.

**Avoids pitfalls:** Audio blocking event loop (thread isolation from start), echo/feedback loop (TTS muting logic), wake word environment mismatch (test in target room early), LLM hallucination (allowlist validation), context bloat (system prompt under 500 tokens), cloud timeout/offline feedback (5s timeouts, spoken errors).

**Research flag:** STANDARD PATTERNS — openWakeWord, Whisper API, Piper TTS, and FastAPI are all well-documented. Phase-level research likely not needed. Individual library setup should reference current docs.

### Phase 3: Integration — Wire Pipeline to Device Control, End-to-End Testing

**Rationale:** Both major components exist independently. This phase wires them together and validates the complete user experience. Latency measurement and tuning happens here because individual stage timing is already known from Phase 2.

**Delivers:** Full end-to-end voice command to device response; spoken pipeline status in dashboard; end-to-end latency measured and within 3-second target; all failure modes tested (no speech, bad intent, device offline, no internet); demo-ready product.

**Addresses features:** All table stakes complete; conversational follow-ups (LLM context); explicit failure handling across all pipeline stages.

**Avoids pitfalls:** Latency budget (measure full pipeline, apply optimizations: streaming STT, fast model, early TTS start), wake word threshold tuning in real environment, confirming echo suppression holds in integration.

**Research flag:** NO RESEARCH NEEDED — integration of already-built components. Any issues at this phase are implementation/tuning, not new technical territory.

### Phase Ordering Rationale

- Dashboard-first ordering (from ARCHITECTURE.md build order) means device control can be manually tested before voice is involved — reduces variables when debugging
- Adapter pattern established in Phase 1 means Phase 2 never needs to know about device specifics; the LLM Orchestrator just produces a JSON intent and hands off
- Latency optimization deferred to Phase 3 because individual stage timings can't be meaningfully measured until all stages exist; individual stages each have acceptable latency headroom
- No automation rules in any phase — explicitly deferred to v2+ per FEATURES.md anti-features

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Philips Hue Bridge REST API — authentication (OAuth vs local token), available device actions, state polling vs push events, rate limits. Also verify ARM64 PyPI wheel availability for openWakeWord, PyAudio, and Piper dependencies before finalizing dependency list.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Voice pipeline components (openWakeWord, Whisper API, Piper, asyncio threading) are well-documented with established integration patterns
- **Phase 3:** Integration and latency tuning — no new technology, implementation work only

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core choices (openWakeWord, Whisper API, Piper, FastAPI, SQLite) are well-established. Only LLM selection is MEDIUM (both Claude and GPT-4o-mini are valid; preference-driven). |
| Features | HIGH | MVP scope is clear and well-validated against the DIY voice assistant ecosystem. Table stakes vs v2+ boundary is crisp. |
| Architecture | MEDIUM | Single-process async with threaded audio is the right pattern. Specific CPU/memory benchmarks for openWakeWord and Piper on Pi 5 should be verified during Phase 1 setup. |
| Pitfalls | HIGH | Pitfalls are experience-derived from known voice assistant failure modes. Echo loop, thread blocking, and LLM hallucination are widely documented. Latency budget math is verifiable. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Hue Bridge API specifics:** Local token vs OAuth, whether the API supports push events or requires polling, confirmed list of supported actions — validate during Phase 1 planning
- **Pi 5 benchmarks for openWakeWord:** CPU load at idle listening, detection latency — should be tested in Phase 1 spike before committing to single-process architecture
- **Piper voice quality subjective evaluation:** Research rates it as "good but not Alexa quality" — user should evaluate available Piper voices before finalizing
- **Exact LLM selection:** Claude vs GPT-4o-mini is unresolved. Recommendation: pick Claude given the LLM is Anthropic-provided here, but either works. Decide before Phase 2.
- **Chosen device integration:** Hue Bridge is recommended but user must confirm. If no Hue bridge exists, TP-Link Kasa (python-kasa) or Home Assistant REST API are fallback options. This must be decided before Phase 1 begins.

## Sources

### Primary (HIGH confidence)

- openWakeWord GitHub (Apache 2.0) — wake word detection capabilities, Pi deployment
- OpenAI Whisper API documentation — pricing (~$0.006/min), accuracy, streaming support
- Piper TTS GitHub — voice quality, Pi performance, available voices
- FastAPI documentation — async support, WebSocket patterns
- SQLite WAL mode documentation — crash resilience, write patterns
- Anthropic Claude API / OpenAI function calling documentation — structured JSON output, tool use

### Secondary (MEDIUM confidence)

- Raspberry Pi community / forums — Pi 5 memory budget, ARM64 dependency compatibility patterns
- Home Assistant Voice project and Rhasspy — validated feature scope decisions (what's table stakes vs v2)
- Philips Hue Developer documentation — REST API overview, bridge authentication (specifics need Phase 1 verification)

### Tertiary (LOW confidence — needs validation)

- End-to-end latency budget: calculated from individual component estimates, not measured on Pi 5 hardware
- openWakeWord CPU load estimate: from community reports, not direct Pi 5 measurement
- Piper quality assessment: subjective, voice-dependent; validate during project setup

---
*Research completed: 2026-04-11*
*Ready for roadmap: yes*
