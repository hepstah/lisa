# CLAUDE.md

This repository may be edited by multiple AI agents in parallel. Read this file before making changes.

## Primary Goal

Help move the project forward without creating overlap, surprise refactors, or conflicting architecture.

Your secondary role is adversarial review: pick apart weak assumptions, unnecessary complexity, and fragile design choices before they spread.

## Read First

Review [.planning/AGENT_COORDINATION.md](E:\dev\lisa\.planning\AGENT_COORDINATION.md:1) before making substantive edits.

## Repo Priorities

Current priority order:

1. Local development and testability without Raspberry Pi hardware
2. Narrow interface boundaries between voice pipeline components
3. Clear dashboard visibility into status, commands, and failures
4. Hardware-specific behavior only after dev-mode paths exist

## How To Work In This Repo

1. Claim a narrow scope before editing.
2. Keep file ownership tight and explicit.
3. Prefer the simplest solution that satisfies the current requirement.
4. Do not revert or overwrite edits you did not make.
5. If another agent already changed your area, adapt to that work.
6. Surface findings before changing architecture.
7. If a task crosses multiple subsystems, propose the interface first.
8. Be skeptical of abstractions, layers, and configuration that are not yet justified.
9. Favor elegant code paths with fewer moving parts over flexible but premature designs.

## Default Bias

When there is a choice, prefer:

- dev-mode trigger paths over hardware wake-word implementation
- fake or stub device adapters over broad protocol support
- typed transcript injection over mandatory live audio
- explicit contracts over speculative abstractions
- one working integration over an extensible framework
- straightforward implementations over clever or highly configurable ones

## Avoid

Do not do these without explicit instruction:

- broad architectural rewrites
- opportunistic cleanup refactors
- expanding v1 scope to cover multiple device protocols
- replacing a narrow implementation with a generalized framework
- touching unrelated files while working on a scoped task
- introducing abstractions before a second real use case exists

## Suggested Collaboration Format

Before edits:

```text
Claim:
- Goal: ...
- Files: ...
- Non-goals: ...
- Expected output: ...
```

After edits:

```text
Handoff:
- Status: complete / partial / blocked
- Files changed: ...
- Contract introduced: ...
- Tests run: ...
- Risks: ...
- Next recommended step: ...
```

## Project Direction

Treat Lisa v1 as a narrow end-to-end proof, not a full smart-home platform.

That means:

- one concrete integration is better than a protocol abstraction
- one reliable command path is better than feature breadth
- explicit failure behavior is better than silent fallback
- a reproducible local dev loop is more important than Pi-only polish
- the simplest correct design is preferred, even if it feels less future-proof

## Review Posture

Assume the other implementer is a capable junior engineer:

- challenge scope growth aggressively
- question abstractions that are not earned
- look for simpler designs first
- call out code that is technically functional but inelegant
- prefer a small, clear implementation over a reusable system built too early

## If Unsure

If ownership is ambiguous or the task is drifting wider than claimed, stop and narrow the scope before editing.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Lisa**

Lisa is a single-home, voice-triggered smart-home assistant running on a Raspberry Pi 5. V1 is not a general home automation platform. V1 proves one thing: a user can say a short command, Lisa understands it reliably enough, and one configured device responds.

**Core Value:** Say "Hey Lisa, turn off the bedroom lamp" and the lamp turns off quickly and predictably.

### Constraints

