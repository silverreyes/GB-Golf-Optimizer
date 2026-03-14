---
phase: 07-polish
plan: 01
subsystem: ui
tags: [flask, jinja2, javascript, pytest, html]

# Dependency graph
requires:
  - phase: 06-lock-exclude-ui
    provides: Clear All button (id="clear-all-btn") already in template, lock/exclude checkbox infrastructure
provides:
  - Constraint count display element (id="constraint-count") inside show_results block
  - updateConstraintCount() JS function wired into all checkbox listeners and clearAllCheckboxes()
  - 5 new HTML-presence tests for UI-05 (Clear All) and UI-06 (constraint count) plus Wave 0 sort headers scaffold
affects: [07-02-PLAN.md (sort headers RED scaffold set up here)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 RED scaffold: add failing tests first, implement in subsequent task, confirm RED before implementation"
    - "Null-guard pattern for conditional DOM elements: if (!el) return; handles absent element gracefully"
    - "Constraint count wired into all 3 checkbox change listeners + clearAllCheckboxes() + page-load init"

key-files:
  created: []
  modified:
    - tests/test_web.py
    - gbgolf/web/templates/index.html

key-decisions:
  - "updateConstraintCount() defined before clearAllCheckboxes() so clearAllCheckboxes() can call it without hoisting issues"
  - ".lock-golfer-cb change listener added (was missing) — counts toward locks via combined selector .lock-cb:checked, .lock-golfer-cb:checked"
  - "test_sort_headers_rendered intentionally RED — Plan 02 Wave 0 scaffold, will turn GREEN in 07-02"
  - "constraint-count element inside {% if show_results and card_pool_json %} block — absent on GET, present on POST results"

patterns-established:
  - "Constraint display: hidden when 0 active constraints, shows 'Locks: N | Excludes: N' format otherwise"

requirements-completed: [UI-05, UI-06]

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 07 Plan 01: UI-05/UI-06 Constraint Count Display and Clear All Tests Summary

**Constraint count div (`id="constraint-count"`) added above Re-Optimize button with `updateConstraintCount()` JS wired into all checkbox listeners; 5 new server-side HTML-presence tests (4 GREEN, 1 intentional RED scaffold for Plan 02)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-14T20:14:29Z
- **Completed:** 2026-03-14T20:16:25Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- 5 new tests appended to test_web.py: 4 GREEN (UI-05/UI-06 presence tests), 1 intentional RED scaffold for Plan 02 sort headers
- `<div id="constraint-count">` added inside show_results block (absent on GET, present on POST with results)
- `updateConstraintCount()` JS function defined with null-guard and "Locks: N | Excludes: N" format
- Added missing `.lock-golfer-cb` change listener (was absent from original template)
- Wired `updateConstraintCount()` into `.lock-cb`, `.lock-golfer-cb`, `.exclude-cb` listeners, `clearAllCheckboxes()`, and page-load init

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 5 failing tests (Wave 0 RED scaffold)** - `ccc0f89` (test)
2. **Task 2: Add constraint count element and JS to index.html** - `ec1b971` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `tests/test_web.py` - 5 new Phase 07 test functions appended after last Phase 06 test
- `gbgolf/web/templates/index.html` - constraint-count div + updateConstraintCount() + .lock-golfer-cb listener + calls to updateConstraintCount() in all listeners and page load

## Decisions Made
- `updateConstraintCount()` placed before `clearAllCheckboxes()` in script block (clearAllCheckboxes calls it)
- `.lock-golfer-cb` change listener added inline — was missing from original Phase 6 template
- `test_sort_headers_rendered` intentionally RED: serves as Wave 0 scaffold for Plan 02, which adds onclick sortTable() handlers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 can proceed: `test_sort_headers_rendered` RED scaffold is in place
- Manual browser verification checklist from plan (constraint count behavior) is ready to test
- All prior 27 tests remain GREEN; total suite is 31 passed + 1 intentional RED

---
*Phase: 07-polish*
*Completed: 2026-03-14*
