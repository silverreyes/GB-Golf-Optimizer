---
phase: 01-data-foundation
plan: 01
subsystem: testing
tags: [pytest, pydantic, python-dateutil, setuptools, tdd]

# Dependency graph
requires: []
provides:
  - pyproject.toml with dependency declarations and pytest config
  - gbgolf package skeleton (importable gbgolf.data namespace)
  - 6 test stubs in RED state covering roster, projections, matching, filters, config, pipeline
  - conftest.py with shared fixtures (sample_roster_csv, sample_projections_csv, valid_config_dict, tmp_csv_file)
affects: [01-02, 01-03, 01-04]

# Tech tracking
tech-stack:
  added: [pydantic>=2.0, python-dateutil>=2.9, pytest>=8.0, setuptools]
  patterns: [TDD-RED scaffold, lazy imports inside test functions to enable clean collection]

key-files:
  created:
    - pyproject.toml
    - gbgolf/__init__.py
    - gbgolf/data/__init__.py
    - gbgolf/data/__main__.py
    - tests/conftest.py
    - tests/test_roster.py
    - tests/test_projections.py
    - tests/test_matching.py
    - tests/test_filters.py
    - tests/test_config.py
    - tests/test_pipeline.py
  modified: []

key-decisions:
  - "Used setuptools.build_meta instead of setuptools.backends.legacy:build — Python 3.11 pip compatibility"
  - "Moved module-level imports inside test functions so pytest --collect-only succeeds with 0 collection errors (tests fail RED at execution time, not collection time)"

patterns-established:
  - "Lazy imports pattern: all imports from unimplemented modules placed inside test function bodies, not at module level"
  - "conftest.py as single source of truth for test fixture data"

requirements-completed: [UPLD-01, UPLD-02, OPT-05, OPT-07, DATA-01, DATA-02, DATA-03]

# Metrics
duration: 4min
completed: 2026-03-13
---

# Phase 1 Plan 01: Project Scaffold + TDD Test Infrastructure Summary

**pyproject.toml project bootstrap with pydantic+dateutil deps, gbgolf.data package skeleton, and 6 TDD-RED test stubs covering all Phase 1 features**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-13T22:43:49Z
- **Completed:** 2026-03-13T22:47:48Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Installable Python package with pyproject.toml (pydantic, python-dateutil, pytest declared as deps)
- gbgolf.data namespace importable; placeholder CLI entry point in __main__.py raises NotImplementedError
- All 6 test files collected by pytest with 0 collection errors; all tests fail RED on ImportError during execution (correct TDD state for Plans 02-04 to make green)

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold (pyproject.toml + package skeleton)** - `3be7a40` (chore)
2. **Task 2: Test scaffold — conftest.py + 6 failing test stubs** - `41fb7c2` (test)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `pyproject.toml` - Project metadata, dependency declarations, pytest config with testpaths=["tests"] and addopts="-x -q"
- `gbgolf/__init__.py` - Empty package marker
- `gbgolf/data/__init__.py` - Module docstring declaring public API (load_cards, load_config, validate_pipeline)
- `gbgolf/data/__main__.py` - Placeholder CLI entry point raising NotImplementedError
- `tests/conftest.py` - Shared fixtures: sample_roster_csv (7-player CSV with all GameBlazers columns), sample_projections_csv, valid_config_dict (2 contests), tmp_csv_file
- `tests/test_roster.py` - 3 stubs for UPLD-01 (parse_roster_csv)
- `tests/test_projections.py` - 3 stubs for projections parsing
- `tests/test_matching.py` - 5 stubs for normalize_name and match_projections
- `tests/test_filters.py` - 5 stubs for DATA-01/02/03 apply_filters
- `tests/test_config.py` - 3 stubs for OPT-07 load_contest_config
- `tests/test_pipeline.py` - 4 stubs for OPT-05 validate_pipeline and CLI

## Decisions Made

- Used `setuptools.build_meta` instead of `setuptools.backends.legacy:build` — the newer backend syntax is not available in this environment's setuptools version
- Moved all `from gbgolf.data.*` imports inside test function bodies rather than at module level — this is required because pytest collection executes module-level code, and top-level ImportError causes collection errors (ERRORS, not FAILED), which would violate the RED-state spec

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed build-backend for Python 3.11 / pip 24 compatibility**
- **Found during:** Task 1 (Project scaffold)
- **Issue:** `setuptools.backends.legacy:build` requires setuptools >=68.3 with the new backends API; pip 24 in this environment lacks it
- **Fix:** Changed build-backend to `setuptools.build_meta` (standard, widely compatible)
- **Files modified:** pyproject.toml
- **Verification:** `pip install -e ".[dev]"` exits 0; all deps installed
- **Committed in:** 3be7a40 (Task 1 commit)

**2. [Rule 1 - Bug] Moved test imports inside function bodies to achieve RED (not ERROR) state**
- **Found during:** Task 2 (Test scaffold)
- **Issue:** Top-level `from gbgolf.data.config import load_contest_config` causes `ModuleNotFoundError` during pytest collection — pytest reports these as `ERROR` in collection, not `FAILED` during execution. Plan requires "all test stubs fail RED" meaning FAILED not ERROR.
- **Fix:** Moved all imports from unimplemented modules inside test function bodies. pytest --collect-only now shows 6 files, 23 tests, 0 errors.
- **Files modified:** all 6 test files
- **Verification:** `pytest tests/ --collect-only -q` shows all tests collected; `pytest tests/ -q` exits with FAILED (not ERROR)
- **Committed in:** 41fb7c2 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking build config, 1 bug in test design)
**Impact on plan:** Both auto-fixes required for correctness. No scope creep.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Test scaffold ready: Plans 02, 03, 04 each have failing tests waiting to be made green
- Import paths established: `gbgolf.data.roster`, `gbgolf.data.projections`, `gbgolf.data.matching`, `gbgolf.data.filters`, `gbgolf.data.config`, `gbgolf.data.models`
- Fixtures available in conftest.py with realistic GameBlazers sample data including edge cases (zero salary, expired card, no projection match)

---
*Phase: 01-data-foundation*
*Completed: 2026-03-13*
