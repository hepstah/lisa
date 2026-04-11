# Agent Coordination

This repo may be worked on by multiple AI agents in parallel. The point of this file is to reduce overlap, prevent accidental reverts, and force clean handoffs.

## Operating Rules

1. Do not rewrite broad architecture unless explicitly asked.
2. Claim a narrow area before editing.
3. Report findings before making large or cross-cutting changes.
4. Do not revert edits you did not make.
5. If another agent changed files in your area, adapt to those changes instead of replacing them.
6. Prefer additive patches over opportunistic refactors.
7. Shared contracts should be written down before multiple agents implement against them.
8. Optimize for local-dev testability before hardware-specific behavior.

## Recommended Division Of Labor

- One agent owns planning, interfaces, prompts, and review.
- One agent owns implementation of a narrow slice.
- Nobody performs cleanup refactors outside their claimed scope.
- If work crosses subsystem boundaries, stop and publish the proposed interface first.

## Work Claim Format

Before making edits, post a claim in this format:

```text
Claim:
- Goal: add dev-mode trigger abstraction
- Files: src/voice/trigger.py, src/config.py
- Non-goals: no dashboard changes, no STT changes
- Expected output: manual trigger implementation + config flag
```

Rules for claims:

- Keep the file list as tight as possible.
- State what is explicitly out of scope.
- If the task is exploratory, say that no edits are planned yet.

## Handoff Format

When pausing or finishing, post a handoff in this format:

```text
Handoff:
- Status: complete / partial / blocked
- Files changed: ...
- Contract introduced: ...
- Tests run: ...
- Risks: ...
- Next recommended step: ...
```

Rules for handoffs:

- Always list exact files changed.
- If no tests were run, say so directly.
- Call out assumptions that may break another agent's work.

## Coordination Message To Share

Use this message in another terminal when working with a second agent:

```text
We’re sharing the same repo. I want you to act as a parallel collaborator, not an independent planner.

Rules:
1. Do not rewrite broad architecture unless asked.
2. Claim a narrow area before editing.
3. Report findings before making big changes.
4. If you touch files, list exact files changed.
5. Do not revert edits you didn’t make.
6. If you see my changes, adapt to them instead of replacing them.
7. Prefer additive patches over refactors unless the refactor is the task.
8. End every update with:
   - Status
   - Files touched
   - Risks / assumptions
   - Suggested next step
```

## Project-Specific Guidance

For this project, local development matters more than hardware integration right now.

Prefer work in this order:

1. Dev-mode execution paths
2. Interface boundaries between trigger, STT, intent parsing, device control, and TTS
3. Dashboard visibility and interaction history
4. Hardware-specific Pi behavior

Good candidate split:

- Agent A: planning docs, interface proposals, prompt design, edge-case review
- Agent B: implementation of agreed interfaces and dev-mode paths

## Anti-Patterns

Avoid these behaviors:

- Two agents editing the same subsystem without a claim
- Refactoring unrelated files while implementing a narrow task
- Replacing another agent's design without first writing down the disagreement
- Mixing planning, infra, UI, and device support into one unchecked patch
- Declaring something "done" without saying what was actually tested

## Default Rule

If there is any ambiguity about ownership, stop and narrow the task before editing.
