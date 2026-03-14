---
phase: 07-polish
plan: 02
subsystem: ui
tags: [javascript, sorting, html, jinja2, vanilla-js]

# Dependency graph
requires:
  - phase: 07-01
    provides: constraint count div, updateConstraintCount() JS, clearAllCheckboxes() JS, .lock-golfer-cb listeners, test_sort_headers_rendered RED scaffold
provides:
  - Sortable player pool table with onclick headers, data-sort td attributes, sortTable() and updateSortIndicators() JS functions
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "data-sort attribute on each td cell enables robust numeric/text sort without DOM text parsing"
    - "th.textContent setter is safe for indicator updates because onclick is an HTML attribute, not a JS property"
    - "tbody.appendChild() reorders existing rows without cloning — form values (name/value/checked) preserved through sort"

key-files:
  created: []
  modified:
    - gbgolf/web/templates/index.html
    - tests/test_web.py

key-decisions:
  - "th.textContent used for sort indicator updates — safe because onclick attribute is unaffected by textContent setter"
  - "data-sort uses raw values (no $ prefix for salary, 0/1 for checkboxes) enabling parseFloat numeric sort"
  - "First click on any column = descending; second click = ascending — consistent with common table sort UX"
  - "updateSortIndicators(3, true) called on page load to show initial Player column indicator matching server sort order"

patterns-established:
  - "Sort indicator pattern: strip existing [▲▼] with regex then append new indicator — idempotent on multiple clicks"
  - "sortTable() guard: if (!tbody) return — safe when player pool not in DOM (GET with no results)"

requirements-completed: [UI-05, UI-06]

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 7 Plan 02: Sortable Player Pool Table Summary

**Vanilla JS table sort with data-sort td attributes, onclick th headers, and ▲/▼ indicators — turns test_sort_headers_rendered GREEN and completes Phase 7 (v1.1 milestone)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T20:18:49Z
- **Completed:** 2026-03-14T20:20:40Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- All 8 player pool column headers have `onclick="sortTable(N)"` handlers
- All td cells in player pool tbody have `data-sort` attributes with raw values for numeric/text sort
- `sortTable()` and `updateSortIndicators()` vanilla JS functions added to script block
- `updateSortIndicators(3, true)` called on page load to show initial Player ▲ indicator
- test_sort_headers_rendered turned GREEN; full 83-test suite GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Add data-sort attributes and onclick sortTable() to player pool table** - `a755618` (feat)
2. **Task 2: Add sortTable() and updateSortIndicators() JS functions** - `4ec6cba` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `gbgolf/web/templates/index.html` - Updated thead with onclick handlers; updated tbody td elements with data-sort attributes; added sortTable(), updateSortIndicators() JS; added updateSortIndicators(3, true) page-load call
- `tests/test_web.py` - Updated test_player_pool_table_columns assertions to use `>Header</th>` pattern (compatible with onclick-enhanced headers)

## Decisions Made
- `th.textContent` setter used for sort indicator updates — safe because onclick is an HTML attribute, not a JS child node property; textContent replaces text nodes only
- data-sort uses raw values: no `$` prefix on salary (enables parseFloat), 0/1 integers for checkbox columns
- First click = descending sort (highest/checked-first), second click = ascending — standard table UX convention
- `updateSortIndicators(3, true)` at page load shows Player ▲ matching the server's default A-Z sort order

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_player_pool_table_columns to match onclick-enhanced th elements**
- **Found during:** Task 1 (adding onclick attributes to th headers)
- **Issue:** Existing test asserted `<th>Lock</th>` (exact string) but rendered HTML now has `<th onclick="sortTable(0)">Lock</th>` — assertion failed after valid template change
- **Fix:** Updated 8 assertions to use `>Lock</th>` pattern (matches header text content regardless of attributes)
- **Files modified:** tests/test_web.py
- **Verification:** All 32 test_web.py tests GREEN after fix
- **Committed in:** a755618 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug: fragile test assertion)
**Impact on plan:** Fix necessary for correctness — test was checking column presence, not onclick absence. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 7 complete — all requirements UI-01 through UI-06 implemented and tested
- v1.1 milestone complete: sortable player pool table, constraint count display, lock/exclude UI, re-optimize route
- Full 83-test suite GREEN
- No blockers for future phases

---
*Phase: 07-polish*
*Completed: 2026-03-14*
