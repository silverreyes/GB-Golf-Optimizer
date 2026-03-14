---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Manual Lock/Exclude
status: planning
stopped_at: Phase 4 context gathered
last_updated: "2026-03-14T07:05:53.775Z"
last_activity: 2026-03-14 — v1.1 roadmap created
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Generate the best possible cash contest lineups from the user's available player cards, maximizing expected score within salary and collection constraints.
**Current focus:** Phase 4 — Constraint Foundation

## Current Position

Phase: 4 of 7 (Constraint Foundation)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-14 — v1.1 roadmap created

Progress: [░░░░░░░░░░] 0% (v1.1)

## Accumulated Context

### Decisions

All key decisions logged in PROJECT.md Key Decisions table.

Recent decisions affecting current work:
- Session architecture: Lock/exclude identifiers stored in Flask built-in cookie session (fits comfortably under 4KB). Card objects NOT stored in session — serialized to hidden form field instead.
- Stable card key: Use composite (player, salary, multiplier, collection) key rather than Python id() — id() breaks across requests.
- No new dependencies: Flask session + PuLP += constraint API + Jinja2 checkboxes covers all v1.1 needs without additions.

### Pending Todos

None.

### Blockers/Concerns

- Phase 4 risk: Lock constraint semantics in the multi-lineup sequential loop. Card-level locks can only fire once (card consumed). Golfer-level locks may become infeasible in lineup 2+ if golfer has only one card. See PITFALLS.md for full checklist.

## Session Continuity

Last session: 2026-03-14T07:05:53.773Z
Stopped at: Phase 4 context gathered
Resume file: .planning/phases/04-constraint-foundation/04-CONTEXT.md
