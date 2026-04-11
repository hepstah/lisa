# Features Research: Lisa (Voice-Controlled Home Assistant)

**Researched:** 2026-04-11
**Domain:** Raspberry Pi voice assistant with cloud LLM + smart home control
**Ecosystem:** Rhasspy, Home Assistant Voice, Mycroft/OpenVoiceOS, custom builds

## Table Stakes

Features users expect from any voice-controlled home assistant. Missing these = broken product.

| Feature | Complexity | Dependencies | Notes |
|---------|-----------|--------------|-------|
| **Wake word detection** | Medium | Audio hardware, microphone | Must work reliably in ambient noise. False positive rate is critical. |
| **Speech-to-text** | Low (cloud) | Internet connection, mic | Cloud STT is near-solved. Accuracy is table stakes. |
| **Natural language understanding** | Low (cloud) | LLM API | LLM handles intent parsing. Must extract device + action + parameters. |
| **Text-to-speech response** | Medium | Speaker/audio output | Must sound natural, not robotic. Latency matters. |
| **Device on/off control** | Medium | One chosen device integration | "Turn on the lights" must work. The core promise. V1: one integration path only. |
| **Explicit failure handling** | Medium | All pipeline stages | Every failure mode (no speech, STT timeout, bad intent, device offline, no internet) must produce spoken feedback + dashboard entry. Not silence. |
| **Device status visibility** | Low | Dashboard, device integration | User needs to see what's on/off. Dashboard shows current state + command history. |
| **Configuration without shell** | Medium | Dashboard UI | Configure the initial device integration through the dashboard, not config files or SSH. |

## Differentiators

Features that set Lisa apart from basic voice assistants or existing solutions.

| Feature | Complexity | Dependencies | Notes |
|---------|-----------|--------------|-------|
| **Conversational AI (LLM-backed)** | Medium | Cloud LLM API | Most DIY assistants use rigid intent matching. LLM enables natural conversation. This IS Lisa's differentiator. |
| **Contextual follow-ups** | Medium | LLM conversation memory | "Turn on the living room lights" → "Make them dimmer" — LLM tracks context. |
| **Proactive suggestions** | High | Usage patterns, LLM | "You usually turn off the porch light at 11pm. Want me to do that?" |
| **Local-first privacy** | Low | Architecture choice | Wake word + TTS run locally. Only voice commands hit the cloud. Audio not stored. |
| **Multi-room audio** | High | Multiple Pis, networking | Multiple Pis with mics, coordinated wake word. Defer to v2+. |
| **Voice identification** | High | Speaker recognition model | Know WHO is speaking. Complex, defer. |
| **Text/typed fallback** | Low | Dashboard input | Type commands in dashboard when voice isn't convenient. |
| **Command history/log** | Low | Database, dashboard | See what was asked and what happened. Debugging + trust. |
| **Automation rules** | Medium | Rule engine, scheduler | "Turn off lights at 11pm" / "If motion sensor, turn on hallway light." |
| **Scene/group control** | Medium | Device grouping logic | "Goodnight" → turns off all lights, locks doors, sets thermostat. |
| **REST API for extensibility** | Low | FastAPI endpoints | Let other tools/scripts trigger Lisa actions. |
| **Custom wake word** | Low | openWakeWord training | Change "Hey Lisa" to anything. Training pipeline needed. |

## Anti-Features

Things to deliberately NOT build. Including these would hurt the project.

| Anti-Feature | Why Not |
|-------------|---------|
| **Generic multi-protocol abstraction (v1)** | Don't build a universal smart home protocol layer. V1 supports exactly one integration path. Prove end-to-end before abstracting. |
| **Local LLM on Pi 4GB** | Can't run useful models. Cloud API is the right call. Don't waste time trying. |
| **Native mobile app** | Web dashboard works on phones. App stores add massive complexity for no v1 value. |
| **Multi-user voice recognition** | Speaker identification is a research problem. Single-user for v1. |
| **Remote access (internet-facing)** | Security nightmare. Local network only for v1. Use VPN if needed. |
| **Video/camera features** | Different domain. Adds hardware requirements, storage, processing. Out of scope. |
| **Custom automation engine** | Don't build a full rule engine. Simple time-based + trigger-based rules in v1. Node-RED or HA for complex flows. |
| **Hardware enclosure design** | Pi runs bare or in generic case. Don't scope 3D printing or custom hardware. |
| **Plugin/skill marketplace** | Massive infrastructure. Extensibility via REST API is sufficient. |

## Feature Dependencies

```
Wake Word Detection
  └── Audio Capture (mic + PyAudio)
       └── Speech-to-Text (cloud)
            └── LLM Intent Parsing (cloud)
                 ├── Device Control (MQTT)
                 │    └── Device Status (dashboard)
                 └── Text-to-Speech Response (local)

Dashboard
  ├── Device Status Display
  ├── Device Configuration
  ├── Command History
  ├── Text Input Fallback
  └── Automation Rules UI

Automation Rules
  ├── Scheduler (time-based)
  └── Device Events (trigger-based)
```

## MVP Recommendation

Aligned with PROJECT.md v1 scope — prove one end-to-end device path:

1. Wake word detection ("Hey Lisa") with acceptable false-trigger rate
2. Short utterance capture + cloud STT
3. Cloud LLM intent parsing into small set of supported intents
4. Local TTS spoken confirmation/error
5. One concrete device integration (e.g., Hue lights) controlled end-to-end
6. Web dashboard: assistant status, command history, device configuration for that one integration
7. Explicit failure handling for all pipeline failure modes

V1 does NOT include: automation rules, multi-protocol support, discovery, or generic device frameworks. Everything else is v2+.

---
*Researched: 2026-04-11*
