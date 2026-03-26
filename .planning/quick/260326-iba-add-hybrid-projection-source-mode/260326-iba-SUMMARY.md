---
phase: quick
plan: 260326-iba
subsystem: data-layer, web-ui
tags: [projections, hybrid, merge, csv, database]
dependency_graph:
  requires: [validate_pipeline, validate_pipeline_auto, load_projections_from_db, parse_projections_csv]
  provides: [validate_pipeline_hybrid]
  affects: [gbgolf.web.routes, index.html]
tech_stack:
  patterns: [CSV-priority merge with DB fallback, TDD red-green]
key_files:
  created: []
  modified:
    - gbgolf/data/__init__.py
    - gbgolf/web/routes.py
    - gbgolf/web/templates/index.html
    - tests/test_web.py
decisions:
  - "Hybrid radio disabled when DB has no projections (same guard as Auto)"
  - "CSV overwrites DB on name conflict via dict merge order: {**db, **csv}"
  - "Empty DB in hybrid mode gracefully falls back to CSV-only (catches ValueError)"
metrics:
  duration: 4min
  completed: "2026-03-26T19:18:00Z"
---

# Quick Task 260326-iba: Add Hybrid Projection Source Mode Summary

Hybrid projection source merging CSV uploads (priority) with DataGolf DB projections (fallback) via dict merge `{**db, **csv}`, with third radio button in UI and full test coverage.

## What Was Built

### validate_pipeline_hybrid() function
New pipeline function in `gbgolf/data/__init__.py` that:
1. Parses CSV projections from uploaded file
2. Loads DB projections (catches ValueError for empty DB, uses empty dict)
3. Merges with `{**db_projections, **csv_projections}` giving CSV priority
4. Runs standard match_projections, apply_filters, pool-size guard
5. Returns ValidationResult with merged projections

### Route branching
Updated `gbgolf/web/routes.py` POST handler to branch on `projection_source == "hybrid"`:
- Validates projections file is present (same as CSV path)
- Saves file to temp, calls validate_pipeline_hybrid()
- Updated projections file requirement check to `in ("csv", "hybrid")`

### UI: Hybrid radio button
Added third radio button in `index.html` between Auto and Upload CSV:
- Disabled when `db_has_projections` is false (no DB to fill gaps from)
- JS toggle shows BOTH upload zone AND staleness label when hybrid selected
- Auto shows only staleness, CSV shows only upload zone, Hybrid shows both

### Tests
8 new tests added to `tests/test_web.py`:
- `test_hybrid_fills_gaps_from_db` - CSV 10 players + DB 30 = full lineup
- `test_hybrid_csv_takes_priority` - CSV 99.0 overrides DB 72.5
- `test_hybrid_db_empty_still_works` - empty DB graceful fallback
- `test_hybrid_no_projections_file_error` - missing file returns error
- `test_hybrid_unmatched_from_both_sources` - exclusion report accuracy
- `test_hybrid_radio_rendered` - radio button present in HTML
- `test_hybrid_radio_disabled_no_db` - disabled attribute when no DB
- `test_hybrid_radio_enabled_with_db` - enabled when DB has data

## Task Completion

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 (RED) | Failing hybrid tests | 7249c69 | tests/test_web.py |
| 1 (GREEN) | validate_pipeline_hybrid + route | f6289c7 | gbgolf/data/__init__.py, gbgolf/web/routes.py |
| 2 | Hybrid radio button + JS toggle | ec3955b | gbgolf/web/templates/index.html, tests/test_web.py |

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- All 48 tests pass (40 existing + 8 new hybrid)
- Zero regression on csv and auto paths
- TDD red-green cycle confirmed: test_hybrid_csv_takes_priority failed in RED, passed in GREEN

## Self-Check: PASSED

All 5 files found. All 3 commits verified (7249c69, f6289c7, ec3955b).
