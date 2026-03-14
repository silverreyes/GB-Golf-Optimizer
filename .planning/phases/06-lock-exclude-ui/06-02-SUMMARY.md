---
phase: 06-lock-exclude-ui
plan: 02
subsystem: ui
tags: [flask, jinja2, html-forms, checkboxes, javascript, css]

# Dependency graph
requires:
  - phase: 06-01
    provides: 7 RED UI-01 tests defining player pool table and /reoptimize checkbox parsing behaviour
  - phase: 05-serialization-and-re-optimize-route
    provides: /reoptimize route, _serialize_cards/_deserialize_cards, card_pool hidden form field
provides:
  - Collapsible player pool <details> section inside #reoptimize-form with 8-column Lock/Exclude table
  - /reoptimize route parses lock_card, exclude_card, lock_golfer checkboxes via getlist() and writes session
  - index() POST passes card_pool sorted list and empty constraint sets to template on fresh upload
  - JS conflict prevention: checking Lock disables Exclude checkbox; checking Exclude disables Lock
  - .lock-golfer-empty CSS rule for column alignment
affects:
  - 06-03 (Plan 03 adds Lock column to lineup output tables — UI-03)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Jinja2 namespace pattern for per-player Lock Golfer checkbox deduplication
    - Pipe-delimited composite key encoding for checkbox values: "{player}|{salary}|{multiplier}|{collection}"
    - Form submission includes entire card pool as hidden field plus checkbox states as multi-value fields

key-files:
  created: []
  modified:
    - gbgolf/web/routes.py
    - gbgolf/web/templates/index.html
    - gbgolf/web/static/style.css

key-decisions:
  - "_parse_card_keys() defined inline in reoptimize() to keep helper co-located with its only caller"
  - "check_feasibility called once per contest config (CONTESTS list) before optimize() in reoptimize route"
  - "ConstraintSet built from parsed form values directly (not session re-read) to avoid stale-state bug"
  - "Standalone <input id='card-pool-data'> removed — card_pool hidden field lives inside form only"

patterns-established:
  - "Checkbox multi-value fields: request.form.getlist() for all lock_card, exclude_card, lock_golfer fields"
  - "Session writes use list-of-lists (JSON-safe): [list(k) for k in locked_cards]"
  - "ConstraintSet uses list-of-tuples directly from _parse_card_keys output"

requirements-completed:
  - UI-01

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 6 Plan 02: Lock/Exclude UI — Player Pool Table Summary

**Collapsible player pool table with per-card Lock/Exclude and per-player Lock Golfer checkboxes inside #reoptimize-form, with /reoptimize route parsing checkbox submissions and writing session constraints**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-14T18:27:16Z
- **Completed:** 2026-03-14T18:30:06Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Updated /reoptimize route to parse lock_card, exclude_card, lock_golfer form fields via getlist() and write session keys locked_cards, locked_golfers, excluded_cards
- Added collapsible <details id="player-pool-section"> inside #reoptimize-form with 8-column table (Lock, Lock Golfer, Exclude, Player, Collection, Salary, Multiplier, Proj Score)
- Lock Golfer checkbox rendered once per unique player using Jinja2 namespace tracking; 30 checkboxes for 30 players
- Pre-checked state reflected on re-render via locked_card_keys, locked_golfer_set, excluded_card_keys template vars
- Added JS conflict prevention and page-load initialization for pre-checked states
- All 7 UI-01 tests GREEN; 1 UI-03 test (test_locked_card_shows_lock_icon) correctly deferred to Plan 03

## Task Commits

Each task was committed atomically:

1. **Task 1: Update /reoptimize route to parse checkboxes and write session** - `f19c5e9` (feat)
2. **Task 2: Add player pool section to index.html and pass template vars from index() route** - `59e9d21` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `gbgolf/web/routes.py` - reoptimize() updated with checkbox parsing, session writes, pre-solve checks, new template kwargs; index() POST updated with card_pool sorted list and empty constraint sets
- `gbgolf/web/templates/index.html` - Added <details id="player-pool-section"> inside #reoptimize-form with 8-column checkbox table; JS conflict prevention added to script block; standalone #card-pool-data input removed
- `gbgolf/web/static/style.css` - Added .lock-golfer-empty rule

## Decisions Made
- `_parse_card_keys()` defined inline in `reoptimize()` — co-location with its only caller avoids polluting module scope
- `check_feasibility()` called once per contest config (iterating `CONTESTS` list) since the function signature requires a single `ContestConfig` — the plan's interface description had the call signature wrong (actual: `check_feasibility(constraints, valid_cards, config)`)
- `ConstraintSet` built from parsed values directly (not session re-read) as specified in the plan to avoid stale-state bug

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect check_feasibility call signature**
- **Found during:** Task 1 (update /reoptimize route)
- **Issue:** Plan's interface description showed `check_feasibility(valid_cards, constraints)` (2 args) but actual function signature is `check_feasibility(constraints, valid_cards, config)` (3 args, different order)
- **Fix:** Called `check_feasibility(constraints, valid_cards, contest_config)` in a loop over `current_app.config["CONTESTS"]`
- **Files modified:** gbgolf/web/routes.py
- **Verification:** `test_reoptimize_parses_lock_checkboxes` passes; no TypeError at runtime
- **Committed in:** f19c5e9 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in plan interface spec)
**Impact on plan:** Fix necessary for correctness. Route now correctly validates feasibility per contest before optimizing.

## Issues Encountered
None beyond the call signature mismatch noted above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 7 UI-01 tests GREEN; player pool table and checkbox parsing fully implemented
- Plan 03 can now add the Lock column (with lock icon) to the lineup output tables to make the 3 UI-03 tests GREEN
- test_locked_card_shows_lock_icon remains the sole failing test — correctly RED until Plan 03

---
*Phase: 06-lock-exclude-ui*
*Completed: 2026-03-14*
