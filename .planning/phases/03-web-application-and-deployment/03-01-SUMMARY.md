---
phase: 03-web-application-and-deployment
plan: 01
subsystem: ui
tags: [flask, gunicorn, jinja2, werkzeug, multipart-upload, tempfile]

# Dependency graph
requires:
  - phase: 01-data-foundation
    provides: validate_pipeline(), load_config(), ValidationResult, Card, ExclusionRecord
  - phase: 02-optimization-engine
    provides: optimize(), OptimizationResult, Lineup

provides:
  - Flask web app factory (create_app) with ProxyFix, config loading, blueprint
  - POST /  route handling CSV uploads via temp files, calling validate_pipeline + optimize
  - Single-page Jinja2 template with upload form (collapses after results), loading overlay, exclusion report, lineup tables by contest with tfoot totals, infeasibility notices
  - Minimal CSS for all UI components
  - wsgi.py Gunicorn entry point

affects: [03-02-deployment]

# Tech tracking
tech-stack:
  added: [flask==3.1.3, gunicorn==25.1.0, werkzeug (ProxyFix), jinja2]
  patterns:
    - App factory pattern (create_app) with TESTING flag to skip ProxyFix
    - Temp file upload pattern — write to NamedTemporaryFile, close, then pass path to pipeline (Windows-safe)
    - Blueprint registration in factory
    - Contest order controlled via Jinja2 contest_order list (not dict iteration order)

key-files:
  created:
    - gbgolf/web/__init__.py
    - gbgolf/web/routes.py
    - gbgolf/web/templates/index.html
    - gbgolf/web/static/style.css
    - wsgi.py
    - tests/test_web.py
  modified:
    - pyproject.toml

key-decisions:
  - "ProxyFix skipped in TESTING mode to avoid test client URL generation conflicts"
  - "Temp files written with mode=wb and file.save() inside with-block, path used outside — Windows-safe file unlock pattern"
  - "contest_order hardcoded as Jinja2 list to guarantee The Tips before The Intermediate Tee regardless of dict iteration"
  - "Flask app factory stores CONTESTS list at startup (not per-request) to avoid repeated config parsing"
  - "Test CSV data uses 30 valid players to satisfy disjoint pool requirements for all 5 lineups (3 Tips + 2 Intermediate Tee)"

patterns-established:
  - "Upload-then-optimize: write uploads to temp files, validate, optimize, render — all in one POST handler"
  - "Error surfacing: ValueError from pipeline caught and rendered as user-facing error message"

requirements-completed: [DISP-01, DISP-02]

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 3 Plan 01: Flask Web Layer Summary

**Flask single-page browser UI wrapping the complete optimization pipeline: CSV upload, lineup generation, and tabular results with contest sections, exclusion report, and infeasibility notices**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-14T01:59:51Z
- **Completed:** 2026-03-14T02:03:24Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Flask app factory with ProxyFix, config loading, and blueprint registration
- POST / route with Windows-safe temp file upload handling calling validate_pipeline and optimize
- Jinja2 template rendering upload form (collapses to "Change files" toggle after results), full-page loading overlay, exclusion report (only when exclusions exist), lineup tables with thead/tfoot, and infeasibility notices in contest-order
- All 7 integration tests pass, full suite (40 tests) green with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing test stubs for web layer** - `b2fef46` (test)
2. **Task 2: Implement Flask web app (make tests GREEN)** - `81122d5` (feat)

**Plan metadata:** _(final docs commit — see below)_

## Files Created/Modified

- `tests/test_web.py` - 7 integration tests covering DISP-01 and DISP-02, with sample CSV data for 30 valid players
- `gbgolf/web/__init__.py` - create_app() factory: ProxyFix, MAX_CONTENT_LENGTH, CONFIG_PATH, CONTESTS, blueprint registration
- `gbgolf/web/routes.py` - Blueprint with GET/POST index route; temp file upload, validate_pipeline + optimize calls
- `gbgolf/web/templates/index.html` - Single-page Jinja2 template: collapsible upload form, loading overlay, exclusion report, contest-ordered lineup tables with tfoot totals
- `gbgolf/web/static/style.css` - Minimal CSS for all UI components including loading overlay and exclusion report
- `wsgi.py` - Gunicorn entry point: from gbgolf.web import create_app; app = create_app()
- `pyproject.toml` - Added flask>=3.0 and gunicorn>=20.0 to dependencies and dev extras

## Decisions Made

- **ProxyFix skipped in TESTING mode:** Flask test client URL generation conflicts with ProxyFix; the TESTING flag bypasses it
- **Windows-safe temp file pattern:** Upload written with `file.save(rf)` inside `with NamedTemporaryFile(delete=False, mode="wb")`, path captured, used outside the with-block after file is closed and unlocked
- **contest_order as Jinja2 list:** `{% set contest_order = ["The Tips", "The Intermediate Tee"] %}` guarantees display order regardless of Python dict iteration
- **CONTESTS loaded at startup:** App factory calls load_config() once and stores result in app.config["CONTESTS"] rather than reloading on every request
- **30-player test fixture:** Enough disjoint cards for all 5 lineups (3 × 6-card Tips + 2 × 5-card Intermediate Tee = 28 card slots)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- pip command failed with exit code 1 when invoked as bare `pip install`; resolved by using `python -m pip install flask gunicorn` with the correct Python 3.11 interpreter on PATH.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Flask web app is fully functional locally; all tests pass
- wsgi.py entry point ready for Gunicorn: `gunicorn wsgi:app`
- Next: 03-02 deployment — systemd service + Nginx reverse proxy on Hostinger KVM 2 VPS at gameblazers.silverreyes.net/golf

---
*Phase: 03-web-application-and-deployment*
*Completed: 2026-03-14*
