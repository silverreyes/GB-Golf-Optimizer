---
phase: 02-optimization-engine
plan: 02
subsystem: optimizer
tags: [pulp, ilp, linear-programming, optimizer, python, tdd, cbc]

# Dependency graph
requires:
  - phase: 02-optimization-engine
    provides: _solve_one_lineup stub, PuLP installed, 10 failing TDD test stubs (02-01)
  - phase: 01-data-foundation
    provides: Card, ContestConfig dataclasses used as ILP inputs
provides:
  - Working _solve_one_lineup ILP implementation in gbgolf/optimizer/engine.py
  - Working optimize() implementation in gbgolf/optimizer/__init__.py (wired to ILP)
  - 5 optimizer tests now GREEN (salary_constraints, collection_limits, same_player, salary_floor, infeasibility_notice)
affects:
  - 02-03 (multi-lineup / uniqueness — extends optimize() with within-contest disjoint card tracking)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - PuLP ILP formulation pattern: binary x[i] variables, LpMaximize objective, CBC solver with msg=0
    - Collection limits as upper-bound-only constraints (never minimums) — lineup with 0 Weekly Collection cards is legal
    - Same-player constraint: group card indices by player name, add sum <= 1 only when player has >1 card
    - Infeasibility: check pulp.LpStatus[prob.status] == "Optimal"; return None for all other statuses
    - Use varValue > 0.5 (not == 1) to extract CBC binary variable results due to floating-point output

key-files:
  created: []
  modified:
    - gbgolf/optimizer/engine.py
    - gbgolf/optimizer/__init__.py

key-decisions:
  - "Use pulp.LpStatus[prob.status] == 'Optimal' (not status code integer) for feasibility check — more readable and matches PuLP docs"
  - "varValue > 0.5 for CBC result extraction — CBC outputs near-integer floats for binary vars, not exact 0/1"
  - "optimize() wired in same commit as ILP core — required to make tests GREEN (tests call optimize(), not _solve_one_lineup directly)"
  - "Collection limits enforced as upper bounds only — a lineup with 0 Weekly Collection cards is legal even with limit=3"

patterns-established:
  - "ILP pattern: prob += constraint for each business rule; solve with PULP_CBC_CMD(msg=0); status check before extraction"
  - "Infeasibility never raises — _solve_one_lineup returns None, optimize() appends string notice to infeasibility_notices list"
  - "Empty/undersized pool short-circuit: return None before creating LpProblem if len(cards) < config.roster_size"

requirements-completed: [OPT-01, OPT-04, OPT-06]

# Metrics
duration: 10min
completed: 2026-03-14
---

# Phase 2 Plan 02: _solve_one_lineup ILP Implementation Summary

**PuLP ILP solver implemented in engine.py with binary card variables, salary/collection/player constraints solved via CBC, plus optimize() wired to iterate lineups per contest**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-14T00:12:00Z
- **Completed:** 2026-03-14T00:22:00Z
- **Tasks:** 1 (TDD GREEN)
- **Files modified:** 2

## Accomplishments

- Implemented full PuLP ILP formulation in `_solve_one_lineup`: binary variable per card, maximize total effective_value, exact roster size constraint, salary floor, salary cap, collection upper-bound limits, same-player uniqueness within lineup
- Wired `optimize()` to call `_solve_one_lineup` iteratively for each contest/entry with disjoint card pools across lineups
- All 5 target tests pass: `test_tips_salary_constraints`, `test_tips_collection_limits`, `test_same_player_once_per_lineup`, `test_salary_floor_enforced`, `test_infeasibility_notice`
- 23 Phase 1 tests remain GREEN (31 total passing)
- No CBC solver output visible during test runs (msg=0 suppression confirmed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _solve_one_lineup ILP and wire optimize()** - `7f50644` (feat)

## Files Created/Modified

- `gbgolf/optimizer/engine.py` — Full PuLP ILP implementation replacing NotImplementedError stub
- `gbgolf/optimizer/__init__.py` — optimize() wired to call _solve_one_lineup iteratively with disjoint card pool tracking

## Decisions Made

- `pulp.LpStatus[prob.status] == "Optimal"` used for feasibility check — string comparison is more readable than integer status code
- `varValue > 0.5` used for CBC result extraction — CBC outputs near-integer floats for binary variables, not exact 0/1
- `optimize()` needed minimal wiring in the same commit as the ILP core so tests could go GREEN (all 5 target tests call `optimize()` not `_solve_one_lineup` directly)
- Collection limits enforced strictly as upper bounds — a lineup with 0 Weekly Collection cards remains legal when limit is 3

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Wired optimize() to call _solve_one_lineup**
- **Found during:** Task 1 (ILP implementation)
- **Issue:** All 5 target tests call `optimize()`, not `_solve_one_lineup` directly. Plan listed only `engine.py` in `files_modified`, but without wiring `__init__.py`, no test could go GREEN regardless of how correct the ILP was.
- **Fix:** Implemented minimal `optimize()` loop: iterate contests, iterate max_entries times, call `_solve_one_lineup` with available cards (excluding already-used card ids), collect lineups and infeasibility notices
- **Files modified:** gbgolf/optimizer/__init__.py
- **Verification:** All 5 target tests pass; 23 Phase 1 tests remain GREEN
- **Committed in:** 7f50644 (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix required for tests to pass. The plan's success criteria explicitly requires the 5 tests to go GREEN, which requires optimize() to call _solve_one_lineup. No scope creep — optimize() implementation is minimal scaffolding, plan 03 adds within-contest card uniqueness for multi-lineup generation.

## Issues Encountered

- `test_tips_lineup_count` and `test_intermediate_lineup_count` remain failing (as expected per plan spec: "via Plan 03"). With only 12 cards for 3 lineups of 6, there's a mathematical impossibility without card reuse within a contest. Plan 03 addresses within-contest card reuse tracking. Confirmed: 31 tests pass, 2 fail (both are plan 03 targets).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- ILP primitive (`_solve_one_lineup`) fully correct and tested
- `optimize()` wired and producing correct lineups with disjoint card pools across contests
- Plan 03 (`test_tips_lineup_count`, `test_intermediate_lineup_count`) requires within-contest card reuse / same-card exclusion across multiple lineups for the same contest
- STATE.md blocker about Franchise/Rookie CSV columns: still open but not blocking (plan 02 doesn't use franchise/rookie)

## Self-Check: PASSED

- FOUND: gbgolf/optimizer/engine.py (modified)
- FOUND: gbgolf/optimizer/__init__.py (modified)
- FOUND: .planning/phases/02-optimization-engine/02-02-SUMMARY.md
- FOUND: commit 7f50644 (feat: ILP implementation + optimize() wiring)
- VERIFIED: 5 target tests GREEN
- VERIFIED: 23+ Phase 1 tests GREEN

---
*Phase: 02-optimization-engine*
*Completed: 2026-03-14*
