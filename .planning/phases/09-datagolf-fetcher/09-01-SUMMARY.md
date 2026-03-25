---
phase: 09-datagolf-fetcher
plan: 01
subsystem: api
tags: [httpx, pydantic, datagolf, fetch, name-normalization, sqlalchemy-core]

# Dependency graph
requires:
  - phase: 08-database-foundation
    provides: fetches and projections table definitions, db instance, app/db_session fixtures
provides:
  - DataGolf fetch pipeline (gbgolf/fetcher.py) with 4 exported functions
  - parse_datagolf_name for "Last, First" to "First Last" conversion
  - write_projections atomic DELETE CASCADE + INSERT pattern
  - run_fetch orchestrator with 30-player guard and error handling
  - write_fetch_log one-liner append logging
  - _DataGolfPlayerProjection Pydantic boundary model (proj_points_total field)
  - 15 unit tests covering FETCH-01, FETCH-03, FETCH-04, FETCH-06
  - Raw API response sample at scripts/datagolf_response_sample.json
affects: [10-cli-integration, 11-deployment]

# Tech tracking
tech-stack:
  added: [httpx>=0.28]
  patterns: [Pydantic boundary model with ConfigDict(extra="ignore"), monkeypatch httpx.get for API mocking, atomic DELETE CASCADE + INSERT for upsert, file-append logging]

key-files:
  created: [gbgolf/fetcher.py, tests/test_fetcher.py, scripts/datagolf_response_sample.json]
  modified: [pyproject.toml, .gitignore]

key-decisions:
  - "DataGolf API field for projected points is proj_points_total (confirmed via live discovery)"
  - "Tournament name available as top-level event_name field in API response"
  - "API response is dict with projections list (not flat list) -- Pydantic model validates individual player objects"
  - "SQLite reuses IDs after DELETE -- tests verify replacement behavior by checking player names, not IDs"

patterns-established:
  - "Pydantic boundary model: _DataGolfPlayerProjection with model_validate() and extra='ignore'"
  - "httpx mocking: monkeypatch httpx.get with MockResponse class (no pytest-httpx dependency needed)"
  - "Fetch logging: simple file.write append to logs/fetch.log, no Python logging module"
  - "Name pipeline: parse_datagolf_name() for format, normalize_name() available for matching"

requirements-completed: [FETCH-01, FETCH-03, FETCH-04, FETCH-06]

# Metrics
duration: 4min
completed: 2026-03-25
---

# Phase 9 Plan 1: DataGolf Fetcher Summary

**DataGolf fetch pipeline with httpx API client, Pydantic boundary validation, atomic DB upsert, 30-player guard, and file-append logging -- 15 tests all green**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-25T22:54:42Z
- **Completed:** 2026-03-25T22:59:12Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Live API discovery confirmed field names: `proj_points_total` for projected points, `event_name` for tournament name, 134 players in response
- Full fetch pipeline: API call -> Pydantic validation -> name normalization -> atomic DB write -> log entry
- 30-player guard prevents bad API responses from overwriting good data in the database
- Atomic DELETE CASCADE + INSERT pattern ensures only one fetch + N projections per tournament at any time
- 15 unit tests covering all behaviors including error paths, guard logic, and idempotency
- Full test suite (105 tests) passes with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add httpx dependency, gitignore logs/, and run live API discovery** - `a641266` (chore)
2. **Task 2 RED: Add failing tests for DataGolf fetcher module** - `a534ddb` (test)
3. **Task 2 GREEN: Implement DataGolf fetcher with full test suite** - `bf8316a` (feat)

_TDD flow: Task 2 RED wrote 15 failing tests, Task 2 GREEN implemented code to pass them._

## Files Created/Modified
- `gbgolf/fetcher.py` - DataGolf fetch pipeline: parse_datagolf_name, write_fetch_log, write_projections, run_fetch, _DataGolfPlayerProjection Pydantic model
- `tests/test_fetcher.py` - 15 unit tests covering FETCH-01, FETCH-03, FETCH-04, FETCH-06 and idempotency
- `scripts/datagolf_response_sample.json` - Raw API response (134 players) for field name reference
- `pyproject.toml` - Added httpx>=0.28 to dependencies
- `.gitignore` - Added logs/ and instance/ directories

## Decisions Made
- DataGolf API projected points field is `proj_points_total` (confirmed from live discovery call, not `fantasy_points` or `proj_points` as speculated)
- Tournament name is available as top-level `event_name` field -- no need for secondary API call
- API response is a dict with `projections` key containing player list, plus metadata (`event_name`, `last_updated`, `site`, `slate`, `tour`)
- SQLite reuses auto-increment IDs after DELETE, so stale-replacement test verifies by player names rather than comparing fetch IDs
- MockResponse class with monkeypatch for httpx testing (no external test dependency needed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale-replacement test for SQLite ID reuse**
- **Found during:** Task 2 GREEN phase
- **Issue:** `test_write_projections_replaces_stale` assumed old and new fetch IDs would differ, but SQLite reuses IDs after DELETE
- **Fix:** Changed test assertions to verify by player names (Old Player gone, New Player A/B present) instead of comparing fetch_id values
- **Files modified:** tests/test_fetcher.py
- **Verification:** All 15 tests pass
- **Committed in:** bf8316a (Task 2 GREEN commit)

**2. [Rule 3 - Blocking] Added instance/ to .gitignore**
- **Found during:** Post-task verification
- **Issue:** Flask test runs created `instance/` directory (Flask default for SQLite DB files)
- **Fix:** Added `instance/` to .gitignore
- **Files modified:** .gitignore
- **Committed in:** docs commit

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above. API discovery call succeeded on first attempt. All tests passed after the SQLite ID reuse fix.

## User Setup Required

None - DATAGOLF_API_KEY was already configured in `.env` from Phase 8 setup. The httpx dependency installs automatically via pip.

## Next Phase Readiness
- Fetcher module ready for Phase 9 Plan 2 (Flask CLI command registration and cron documentation)
- All 4 exported functions available: `parse_datagolf_name`, `write_fetch_log`, `write_projections`, `run_fetch`
- `run_fetch()` accepts `log_dir` parameter for flexible log file placement
- API field names confirmed and hardcoded in Pydantic model -- no discovery needed in future plans

## Self-Check: PASSED

All 5 files verified present. All 3 commit hashes verified in git log.

---
*Phase: 09-datagolf-fetcher*
*Completed: 2026-03-25*
