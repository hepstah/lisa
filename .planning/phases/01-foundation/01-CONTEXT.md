# Phase 1: Foundation - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning (partial context — open areas noted for revisit)

<domain>
## Phase Boundary

Infrastructure, device control via TP-Link Kasa, API server, and web dashboard — all working end-to-end without voice. Users can control devices and inspect system state via the dashboard without touching a terminal.

</domain>

<decisions>
## Implementation Decisions

### Device Integration
- **D-01:** TP-Link Kasa is the v1 device integration (user has Kasa hardware available)
- **D-02:** Use python-kasa library for direct WiFi control — no hub required

### Development Approach
- **D-03:** Dev-mode paths preferred over Pi-specific behavior (per CLAUDE.md)
- **D-04:** Local development and testability without Raspberry Pi hardware is top priority

### Technology Stack (from research)
- **D-05:** Python 3.11+ backend with FastAPI (async, WebSocket support)
- **D-06:** React + Vite + Tailwind CSS for dashboard
- **D-07:** SQLite with WAL mode for state persistence
- **D-08:** systemd for process management on Pi

### Claude's Discretion
- Device adapter interface design (keep narrow — one integration, not a framework)
- Dashboard layout and visual style
- REST API endpoint structure
- WebSocket event format for real-time updates
- Dev-mode fake device adapter for testing without hardware
- Auth approach for local-network API (likely none for v1)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Scope
- `.planning/PROJECT.md` — V1 product definition, narrowing decisions, failure modes, validation criteria
- `.planning/REQUIREMENTS.md` — Phase 1 requirements: INFRA-01..04, DEVICE-02..04, DASH-01..04, ERR-02, ERR-04
- `CLAUDE.md` — Multi-agent coordination rules, default biases, review posture

### Research
- `.planning/research/STACK.md` — Technology recommendations, Kasa listed as alternative, python-kasa library
- `.planning/research/ARCHITECTURE.md` — Component boundaries, build order, data flow
- `.planning/research/PITFALLS.md` — Phase 1 pitfalls: ARM deps, WebSocket drops, SD card corruption

### Coordination
- `.planning/AGENT_COORDINATION.md` — Multi-agent operating rules, claim/handoff format

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — patterns will be established in this phase

### Integration Points
- This phase establishes the foundation that Phase 2 (Voice Pipeline) will integrate with

</code_context>

<specifics>
## Specific Ideas

- Kasa hardware is available for testing
- CLAUDE.md emphasizes: fake/stub device adapters over broad protocol support, typed transcript injection over mandatory live audio, one working integration over extensible framework
- Dev-mode trigger paths take priority over hardware-specific implementation

</specifics>

<deferred>
## Deferred Ideas

### Open Discussion Areas (noted for revisit)
These gray areas were identified but the user deferred discussion. Claude has discretion, but user may want to revisit before or during execution:
- **Device adapter specifics** — which Kasa device types, discovery vs manual config, dev-mode stub design
- **Dashboard design** — layout approach, theme, mobile-responsive or desktop-focused
- **API surface** — endpoint design, WebSocket format, auth approach
- **Dev experience** — testing without hardware, CI approach, hot reload setup

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-04-11*
