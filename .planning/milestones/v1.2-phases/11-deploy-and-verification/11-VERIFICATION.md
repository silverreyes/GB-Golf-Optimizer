---
phase: 11-deploy-and-verification
verified: 2026-03-25T00:00:00Z
status: human_needed
score: 6/7 must-haves verified
human_verification:
  - test: "Production end-to-end: DataGolf source shows staleness label and produces lineups"
    expected: "https://gameblazers.silverreyes.net/golf — DataGolf radio selected, staleness label shows tournament name and relative age, clicking Optimize produces filled lineups"
    why_human: "Cannot SSH to production VPS or load browser from this environment"
  - test: "Production end-to-end: CSV upload source produces lineups after deploy"
    expected: "Upload CSV radio selected, file upload works, Optimize produces lineups"
    why_human: "Requires live browser interaction on the deployed VPS app"
  - test: "Cron entry registered on VPS"
    expected: "`crontab -l` on VPS deploy user shows the 0 13 * * 2,3 fetch-projections line"
    why_human: "Cannot inspect VPS crontab remotely"
---

# Phase 11: Deploy and Verification — Verification Report

**Phase Goal:** Deploy v1.2 to the production VPS with both projection sources (DataGolf API and CSV upload) verified working end-to-end. Fix the PostgreSQL PRAGMA bug that would crash fetcher.py on production. Update deploy.sh with migration step. Rewrite DEPLOY.md as the authoritative deployment guide with real values.
**Verified:** 2026-03-25
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PRAGMA foreign_keys is dialect-guarded, does not crash PostgreSQL | VERIFIED | `gbgolf/fetcher.py` line 94: `if session.get_bind().dialect.name == "sqlite":` — guard confirmed present |
| 2 | deploy.sh runs `flask db upgrade` between file sync and service restart | VERIFIED | Lines 11-29: tar sync (line 11), flask db upgrade (line 26), systemctl restart (line 29) — correct order confirmed |
| 3 | deploy.sh excludes .venv directory from tar sync | VERIFIED | Line 19: `--exclude='./.venv'` present alongside existing `--exclude='./venv'` |
| 4 | All existing tests still pass after PRAGMA fix | VERIFIED | `python -m pytest tests/ -q` exits 0 with `116 passed in 9.11s` |
| 5 | DEPLOY.md contains complete instructions with real values (no v1.0 placeholders) | VERIFIED | IP 193.46.198.60 appears 2x, no `<deploy_user>` or `/path/to/` strings, all 10 sections present |
| 6 | DEPLOY.md contains the exact crontab line and docker exec psql commands | VERIFIED | `0 13 * * 2,3` line present; 4 `docker exec` psql commands present |
| 7 | Both projection sources work in production (human-verified end-to-end) | HUMAN NEEDED | Per SUMMARY 11-02: human reported "OK — Texas Children's Houston Open — 134 players"; browser verification and cron cannot be confirmed programmatically |

**Score:** 6/7 truths verified (1 requires human confirmation)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `gbgolf/fetcher.py` | PostgreSQL-safe write_projections with dialect guard | VERIFIED | Line 94: `if session.get_bind().dialect.name == "sqlite":` — substantive, used by run_fetch() at line 209 |
| `deploy/deploy.sh` | Deployment script with migration step, .venv exclusion, https URL | VERIFIED | All three changes present; bash syntax valid (`bash -n` exits 0); 32 lines, fully substantive |
| `deploy/DEPLOY.md` | Authoritative v1.2 guide with real values | VERIFIED | 235 lines, 10 numbered sections, real IP/user/paths throughout, no placeholder strings remaining |
| `tests/test_fetcher.py` | Dialect-conditional PRAGMA test + clarifying comments | VERIFIED | 5 occurrences of "SQLite requires explicit FK enforcement"; `test_write_projections_skips_pragma_on_non_sqlite` test present and passing |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `gbgolf/fetcher.py` | `db.session` | dialect-conditional PRAGMA (`if session.get_bind().dialect.name == "sqlite":`) | VERIFIED | Guard on line 94, PRAGMA execution on line 95 only when sqlite; non-sqlite paths skip it |
| `deploy/deploy.sh` | VPS service | SSH commands in order: tar sync -> flask db upgrade -> systemctl restart | VERIFIED | Lines 11/23 (sync), 26 (migrate), 29 (restart) — strict sequential order, `set -e` ensures abort on failure |
| `deploy/DEPLOY.md` | VPS PostgreSQL Docker container | `docker exec -i CONTAINER_NAME psql` commands | VERIFIED | 4 `docker exec` occurrences covering user/DB creation, verification query, and DB row checks |
| `deploy/DEPLOY.md` | crontab | `0 13 * * 2,3` cron registration instructions | VERIFIED | Section 8 contains the exact cron line with `FLASK_APP=gbgolf.web:create_app .venv/bin/flask fetch-projections >> logs/fetch.log 2>&1` |

---

### Requirements Coverage

Phase 11 is a verification/deploy phase. The REQUIREMENTS.md Traceability table explicitly states: "Phase 11 (Deploy and Verification): verification phase — validates all requirements in production, owns no unique requirements."