- **Latency target:** Median successful command should complete in under 3 seconds on a healthy home network; slower tails are expected and must degrade clearly
- **Internet dependency:** STT and LLM require internet access; when unavailable, Lisa must say that voice understanding is temporarily unavailable
- **Audio reality:** V1 assumes a close or same-room microphone setup, not robust far-field performance
- **Safety:** Lisa must only execute commands within a predefined allowlist of supported actions
- **Complexity budget:** New abstractions must be justified by the first integration, not hypothetical future protocols
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Wake Word Detection
| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **openWakeWord** | **Recommended** | Open-source, runs efficiently on Pi, customizable wake words, active community. Apache 2.0 license. |
| Porcupine (Picovoice) | Not recommended | Commercial license, free tier limited. Good accuracy but vendor lock-in. |
| Snowboy | Avoid | Discontinued. No longer maintained. |
### Speech-to-Text (STT)
| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **OpenAI Whisper API** | **Recommended** | Best accuracy, handles accents well, fast cloud processing. ~$0.006/min. |
| Deepgram API | Alternative | Faster response time, streaming support. Comparable accuracy. |
| Whisper (local) | Not for v1 | Pi 5 4GB can run whisper-tiny but accuracy suffers. Good future fallback. |
| Google Cloud STT | Avoid | More expensive, complex auth setup, less privacy-friendly. |
### Large Language Model (LLM)
| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **Anthropic Claude API** | **Recommended** | Strong instruction following, good at structured output (JSON for device commands), tool use support for device control. |
| OpenAI GPT-4o-mini | Alternative | Lower cost, good quality. Tool use / function calling well-documented. |
| OpenAI GPT-4o | Alternative | Higher quality but higher cost per request. |
### Text-to-Speech (TTS)
| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **Piper TTS** | **Recommended** | Open-source, runs locally on Pi, natural-sounding voices, low latency. No cloud dependency for output. |
| OpenAI TTS API | Alternative | Higher quality voices but adds latency and cost. Good fallback. |
| espeak-ng | Avoid | Robotic quality. Not suitable for conversational assistant. |
### Smart Home Device Control (V1: Single Integration Path)
| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **Philips Hue Bridge API** | **Recommended for v1** | REST API, no extra hardware beyond the bridge, well-documented, lights are the obvious first device. Most homes with smart devices have Hue. |
| Home Assistant REST API | Alternative | If user already runs HA on separate hardware, Lisa can call its API to control any HA entity. Avoids direct protocol work. |
| Wi-Fi smart plug API (Tapo/Kasa) | Alternative | python-kasa library controls TP-Link devices directly over WiFi. No hub needed. Simpler but vendor-locked. |
| MQTT broker + Zigbee2MQTT | Defer to v2 | Powerful but requires USB coordinator hardware + protocol knowledge. Too much infrastructure for v1. |
| Z-Wave JS | Defer to v2+ | Requires Z-Wave USB stick. Not justified until first integration proves the product. |
### Web Dashboard
| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **Python (FastAPI)** | **Recommended backend** | Async, lightweight, good WebSocket support, same language as voice pipeline. |
| **React + Vite** | **Recommended frontend** | Fast builds, component model works well for device cards and status displays. |
| **Tailwind CSS** | **Recommended styling** | Utility-first, rapid UI development, no heavy CSS framework. |
| Flask | Avoid | Sync by default, less suited for real-time device status updates. |
| Next.js | Overkill | SSR not needed for a local network dashboard. |
### Audio Hardware Interface
| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **PyAudio / sounddevice** | **Recommended** | Python bindings for PortAudio. Direct mic access, works with USB mics on Pi. |
| **ALSA** | **Required** | Underlying Linux audio system. Configure once, PyAudio uses it. |
| PulseAudio/PipeWire | Optional | Adds complexity. ALSA direct is simpler for single-mic setup. |
### Orchestration
| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **systemd services** | **Recommended** | Native to Raspberry Pi OS. Auto-start, restart on failure, logging built-in. |
| Docker Compose | Alternative | Cleaner isolation but adds memory overhead on 4GB Pi. |
| PM2 | Avoid | Node.js process manager, wrong ecosystem. |
## Language & Runtime
- **Primary language:** Python 3.11+ — unifies voice pipeline, LLM integration, device control, and web backend
- **Frontend:** TypeScript + React for dashboard
- **System:** Raspberry Pi OS (64-bit, Lite) — no desktop environment needed
## Memory Budget (Pi 5, 4GB)
| Component | Estimated RAM |
|-----------|--------------|
| OS + system services | ~400MB |
| Wake word (openWakeWord) | ~100MB |
| Audio processing (PyAudio) | ~50MB |
| TTS (Piper) | ~200MB |
| FastAPI backend | ~100MB |
| React dashboard (served) | ~0MB (client-side) |
| **Headroom** | **~3.1GB available** |
## What NOT to Use
| Technology | Why Not |
|-----------|---------|
| Home Assistant (full, on same Pi) | Too heavy for "alongside" deployment on 4GB Pi; use its REST API from separate hardware if available |
| Local LLM (llama.cpp) | Pi 5 4GB can't run useful models; cloud API is the right call |
| Snowboy | Dead project, no maintenance |
| Node.js for backend | Fragments the stack; Python unifies voice + LLM + devices |
| Bluetooth for devices | Unreliable range, limited device ecosystem vs Zigbee/WiFi |
| Generic protocol abstraction layer | V1 supports one integration. Don't build abstractions before proving the product. |
| MQTT/Zigbee in v1 | Requires extra hardware (USB coordinator). Choose an API-based integration first. |
## Verification Steps
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
