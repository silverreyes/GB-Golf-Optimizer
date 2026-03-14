---
phase: 02-optimization-engine
plan: 01
subsystem: optimizer
tags: [pulp, ilp, linear-programming, optimizer, python, tdd]

# Dependency graph
requires:
  - phase: 01-data-foundation
    provides: Card, ContestConfig, ValidationResult dataclasses used as optimizer inputs
provides:
  - gbgolf.optimizer public API (optimize, OptimizationResult, Lineup)
  - ILP engine skeleton (gbgolf/optimizer/engine.py with _solve_one_lineup stub)
  - 10 failing optimizer test stubs establishing the RED TDD baseline
  - pulp>=3.3.0 installed and in pyproject.toml
affects:
  - 02-02 (ILP core implementation — implements against test contract and engine stub)
  - 02-03 (multi-lineup / uniqueness — extends engine, all tests still apply)

# Tech tracking
tech-stack:
  added: [pulp 3.3.0]
  patterns:
    - TDD RED baseline — tests import cleanly but fail with NotImplementedError at runtime
    - Module-level card fixtures in test files for fast, isolated optimizer tests (no CSV pipeline)
    - Optimizer stubs raise NotImplementedError — enforces TDD discipline across downstream plans
    - Public API via __all__ in optimizer __init__.py

key-files:
  created:
    - gbgolf/optimizer/__init__.py
    - gbgolf/optimizer/engine.py
    - tests/test_optimizer.py
  modified:
    - pyproject.toml

key-decisions:
  - "PuLP 3.3.0 chosen as the ILP solver library — pure Python, no binary dependency, available on Windows"
  - "Lineup.__post_init__ computes total_salary, total_projected_score, total_effective_value eagerly — avoids recomputation in tests and UI"
  - "Optimizer tests use module-level Card objects (not CSV pipeline) — fast, isolated, no I/O"
  - "NotImplementedError propagates naturally in test stubs (not wrapped in pytest.raises) — true RED state, not hidden pass"

patterns-established:
  - "TDD pattern: all stubs raise NotImplementedError; plans 02-02+ implement GREEN in-place"
  - "Card identity: use id(card) for cross-lineup uniqueness checks (object identity, not value equality)"
  - "Infeasibility: returns OptimizationResult with empty/partial lineups + infeasibility_notices strings, never raises"

requirements-completed: [OPT-01, OPT-02, OPT-03, OPT-04, OPT-06]

# Metrics
duration: 8min
completed: 2026-03-14
---

# Phase 2 Plan 01: Optimizer Scaffold and RED Baseline Summary

**PuLP ILP solver installed, optimizer module skeleton created (Lineup/OptimizationResult/optimize stubs), and 10 failing TDD test stubs establishing the full optimizer contract**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-14T00:03:17Z
- **Completed:** 2026-03-14T00:11:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Installed PuLP 3.3.0 and added it to pyproject.toml dependencies
- Created `gbgolf/optimizer/__init__.py` with `Lineup`, `OptimizationResult` dataclasses and `optimize()` stub
- Created `gbgolf/optimizer/engine.py` with `_solve_one_lineup()` stub importing pulp and Phase 1 types
- Wrote 10 failing test stubs in `tests/test_optimizer.py` covering all OPT-01 through OPT-06 requirements
- Confirmed RED state: all 10 optimizer tests collect cleanly and fail with NotImplementedError
- Confirmed 23 Phase 1 tests remain GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Add PuLP dependency and create optimizer module skeleton** - `f773c8c` (feat)
2. **Task 2: Write failing test stubs for optimizer (RED baseline)** - `78eb910` (test)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `gbgolf/optimizer/__init__.py` — Public API: Lineup, OptimizationResult dataclasses + optimize() stub
- `gbgolf/optimizer/engine.py` — ILP engine skeleton: _solve_one_lineup() stub with pulp import
- `tests/test_optimizer.py` — 10 failing test stubs covering lineup count, salary/collection constraints, player uniqueness, cross-contest card disjointness, infeasibility handling
- `pyproject.toml` — Added pulp>=3.3.0 to dependencies list

## Decisions Made

- PuLP 3.3.0 chosen as the ILP solver library — pure Python, no binary dependency, available on Windows
- `Lineup.__post_init__` computes totals eagerly (total_salary, total_projected_score, total_effective_value) to avoid recomputation in downstream tests and formatter code
- Optimizer tests use module-level `Card` objects directly, not the CSV/pipeline path — keeps tests fast and isolated from I/O
- `NotImplementedError` propagates naturally in test stubs rather than being wrapped in `pytest.raises` — this is true RED state (the tests genuinely fail, not pass on expected exception)
- Card identity for uniqueness checks uses `id(card)` (object identity) per plan spec

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `pip install pulp` used bare `pip` which resolved to Python 3.12's pip while the project runs on Python 3.11. Fixed by using `python -m pip install pulp>=3.3.0` which installs into the correct interpreter. No plan change needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED baseline established: Plans 02-02 and 02-03 can implement GREEN against exact test names
- `gbgolf.optimizer` module importable, public API defined
- `_solve_one_lineup` stub ready for ILP implementation in 02-02
- Blocker from STATE.md still open: confirm whether same golfer can appear on two different cards in one lineup (affects ILP constraint in 02-02)

## Self-Check: PASSED

- FOUND: gbgolf/optimizer/__init__.py
- FOUND: gbgolf/optimizer/engine.py
- FOUND: tests/test_optimizer.py
- FOUND: .planning/phases/02-optimization-engine/02-01-SUMMARY.md
- FOUND: commit f773c8c (feat: PuLP dependency + optimizer skeleton)
- FOUND: commit 78eb910 (test: 10 failing optimizer stubs)

---
*Phase: 02-optimization-engine*
*Completed: 2026-03-14*
