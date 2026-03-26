---
phase: 09-datagolf-fetcher
verified: 2026-03-25T23:30:00Z
status: human_needed
score: 8/9 must-haves verified
human_verification:
  - test: "Run `flask fetch-projections` with a live DATAGOLF_API_KEY against the real DataGolf API"
    expected: "Command exits 0, stdout prints 'OK: <tournament> | <N> players | fetch_id=<id>', and logs/fetch.log gets a timestamped OK line"
    why_human: "The live end-to-end cron trigger path (FETCH-02) requires a real API key and real network call; the automated tests mock httpx.get so they cannot prove the deployed command actually reaches DataGolf and writes rows to the database"
  - test: "Run `flask fetch-projections` a second time immediately after the first"
    expected: "Player count in DB remains the same (no duplicate rows) and logs/fetch.log has exactly two OK lines for the same event"
    why_human: "Idempotency is tested with mocked data in pytest; confirming it holds end-to-end against live API data (different event_name values, real IDs) cannot be asserted programmatically"
---

# Phase 9: DataGolf Fetcher Verification Report

**Phase Goal:** The system automatically fetches projections from the DataGolf API and stores them safely in the database on a cron schedule
**Verified:** 2026-03-25T23:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `parse_datagolf_name` converts "Last, First" to "First Last" including suffix edge cases | VERIFIED | 4 unit tests pass: standard, suffix, no-comma, whitespace cases all correct |
| 2 | `write_projections` atomically replaces stale data for the same tournament via DELETE CASCADE + INSERT | VERIFIED | Lines 96-133 of fetcher.py implement exact pattern; `test_write_projections_replaces_stale` and `test_write_projections_idempotent` both pass |
| 3 | `run_fetch` calls DataGolf API, validates >= 30 players, normalizes names, writes to DB, and logs activity | VERIFIED | Lines 140-216 implement full pipeline; 5 run_fetch tests pass covering success and all error paths |
| 4 | If API returns error or < 30 players, existing DB projections are preserved unchanged | VERIFIED | Guard at line 193 (`if len(players) < 30`) halts before any DB write; `test_run_fetch_low_count_guard`, `test_run_fetch_api_error`, `test_run_fetch_network_error` all pass |
| 5 | Fetch activity is written to logs/fetch.log in the specified one-liner format | VERIFIED | `write_fetch_log` at lines 68-78 appends `"YYYY-MM-DD HH:MM:SS UTC | {line}\n"`; OK and ERROR log format tests pass |
| 6 | `flask fetch-projections` CLI command executes the DataGolf fetch pipeline end-to-end | VERIFIED | `@app.cli.command("fetch-projections")` registered in `gbgolf/web/__init__.py` lines 62-67; `test_cli_command_registered` confirms `--help` exits 0 with correct docstring |
| 7 | CLI command prints a human-readable summary to stdout | VERIFIED | `click.echo(result)` at line 67 of `__init__.py`; `test_cli_command_invokes_run_fetch` confirms output echoed |
| 8 | Cron line for Phase 11 deployment is documented with correct UTC offsets | VERIFIED | Lines 9 and 13 of fetcher.py docstring: `0 13 * * 2,3` (EST) and `0 12 * * 2,3` (EDT) with full crontab example |
| 9 | Running `flask fetch-projections` with a real API key writes rows and a log entry | HUMAN NEEDED | User approved this at the Plan 02 human-verify checkpoint; cannot be re-verified programmatically |

**Score:** 8/9 truths automated-verified (1 requires human confirmation)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `gbgolf/fetcher.py` | DataGolf fetch pipeline: Pydantic model, name parsing, DB writes, fetch orchestration, log writing | VERIFIED | 217 lines; exports `parse_datagolf_name`, `write_fetch_log`, `write_projections`, `run_fetch`; `_DataGolfPlayerProjection` Pydantic model present |
| `tests/test_fetcher.py` | >= 80 lines, >= 10 test functions covering FETCH-01/03/04/06 and idempotency | VERIFIED | 373 lines; 17 test functions (counted via `grep -c "def test_"`); all 17 pass |
| `scripts/datagolf_response_sample.json` | Raw API response for field name reference | VERIFIED | File exists; valid JSON dict with keys `event_name`, `last_updated`, `note`, `projections`, `site`, `slate`, `tour` |
| `gbgolf/web/__init__.py` | Flask CLI command registration for fetch-projections | VERIFIED | Contains `@app.cli.command("fetch-projections")`, `import click`, `click.echo(result)` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `gbgolf/fetcher.py` | `gbgolf/data/matching.py` | `from gbgolf.data.matching import normalize_name` | IMPORTED / NOT CALLED | Line 23: imported with `noqa: F401` comment "available for future use"; `parse_datagolf_name` handles format conversion without calling `normalize_name`. Import satisfies PLAN spec but function is unused in Phase 9. |
| `gbgolf/fetcher.py` | `gbgolf/db.py` | `from gbgolf.db import db` | VERIFIED | Line 24: `from gbgolf.db import db`; used at line 208: `write_projections(db.session, ...)` |
| `gbgolf/fetcher.py` | DataGolf API | `httpx.get` with `fantasy-projection-defaults` | VERIFIED | Lines 155-165: `httpx.get("https://feeds.datagolf.com/preds/fantasy-projection-defaults", ...)` with all required params |
| `tests/test_fetcher.py` | `gbgolf/fetcher.py` | `from gbgolf.fetcher import` | VERIFIED | Line 9: `from gbgolf.fetcher import parse_datagolf_name, write_fetch_log, write_projections, run_fetch` |
| `gbgolf/web/__init__.py` | `gbgolf/fetcher.py` | `from gbgolf.fetcher import run_fetch` | VERIFIED | Line 65 (lazy import inside CLI command): `from gbgolf.fetcher import run_fetch` |
| `flask fetch-projections` CLI | `gbgolf/fetcher.py::run_fetch()` | `@app.cli.command` decorator | VERIFIED | Lines 62-67 of `__init__.py`: `@app.cli.command("fetch-projections")` with `result = run_fetch()` |

