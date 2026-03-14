---
phase: 04-constraint-foundation
plan: 02
subsystem: optimizer
tags: [pulp, ilp, constraints, lock, exclude, composite-key]

# Dependency graph
requires:
  - phase: 04-constraint-foundation plan 01
    provides: ConstraintSet dataclass, PreSolveError, check_conflicts, check_feasibility

provides:
  - optimize() with ConstraintSet parameter, composite key deduplication, pre-solve error returns
  - _solve_one_lineup() with locked_card_keys and locked_golfer_names ILP constraints
  - golfer-lock-fires-once tracking via unsatisfied_golfer_locks set
  - card-lock-fires-once tracking via active_card_locks set
  - 6 new behavioral tests for lock/exclude correctness

affects:
  - 04-03-PLAN (Flask route that calls optimize() with session-built ConstraintSet)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Composite key (player, salary, multiplier, collection) for stable cross-request card identity
    - Pre-solve check pattern: check_conflicts -> check_feasibility -> lineup loop
    - Lock-fires-once pattern: discard from active set after placement to prevent multi-lineup infeasibility
    - Exclude pre-filter: applied per lineup iteration before passing pool to ILP solver

key-files:
  created: []
  modified:
    - gbgolf/optimizer/__init__.py
    - gbgolf/optimizer/engine.py
    - tests/test_optimizer.py

key-decisions:
  - "Composite key (player, salary, multiplier, collection) replaces Python id() for cross-request stable deduplication"
  - "Golfer lock fires once globally — discard from unsatisfied_golfer_locks after first placement to prevent lineup 2+ infeasibility"
  - "Card lock fires once — discard from active_card_locks after placement; the used_card_keys mechanism prevents the card from appearing again anyway"
  - "Excluded cards are pre-filtered before _solve_one_lineup — engine.py does not need to know about excludes"

patterns-established:
  - "Pre-solve checks run before lineup loop: early return with empty lineups and infeasibility_notices on any error"
  - "Lock/exclude sets passed to _solve_one_lineup only when non-empty (None default avoids ILP overhead)"
  - "TDD: RED (failing test) committed before GREEN (implementation) to confirm correct test scope"

requirements-completed: [LOCK-01, LOCK-02, EXCL-01, EXCL-02]

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 4 Plan 02: Optimizer Lock/Exclude Engine Integration Summary

**PuLP ILP engine updated to accept locked_card_keys/locked_golfer_names constraints; optimize() orchestrates ConstraintSet pre-solve checks, composite key deduplication, and fires-once lock tracking across sequential lineups**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-14T07:23:31Z
- **Completed:** 2026-03-14T07:27:46Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Updated `_solve_one_lineup()` with two optional ILP constraint params: `locked_card_keys` (card-level force-in) and `locked_golfer_names` (player-level at-least-one)
- Updated `optimize()` with new signature accepting `ConstraintSet`, pre-solve conflict/feasibility checks before lineup loop, and golfer/card lock-fires-once semantics
- Replaced id()-based card deduplication with composite key `(player, salary, multiplier, collection)` throughout
- Added 6 new behavioral tests covering card lock, golfer lock fires-once, exclude card, exclude golfer, conflict error, and salary pre-solve error

## Task Commits

Each task was committed atomically:

1. **Deviation: constraints.py prerequisite** - `f232f54` (feat: Plan 01 Task 2 was uncommitted)
2. **Task 1: _solve_one_lineup() lock params** - `2389608` (feat)
3. **Task 2: RED tests** - `77f50c8` (test)
4. **Task 2: optimize() GREEN implementation** - `eb0d456` (feat)

## Files Created/Modified

- `gbgolf/optimizer/constraints.py` - Created as blocking deviation fix (Plan 01 Task 2 was uncommitted)
- `gbgolf/optimizer/engine.py` - Added `locked_card_keys` and `locked_golfer_names` optional params with ILP constraints
- `gbgolf/optimizer/__init__.py` - New optimize() signature, composite key deduplication, pre-solve checks, lock/exclude orchestration
- `tests/test_optimizer.py` - Updated id() tests to composite key; added 6 behavioral lock/exclude tests

## Decisions Made

- Composite key `(player, salary, multiplier, collection)` replaces `id()` — id() is not stable across Flask requests since Card objects are rebuilt from session data each time
- Golfer lock fires once globally: after a golfer is placed in any lineup, the lock is discarded from `unsatisfied_golfer_locks`. This prevents infeasibility in lineup 2+ when a golfer has only one card (which was already consumed)
- Card lock fires once: after a locked card is placed, it's discarded from `active_card_locks`. The `used_card_keys` mechanism already prevents the card from appearing again, so this is mostly cleanup
- Excludes are a pre-filter (not ILP constraints): simpler and avoids adding potentially many `x[i] == 0` constraints to the ILP

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created constraints.py missing from filesystem**
- **Found during:** Pre-execution dependency check
- **Issue:** Plan 02 imports `from gbgolf.optimizer.constraints import ConstraintSet` but the file did not exist on disk. Plan 01 Task 1 (RED tests) was committed but Task 2 (GREEN implementation) was uncommitted.
- **Fix:** Implemented `gbgolf/optimizer/constraints.py` with ConstraintSet, PreSolveError, check_conflicts, check_feasibility following Plan 01's specification. All 12 test_constraints.py tests went GREEN.
- **Files modified:** `gbgolf/optimizer/constraints.py` (created)
- **Verification:** `python -m pytest tests/ -v` — 52 tests passed after creation
- **Committed in:** `f232f54` (pre-task prerequisite commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Plan 01's missing implementation was a prerequisite; creating it was necessary to unblock Plan 02. No scope creep — only Plan 01's specified interface was implemented.

## Issues Encountered

None - after fixing the blocking prerequisite, plan executed exactly as specified.

## Next Phase Readiness

- `optimize()` now accepts `ConstraintSet` with full lock/exclude orchestration
- `_solve_one_lineup()` accepts lock params via ILP constraints
- Plan 03 (Flask route) can now build a `ConstraintSet` from session data and call `optimize(valid_cards, contests, constraints=cs)`
- All 58 tests passing (full suite green)

---
*Phase: 04-constraint-foundation*
*Completed: 2026-03-14*

## Self-Check: PASSED

- FOUND: gbgolf/optimizer/constraints.py
- FOUND: gbgolf/optimizer/engine.py
- FOUND: gbgolf/optimizer/__init__.py
- FOUND: tests/test_optimizer.py
- FOUND: .planning/phases/04-constraint-foundation/04-02-SUMMARY.md
- Commits f232f54, 2389608, 77f50c8, eb0d456 all verified in git log
- 58 tests passing (full suite green)
