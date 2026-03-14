---
phase: 04-constraint-foundation
verified: 2026-03-14T12:00:00Z
status: passed
score: 15/15 must-haves verified
re_verification: false
---

# Phase 4: Constraint Foundation Verification Report

**Phase Goal:** The optimizer correctly enforces lock and exclude constraints, detects conflicts and infeasibility before solving, and clears stale state when new CSVs are uploaded
**Verified:** 2026-03-14
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | A ConstraintSet with a locked card key causes check_conflicts and check_feasibility to run without error on a valid pool | VERIFIED | `test_card_lock_places_card` passes; check_conflicts returns None, check_feasibility returns None |
| 2  | check_conflicts returns a PreSolveError when a locked card key is also in excluded_cards | VERIFIED | `test_conflict_card_lock_exclude` passes; error message contains player name |
| 3  | check_conflicts returns a PreSolveError when a locked golfer name is also in excluded_players | VERIFIED | `test_conflict_golfer_lock_exclude` passes; error message contains player name |
| 4  | check_feasibility returns a PreSolveError with specific numbers when locked card salary sum exceeds salary_max | VERIFIED | `test_presolve_salary_exceeded` passes; message contains "70,000" and "64,000" |
| 5  | check_feasibility returns a PreSolveError with specific numbers when locked cards in a collection exceed collection_limits | VERIFIED | `test_presolve_collection_exceeded` passes; message contains "4", "Weekly Collection", "3" |
| 6  | check_feasibility returns None when locked cards are within all limits | VERIFIED | `test_card_lock_places_card`, `test_golfer_lock_satisfied` pass |
| 7  | ConstraintSet is JSON-round-trip safe: locked_cards stored as lists in session re-cast to tuples correctly | VERIFIED | routes.py line 43: `locked_cards=[tuple(k) for k in session.get("locked_cards", [])]` |
| 8  | optimize() accepts a ConstraintSet parameter and passes lock/exclude state into the solver | VERIFIED | optimize() signature has `constraints: ConstraintSet \| None = None`; pre-solve checks called before lineup loop |
| 9  | A locked card key appears in lineup 1 of the targeted contest | VERIFIED | `test_card_lock_forces_card_into_lineup` passes; Scheffler forced into lineup 1 |
| 10 | A locked golfer name satisfies the at-least-one-lineup requirement and does NOT cause infeasibility in lineup 2+ | VERIFIED | `test_golfer_lock_fires_once` passes; unsatisfied_golfer_locks discarded after first placement |
| 11 | An excluded card key never appears in any lineup across any contest | VERIFIED | `test_exclude_card_absent_from_all_lineups` passes; pre-filter removes key from available pool per iteration |
| 12 | An excluded player name means none of their cards appear in any lineup | VERIFIED | `test_exclude_golfer_absent_from_all_lineups` passes |
| 13 | A POST request with file uploads clears locked_cards, locked_golfers, excluded_cards, excluded_players from Flask session unconditionally | VERIFIED | `test_session_cleared_on_upload` passes; routes.py lines 35-38 pop all four keys |
| 14 | After session is cleared, the results page shows a visible "Locks and excludes reset for new upload" banner | VERIFIED | `test_reset_banner_shown` passes; index.html lines 57-61 render the banner when lock_reset=True |
| 15 | Flask app has SECRET_KEY configured so session cookies work | VERIFIED | `create_app()` sets `app.config["SECRET_KEY"]` from env var with dev fallback; confirmed via import check |