**Note on `normalize_name`:** The PLAN key_links spec required `from gbgolf.data.matching import normalize_name` to be present — it is present. However, the function is not called within the Phase 9 fetch pipeline; `parse_datagolf_name` handles the "Last, First" -> "First Last" format conversion without Unicode normalization. The `noqa: F401` comment explicitly acknowledges this. This is a design choice (name matching will use `normalize_name` in Phase 10), not a broken link.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FETCH-01 | 09-01-PLAN, 09-02-PLAN | System fetches projections from DataGolf `fantasy-projection-defaults` API and writes to DB | SATISFIED | `run_fetch()` calls the exact API endpoint with correct params; 5 integration tests pass with mocked httpx |
| FETCH-02 | 09-02-PLAN | Cron job triggers fetcher on Tuesday and Wednesday mornings | PARTIALLY SATISFIED (human gate) | Flask CLI command `flask fetch-projections` exists and is callable; cron schedule `0 13 * * 2,3` documented in module docstring; actual VPS cron setup is Phase 11 — the CLI entry point satisfying Phase 9's scope of this requirement is complete |
| FETCH-03 | 09-01-PLAN | Fetch activity logged to a log file | SATISFIED | `write_fetch_log()` appends to `logs/fetch.log`; OK and ERROR format tests pass; directory auto-creation test passes |
| FETCH-04 | 09-01-PLAN | Existing projections preserved on API error or low player count | SATISFIED | 30-player guard at line 193 and error handling at lines 167-182 both preserve DB; 3 guard/error tests pass |
| FETCH-06 | 09-01-PLAN | DataGolf "Last, First" names normalized to "First Last" before storage | SATISFIED | `parse_datagolf_name()` correctly handles standard, suffix, no-comma, and whitespace cases; `test_run_fetch_normalizes_names` confirms "Scheffler, Scottie" stored as "Scottie Scheffler" in DB |
| FETCH-05 | Phase 8 (not Phase 9) | Projections stored with player name, projected score, tournament name, fetch timestamp | N/A — Phase 8 | Correctly owned by Phase 8; schema provides all four columns across `fetches` + `projections` tables |

**Orphaned requirements check:** REQUIREMENTS.md maps FETCH-01, FETCH-02, FETCH-03, FETCH-04, FETCH-05, FETCH-06 to Phase 8+9. FETCH-05 belongs to Phase 8 (confirmed in Phase 8 plan). All five Phase 9 requirement IDs (FETCH-01/02/03/04/06) are claimed and covered across the two plans. No orphaned requirements.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `gbgolf/fetcher.py` | 23 | `normalize_name` imported but not called (`noqa: F401`) | Info | Intentional — reserved for Phase 10 name matching; does not affect correctness |

No blocker or warning anti-patterns found. No TODO/FIXME/placeholder comments. No empty implementations. No stub returns.

---

### Human Verification Required

#### 1. Live End-to-End Fetch (FETCH-02 validation)

**Test:** With `DATAGOLF_API_KEY` set in `.env`, run `flask fetch-projections` from the project root
**Expected:** Command exits 0, stdout shows `OK: <tournament_name> | <N> players | fetch_id=<id>`, and `logs/fetch.log` contains a timestamped line with `OK | <tournament_name> | <N> players | fetch_id=<id>`
**Why human:** Automated tests monkeypatch `httpx.get` — they cannot prove the real DataGolf endpoint is reachable and returns valid data that flows through the full pipeline into the actual database

#### 2. Idempotency Under Live Conditions

**Test:** Run `flask fetch-projections` twice in succession against the live API
**Expected:** Row count in `fetches` table remains 1 for the current event; row count in `projections` remains the same N after the second run (no duplication); `logs/fetch.log` has two OK lines for the same event
**Why human:** The idempotency guarantee uses SQLite FK pragmas in tests; live PostgreSQL behavior with `RETURNING id` after `DELETE` should match, but confirming this requires an actual database connection

*Note: The 09-02-SUMMARY.md records that the user approved this at the Plan 02 human-verify checkpoint. This verification is confirming that the checkpoint was reached, not repeating it. If the user confirmed it at that time, this item is already cleared.*

---

### Commit Verification

All four commit hashes documented in SUMMARYs are confirmed present in git log:
- `a641266` — chore(09-01): add httpx dependency, gitignore logs, capture API response
- `a534ddb` — test(09-01): add failing tests for DataGolf fetcher module
- `bf8316a` — feat(09-01): implement DataGolf fetcher with full test suite
- `00d3e32` — feat(09-02): wire flask fetch-projections CLI command with tests and cron docs

---

### Full Test Suite

All **107 tests pass** (17 fetcher tests + 90 pre-existing tests from earlier phases). Zero regressions.

```
============================= 107 passed in 7.05s =============================
```

---

## Summary

Phase 9 goal is **achieved**. The DataGolf fetch pipeline is fully implemented: `gbgolf/fetcher.py` provides all four exported functions with correct logic; `gbgolf/web/__init__.py` exposes `flask fetch-projections` as the cron-callable entry point; all five requirement IDs (FETCH-01/02/03/04/06) are covered; 17 tests green with no regressions across the 107-test suite.

The only unresolved item is the live end-to-end verification gate (FETCH-02 deployment aspect), which requires human confirmation — or is already satisfied if the user-approved checkpoint in Plan 02 is counted.

---

_Verified: 2026-03-25T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
