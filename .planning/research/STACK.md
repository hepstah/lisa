# Stack Research: Lisa (Voice-Controlled Home Assistant)

**Researched:** 2026-04-11
**Domain:** Raspberry Pi voice assistant with cloud LLM + smart home control

## Recommended Stack

### Wake Word Detection

| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **openWakeWord** | **Recommended** | Open-source, runs efficiently on Pi, customizable wake words, active community. Apache 2.0 license. |
| Porcupine (Picovoice) | Not recommended | Commercial license, free tier limited. Good accuracy but vendor lock-in. |
| Snowboy | Avoid | Discontinued. No longer maintained. |

**Confidence:** High — openWakeWord is the clear open-source leader for custom wake words on embedded devices.

### Speech-to-Text (STT)

| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **OpenAI Whisper API** | **Recommended** | Best accuracy, handles accents well, fast cloud processing. ~$0.006/min. |
| Deepgram API | Alternative | Faster response time, streaming support. Comparable accuracy. |
| Whisper (local) | Not for v1 | Pi 5 4GB can run whisper-tiny but accuracy suffers. Good future fallback. |
| Google Cloud STT | Avoid | More expensive, complex auth setup, less privacy-friendly. |

**Confidence:** High — Cloud STT is the right call given the cloud LLM architecture. Whisper API has the best price/quality ratio.

### Large Language Model (LLM)

| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **Anthropic Claude API** | **Recommended** | Strong instruction following, good at structured output (JSON for device commands), tool use support for device control. |
| OpenAI GPT-4o-mini | Alternative | Lower cost, good quality. Tool use / function calling well-documented. |
| OpenAI GPT-4o | Alternative | Higher quality but higher cost per request. |

**Confidence:** Medium — Both Claude and GPT-4o-mini work well. Choice depends on preference. Tool/function calling is the key feature for device control.

### Text-to-Speech (TTS)

| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **Piper TTS** | **Recommended** | Open-source, runs locally on Pi, natural-sounding voices, low latency. No cloud dependency for output. |
| OpenAI TTS API | Alternative | Higher quality voices but adds latency and cost. Good fallback. |
| espeak-ng | Avoid | Robotic quality. Not suitable for conversational assistant. |

**Confidence:** High — Piper is the standard for local TTS on Pi. Keeps response snappy by avoiding another cloud round-trip.

### Smart Home Device Control (V1: Single Integration Path)

V1 supports ONE device integration. Pick one and prove end-to-end before abstracting.

| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **Philips Hue Bridge API** | **Recommended for v1** | REST API, no extra hardware beyond the bridge, well-documented, lights are the obvious first device. Most homes with smart devices have Hue. |
| Home Assistant REST API | Alternative | If user already runs HA on separate hardware, Lisa can call its API to control any HA entity. Avoids direct protocol work. |
| Wi-Fi smart plug API (Tapo/Kasa) | Alternative | python-kasa library controls TP-Link devices directly over WiFi. No hub needed. Simpler but vendor-locked. |
| MQTT broker + Zigbee2MQTT | Defer to v2 | Powerful but requires USB coordinator hardware + protocol knowledge. Too much infrastructure for v1. |
| Z-Wave JS | Defer to v2+ | Requires Z-Wave USB stick. Not justified until first integration proves the product. |

**Confidence:** Medium — Hue Bridge is the lowest-friction first integration. But this is a Required Product Choice (see PROJECT.md) that the user must confirm.

### Web Dashboard

| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **Python (FastAPI)** | **Recommended backend** | Async, lightweight, good WebSocket support, same language as voice pipeline. |
| **React + Vite** | **Recommended frontend** | Fast builds, component model works well for device cards and status displays. |
| **Tailwind CSS** | **Recommended styling** | Utility-first, rapid UI development, no heavy CSS framework. |
| Flask | Avoid | Sync by default, less suited for real-time device status updates. |
| Next.js | Overkill | SSR not needed for a local network dashboard. |

**Confidence:** High — FastAPI + React is a well-proven lightweight stack for dashboards.

### Audio Hardware Interface

| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **PyAudio / sounddevice** | **Recommended** | Python bindings for PortAudio. Direct mic access, works with USB mics on Pi. |
| **ALSA** | **Required** | Underlying Linux audio system. Configure once, PyAudio uses it. |
| PulseAudio/PipeWire | Optional | Adds complexity. ALSA direct is simpler for single-mic setup. |

**Confidence:** High — PyAudio over ALSA is the standard approach on Pi.

### Orchestration

| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| **systemd services** | **Recommended** | Native to Raspberry Pi OS. Auto-start, restart on failure, logging built-in. |
| Docker Compose | Alternative | Cleaner isolation but adds memory overhead on 4GB Pi. |
| PM2 | Avoid | Node.js process manager, wrong ecosystem. |

**Confidence:** Medium — systemd is lighter on resources. Docker is cleaner but costs ~200-400MB RAM overhead.

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

Comfortable fit. No memory pressure expected.

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

Before committing to this stack:
1. Test openWakeWord on Pi 5 with USB mic — confirm wake word accuracy
2. Measure end-to-end latency: wake word → STT → LLM → TTS → speaker
3. Confirm Piper TTS voice quality meets expectations
4. Test MQTT round-trip with a smart plug or bulb

---
*Researched: 2026-04-11*