**Score:** 15/15 truths verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `gbgolf/optimizer/constraints.py` | ConstraintSet, PreSolveError, check_conflicts, check_feasibility, CardKey | VERIFIED | All five names in `__all__`; 172 lines, substantive implementation |
| `tests/test_constraints.py` | 12 unit tests covering LOCK-01 through EXCL-02 | VERIFIED | Exactly 12 tests collected and passing |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `gbgolf/optimizer/__init__.py` | optimize() with ConstraintSet param, composite key deduplication, pre-solve error path | VERIFIED | 151 lines; all three features present and working |
| `gbgolf/optimizer/engine.py` | _solve_one_lineup() with locked_card_keys and locked_golfer_names params | VERIFIED | Both params confirmed via inspect.signature; ILP constraints wired at lines 72-83 |
| `tests/test_optimizer.py` | Updated composite key tests + 6 new lock/exclude behavioral tests | VERIFIED | 16 tests passing; no id() calls remain |

### Plan 03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `gbgolf/web/__init__.py` | SECRET_KEY set in create_app() | VERIFIED | Line 25: os.environ.get fallback pattern |
| `gbgolf/web/routes.py` | Session read/write, clear on upload, ConstraintSet construction, lock_reset flag | VERIFIED | All four behaviors present; correct clear-then-build order |
| `gbgolf/web/templates/index.html` | Reset banner rendered when lock_reset=True | VERIFIED | Lines 57-61: Jinja2 conditional inside show_results block |
| `tests/test_web.py` | test_session_cleared_on_upload and test_reset_banner_shown integration tests | VERIFIED | Both tests present plus test_no_reset_banner_on_get; all 10 web tests pass |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tests/test_constraints.py` | `gbgolf/optimizer/constraints.py` | `from gbgolf.optimizer.constraints import ConstraintSet, PreSolveError, check_conflicts, check_feasibility` | WIRED | Direct import at line 12; all 12 tests pass against live module |
| `gbgolf/optimizer/constraints.py` | `gbgolf/data/config.py` | `ContestConfig` parameter in check_feasibility | WIRED | Line 23: `from gbgolf.data.config import ContestConfig`; used in function signature |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `gbgolf/optimizer/__init__.py` | `gbgolf/optimizer/engine.py` | `_solve_one_lineup(available, config, locked_card_keys, locked_golfer_names)` | WIRED | Line 115-120: call passes both lock params |
| `gbgolf/optimizer/__init__.py` | `gbgolf/optimizer/constraints.py` | `from gbgolf.optimizer.constraints import ConstraintSet, check_conflicts, check_feasibility` | WIRED | Line 4: direct import; all three names used in optimize() body |
| `gbgolf/optimizer/engine.py` | `pulp` | `prob += pulp.lpSum(...) >= 1` (golfer lock ILP constraint) | WIRED | Line 83: `prob += pulp.lpSum(x[i] for i in player_indices) >= 1` |

### Plan 03 Key Links

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `gbgolf/web/routes.py` | `gbgolf/optimizer/__init__.py` | `optimize(validation.valid_cards, current_app.config['CONTESTS'], constraints=constraints)` | WIRED | Line 65: constraints= kwarg present |
| `gbgolf/web/routes.py` | `flask.session` | `session.pop('locked_cards', None)` on upload; `session.get('locked_cards', [])` to build ConstraintSet | WIRED | Lines 35-38 (pop); lines 43-47 (get) |
| `gbgolf/web/templates/index.html` | `lock_reset` Jinja2 variable | `{% if lock_reset %}` banner block | WIRED | Line 57: conditional inside show_results block; banner text at line 58-60 |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Phase 4 Scope | Status | Evidence |
|-------------|------------|-------------|---------------|--------|----------|
| LOCK-01 | 04-01, 04-02 | User can lock a specific card to force it into the optimizer | Data structure (04-01) + ILP enforcement (04-02) | SATISFIED for Phase 4 scope | ConstraintSet.locked_cards stored; ILP `x[i] == 1` constraint wired; `test_card_lock_forces_card_into_lineup` passes |
| LOCK-02 | 04-01, 04-02 | User can lock a golfer by name to force at least one of their cards into a lineup | Data structure (04-01) + ILP enforcement (04-02) | SATISFIED for Phase 4 scope | ConstraintSet.locked_golfers stored; `lpSum >= 1` ILP constraint wired; fires-once tracking verified |
| LOCK-03 | 04-01 | App shows an informative error when locked cards make constraints infeasible | Complete in 04-01 | SATISFIED | check_feasibility returns PreSolveError with dollar amounts and collection counts; 3 tests pass |
| LOCK-04 | 04-01 | App warns user when a lock and exclude conflict on the same player or card | Complete in 04-01 | SATISFIED | check_conflicts detects card-level and golfer-level conflicts; 2 tests pass |
| EXCL-01 | 04-01, 04-02 | User can exclude a specific card from all lineups | Data structure (04-01) + ILP pre-filter (04-02) | SATISFIED for Phase 4 scope | ConstraintSet.excluded_cards stored; pre-filter in optimize() per iteration; `test_exclude_card_absent_from_all_lineups` passes |
| EXCL-02 | 04-01, 04-02 | User can exclude a golfer by name, removing all their cards | Data structure (04-01) + ILP pre-filter (04-02) | SATISFIED for Phase 4 scope | ConstraintSet.excluded_players stored; `c.player not in excluded_player_names` filter wired; test passes |
| UI-04 | 04-03 | Lock/exclude state resets automatically when new CSVs are uploaded | Complete in 04-03 | SATISFIED | session.pop() for all four keys before ConstraintSet build; test_session_cleared_on_upload passes |

**Note on "Partial" status in REQUIREMENTS.md for LOCK-01, LOCK-02, EXCL-01, EXCL-02:** The requirements document marks these as "Partial" because the UI layer (Phase 5/6) for users to *set* locks and excludes is not built yet. The Phase 4 scope commitment — data structures and engine enforcement — is fully satisfied. The "Partial" status is accurate and expected at this stage.

**Orphaned requirements check:** No requirements are mapped to Phase 4 in REQUIREMENTS.md that do not appear in the plan frontmatter. All seven Phase 4 requirements (LOCK-01 through LOCK-04, EXCL-01, EXCL-02, UI-04) are accounted for.

---

## Anti-Patterns Found

No anti-patterns detected across all six modified files:

- No TODO/FIXME/HACK/PLACEHOLDER comments
- No empty implementations (`return null`, `return {}`, `return []`)
- No stub handlers (handlers beyond `e.preventDefault()` only)
- No id() calls remaining in optimizer code (confirmed by grep)
- All functions have substantive bodies with real logic

---

## Test Suite Results

| Test File | Tests | Result |
|-----------|-------|--------|
| `tests/test_constraints.py` | 12 | 12 passed |
| `tests/test_optimizer.py` | 16 | 16 passed |
| `tests/test_web.py` | 10 | 10 passed |
| Full suite | 61 | 61 passed, 0 failures |

---

## Human Verification Required

None. All observable behaviors are verifiable programmatically through the test suite.

The reset banner appearance (UI-04) is covered by `test_reset_banner_shown` which checks `"Locks and excludes reset" in html`. No additional human UI verification is required for this phase since Phase 5 will build the actual lock/exclude UI controls.

---

## Summary

Phase 4 achieved its goal completely. All three plans executed successfully:

- **Plan 01** delivered the ConstraintSet/PreSolveError data contract with check_conflicts and check_feasibility pre-solve diagnostics, validated by 12 TDD unit tests.
- **Plan 02** wired the constraint engine into the ILP solver: composite key deduplication replaced id(), _solve_one_lineup() accepts lock params, optimize() orchestrates the full pre-solve → filter → lock-fires-once flow.
- **Plan 03** connected the web layer: SECRET_KEY configured, session cleared on upload before ConstraintSet construction, optimize() called with constraints kwarg, reset banner rendered in Jinja2.

The 61-test suite is fully green with no regressions. All seven Phase 4 requirements are satisfied within their declared scope.

---

_Verified: 2026-03-14T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
