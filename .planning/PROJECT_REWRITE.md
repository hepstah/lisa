# Lisa

## What This Is

Lisa is a single-home, voice-triggered smart-home assistant running on a Raspberry Pi 5. V1 is not a general home automation platform. V1 proves one thing: a user can say a short command, Lisa understands it reliably enough, and one configured device responds.

## Core Value

Say "Hey Lisa, turn off the bedroom lamp" and the lamp turns off quickly and predictably.

## V1 Product Definition

V1 is successful if it delivers all of the following:

- Wake word detection on the Pi
- Short voice command capture after wake word
- Cloud speech-to-text and cloud LLM intent parsing
- Local spoken confirmation
- Control of a small, explicitly supported device set
- Simple local-network web dashboard for status and configuration

V1 does not attempt to be a full smart-home hub, a multi-room voice assistant, or a generic automation engine.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet)

### Active

- [ ] Detect the wake phrase "Hey Lisa" locally on the Pi with acceptable false-trigger rate in a normal home environment
- [ ] Capture a short utterance after wake word and send it to a cloud STT provider
- [ ] Convert transcribed commands into one of a small set of supported intents using a cloud LLM
- [ ] Speak a short confirmation or error response locally
- [ ] Control one concrete initial integration end to end
- [ ] Provide a dashboard to show assistant status, recent commands, and configured devices
- [ ] Provide a simple device configuration flow for the initial integration only
- [ ] Define explicit failure behavior for no internet, provider timeout, and unknown intent

### Out of Scope

- Support for multiple device protocols in v1
- Generic protocol-agnostic device framework in v1
- Zigbee radio management in v1
- Z-Wave radio management in v1
- Arbitrary device discovery across protocols in v1
- User-defined automation rules in v1
- Mobile app
- Local LLM inference
- Multi-user voice recognition
- Video or camera features
- Custom hardware enclosure

## V1 Narrowing Decisions

These are hard constraints for v1, not placeholders.

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use cloud AI services | Pi 5 4GB is not the place to force local STT + LLM quality | Decided |
| Support one initial device path | Prove the end-to-end product before building abstractions | Decided |
| Dashboard is local-network only | Reduces auth and exposure complexity for first release | Decided |
| No automation engine in v1 | Scheduled rules add a separate reliability and UX surface | Decided |
| Prefer existing hub or API integration over direct multi-protocol radio support | Avoids turning v1 into infrastructure work | Decided |

## Required Product Choices

The project should not proceed beyond setup until these are chosen and written down:

1. Initial device integration
   Example: Home Assistant entity control, Hue bridge light control, or a single Wi-Fi plug API
2. Cloud STT provider
3. Cloud LLM provider
4. Local TTS engine
5. Wake-word engine

If any of these remain undecided, the project is not ready for implementation planning.

## Context

- **Platform:** Raspberry Pi 5 with 4GB RAM, running headless on the local network
- **Primary UX:** One wake phrase, one short spoken command, one device action, one concise spoken response
- **Voice pipeline:** Local wake word -> cloud STT -> cloud LLM intent parsing -> local TTS
- **Device model:** Explicitly limited to one supported integration path for v1
- **Dashboard:** Browser-based UI on the local network for setup and visibility, not remote access

## Constraints

- **Latency target:** Median successful command should complete in under 3 seconds on a healthy home network; slower tails are expected and must degrade clearly
- **Internet dependency:** STT and LLM require internet access; when unavailable, Lisa must say that voice understanding is temporarily unavailable
- **Audio reality:** V1 assumes a close or same-room microphone setup, not robust far-field performance
- **Safety:** Lisa must only execute commands within a predefined allowlist of supported actions
- **Complexity budget:** New abstractions must be justified by the first integration, not hypothetical future protocols

## Failure Modes

V1 must define and handle these cases explicitly:

- Wake word heard, but no intelligible speech captured
- STT provider timeout or failure
- LLM returns an unsupported or ambiguous intent
- Target device is offline or command fails
- Internet unavailable

The expected behavior for each case should include:

- What the user hears
- What appears in the dashboard
- Whether a retry is attempted

## Validation Criteria

V1 should only be considered validated when all of the following are true:

- A user can configure the initial supported device path without shell access
- At least one real device can be controlled by voice end to end
- Recent command history shows success and failure states clearly
- Failure cases produce understandable spoken feedback
- The system is stable enough for repeated daily use in one home setup

## Non-Goals for This Document

This document is not trying to predict the final product architecture. It is intentionally restrictive so the first shipped version can prove whether the product is worth expanding.

## Evolution

Update this document only when one of these changes:

1. The initial supported integration is chosen
2. A requirement is validated by shipped behavior
3. A scoped v1 item is cut or added
4. A failure-mode expectation changes
5. V1 is complete and the project is ready to expand beyond a single integration

---
*Draft rewrite created on 2026-04-11 as an execution-safe alternative to the initial PROJECT.md.*