Plan 11-01 claims FETCH-01 through FETCH-06; Plan 11-02 claims SRC-01 through SRC-05. These requirements were implemented in Phases 8, 9, and 10, and Phase 11 validates them in production. The traceability mapping is consistent.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FETCH-01 | 11-01 | Fetches from DataGolf API and writes to PostgreSQL | SATISFIED | `run_fetch()` in fetcher.py calls DataGolf API, `write_projections()` is PostgreSQL-safe after PRAGMA fix |
| FETCH-02 | 11-01 | Cron triggers fetcher Tue/Wed mornings | HUMAN NEEDED | Cron line documented in DEPLOY.md Section 8; production registration requires human confirmation |
| FETCH-03 | 11-01 | Fetch activity logged to file | SATISFIED | `write_fetch_log()` tested and passing; DEPLOY.md Section 9 covers log verification |
| FETCH-04 | 11-01 | Existing data preserved on API error / low count | SATISFIED | Tested via `test_run_fetch_low_count_guard` — 116 tests all pass |
| FETCH-05 | 11-01 | Projections stored with player name, score, tournament, timestamp | SATISFIED | `write_projections()` inserts all four fields; confirmed by test suite |
| FETCH-06 | 11-01 | DataGolf names normalized "Last, First" -> "First Last" | SATISFIED | `parse_datagolf_name()` tested; `test_run_fetch_normalizes_names` passes |
| SRC-01 | 11-02 | User can select DataGolf or Upload CSV | HUMAN NEEDED | Implemented in Phase 10; Phase 11 validates in production browser — requires human |
| SRC-02 | 11-02 | DataGolf source uses most recent DB projections | HUMAN NEEDED | Implemented in Phase 10; production verification requires human |
| SRC-03 | 11-02 | UI shows tournament name and relative fetch age | HUMAN NEEDED | Implemented in Phase 10; staleness label visible only in browser |
| SRC-04 | 11-02 | DataGolf disabled with message when no projections exist | HUMAN NEEDED | Implemented in Phase 10; requires browser interaction to confirm |
| SRC-05 | 11-02 | Unmatched player warnings for DataGolf source | HUMAN NEEDED | Implemented in Phase 10; requires browser interaction with real roster CSV |

**Note on SRC requirements:** These were implemented in Phase 10. Phase 11 Plan 02 is a deployment + human-verification checkpoint. The automated checks that can be done here (DEPLOY.md content, deploy.sh structure, PRAGMA fix) are all verified. The SRC requirements' production behavior is the human checkpoint.

**Orphaned requirements check:** No requirements in REQUIREMENTS.md are mapped to Phase 11 that are not covered by a plan. The traceability section confirms Phase 11 is a validation-only phase.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scanned: `gbgolf/fetcher.py`, `deploy/deploy.sh`, `deploy/DEPLOY.md`, `tests/test_fetcher.py`

No TODO/FIXME/placeholder comments, no empty implementations, no `return null`/`return {}` stubs, no console.log-only handlers found in any modified file.

The one notable deviation from the PLAN (using `session.get_bind().dialect.name` instead of `session.bind.dialect.name`) was an intentional bug fix documented in the SUMMARY and is the correct implementation for Flask-SQLAlchemy scoped sessions.

---

### Human Verification Required

#### 1. DataGolf source end-to-end in production

**Test:** Open `https://gameblazers.silverreyes.net/golf`, select the "DataGolf" radio button, upload a GameBlazers roster CSV, click Optimize.
**Expected:** Staleness label shows tournament name and relative age (e.g., "Texas Children's Houston Open — fetched X days ago"); optimizer lineups appear below.
**Why human:** Cannot access production browser or SSH from this environment.

#### 2. CSV upload source end-to-end in production

**Test:** On the same page, switch to "Upload CSV" source, upload a projections CSV, click Optimize.
**Expected:** Optimizer lineups appear; CSV upload path is unaffected by the DataGolf changes.
**Why human:** Requires browser interaction on the live app.

#### 3. Cron entry registered on VPS

**Test:** SSH to VPS as deploy user, run `crontab -l`.
**Expected:** Output includes the line `0 13 * * 2,3 cd /opt/GBGolfOptimizer && FLASK_APP=gbgolf.web:create_app .venv/bin/flask fetch-projections >> logs/fetch.log 2>&1`
**Why human:** VPS crontab is not readable from this environment.

---

### Automated Verification Summary

All automated checks pass:

- `gbgolf/fetcher.py` — dialect guard present and correct (`session.get_bind().dialect.name == "sqlite"`)
- `deploy/deploy.sh` — flask db upgrade on line 26, between tar sync (line 23) and systemctl restart (line 29); `.venv` excluded; `https://` URL used; bash syntax valid
- `deploy/DEPLOY.md` — 235 lines, 10 sections, real IP/user/path values, no v1.0 placeholders, all required content present
- `tests/test_fetcher.py` — dialect-conditional test present; 5 clarifying comments added to PRAGMA lines
- Git commits verified: b1c9948 (RED test), ca16b7d (GREEN fix), 5e45f91 (deploy.sh), 595360c (DEPLOY.md)
- Test suite: 116/116 passed

The three human verification items (production browser UX, CSV source in production, cron registration) cannot be confirmed programmatically. Per the SUMMARY, the human reported success on all three during the Task 2 checkpoint. This verification report documents them as requiring human confirmation to close formally.

---

_Verified: 2026-03-25_
_Verifier: Claude (gsd-verifier)_
