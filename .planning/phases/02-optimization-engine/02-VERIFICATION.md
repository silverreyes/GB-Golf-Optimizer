---
phase: 02-optimization-engine
verified: 2026-03-13T00:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
gaps: []
---

# Phase 2: Optimization Engine Verification Report

**Phase Goal:** Given validated cards and contest config, the optimizer produces correct optimal lineups for both contests with all constraints satisfied
**Verified:** 2026-03-13
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

Phase success criteria from ROADMAP.md (authoritative contract):

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Optimizer generates 3 Tips lineups (6 golfers each) maximizing effective value within salary floor/cap and collection limits | VERIFIED | `test_tips_lineup_count` PASS; `test_tips_salary_constraints` PASS; `test_tips_collection_limits` PASS — confirmed live: 3 Tips lineups with 18 cards used |
| 2 | Optimizer generates 2 Intermediate Tee lineups (5 golfers each) using only cards not assigned to any Tips lineup | VERIFIED | `test_intermediate_lineup_count` PASS — confirmed live: 10 cards used across 2 Intermediate lineups, 0 overlap with Tips cards |
| 3 | No card appears in more than one lineup across all contests | VERIFIED | `test_no_card_reuse_across_contests` PASS; `test_card_uniqueness_all_lineups` PASS — cross-contest id() disjointness confirmed |
| 4 | Optimizer returns a clear infeasibility message (not a crash) when constraints cannot be satisfied | VERIFIED | `test_salary_floor_enforced` PASS; `test_infeasibility_notice` PASS; `test_partial_results` PASS — returns OptimizationResult with notices list, never raises |

**Score:** 4/4 success criteria verified

### Plan-Level Must-Have Truths (all 3 plans)

#### Plan 02-01 Must-Haves

| Truth | Status | Evidence |
|-------|--------|----------|
| pytest collects tests/test_optimizer.py with 0 errors | VERIFIED | 10 tests collected and pass |
| PuLP is importable after install | VERIFIED | `pulp.__version__ == '3.3.0'` confirmed |
| gbgolf.optimizer public API is importable with correct names | VERIFIED | `from gbgolf.optimizer import optimize, OptimizationResult, Lineup` — OK |

#### Plan 02-02 Must-Haves

| Truth | Status | Evidence |
|-------|--------|----------|
| _solve_one_lineup selects exactly roster_size cards | VERIFIED | ILP equality constraint `sum(x) == config.roster_size` present and tested |
| Lineup satisfies salary_min <= total_salary <= salary_max | VERIFIED | Both salary constraints in engine.py; `test_tips_salary_constraints` PASS |
| Lineup respects collection_limits (upper bounds only) | VERIFIED | Collection limits loop in engine.py uses `<=`; `test_tips_collection_limits` PASS |
| No player appears more than once in a single lineup | VERIFIED | Same-player constraint in engine.py; `test_same_player_once_per_lineup` PASS |
| _solve_one_lineup returns None (not raises) when infeasible | VERIFIED | `pulp.LpStatus != "Optimal"` path returns None; `test_infeasibility_notice` PASS |
| Objective is maximized | VERIFIED | `LpMaximize` with `lpSum(effective_value * x[i])` objective in engine.py |

#### Plan 02-03 Must-Haves

| Truth | Status | Evidence |
|-------|--------|----------|
| optimize() returns 3 Tips lineups each with 6 cards | VERIFIED | Live run: 18 Tips cards used across 3 lineups |
| optimize() returns 2 Intermediate Tee lineups from remaining pool | VERIFIED | Live run: 10 Intermediate cards used, disjoint from Tips |
| No card (by object identity) appears in more than one lineup | VERIFIED | id()-based pool mutation in __init__.py; live total confirms 35 = 18+10+7 |
| optimize() returns partial results plus infeasibility notices | VERIFIED | `test_partial_results` PASS: 12 cards → 2 lineups + 1 notice |
| optimize() never raises | VERIFIED | No raise paths in optimize(); all infeasibility handled as notices |
| unused_cards contains exactly the cards not assigned | VERIFIED | Live: 35 input − 28 used = 7 unused confirmed |

---

### Required Artifacts

| Artifact | Expected | Exists | Substantive | Wired | Status |
|----------|----------|--------|-------------|-------|--------|
| `gbgolf/optimizer/__init__.py` | Public API: optimize, OptimizationResult, Lineup | Yes | 81 lines, full implementation | Imported by tests via `from gbgolf.optimizer import` | VERIFIED |
| `gbgolf/optimizer/engine.py` | ILP engine: _solve_one_lineup with PuLP CBC | Yes | 65 lines, full ILP formulation | Imported in `__init__.py` via `from gbgolf.optimizer.engine import _solve_one_lineup` | VERIFIED |
| `tests/test_optimizer.py` | 10 tests covering all OPT requirements | Yes | 228 lines, 10 test functions, module-level fixtures | Collected and executed by pytest | VERIFIED |
| `pyproject.toml` | `pulp>=3.3.0` in dependencies | Yes | Contains `"pulp>=3.3.0"` | pip-installed, importable at version 3.3.0 | VERIFIED |

---

### Key Link Verification

| From | To | Via | Status | Detail |
|------|----|-----|--------|--------|
| `tests/test_optimizer.py` | `gbgolf.optimizer` | `from gbgolf.optimizer import optimize, OptimizationResult, Lineup` | WIRED | Line 10 of test file; all 10 tests exercise the API |
| `gbgolf/optimizer/__init__.py` | `gbgolf/optimizer/engine._solve_one_lineup` | `from gbgolf.optimizer.engine import _solve_one_lineup` | WIRED | Line 3 of __init__.py; called in optimize() loop |
| `gbgolf/optimizer/engine.py` | `pulp.LpProblem` | ILP formulation with binary variables per card | WIRED | `pulp.LpProblem("lineup", pulp.LpMaximize)` at line 25 |
| `gbgolf/optimizer/engine.py` | `pulp.PULP_CBC_CMD` | `prob.solve(pulp.PULP_CBC_CMD(msg=0))` | WIRED | Line 57 of engine.py; msg=0 suppresses solver output |
| `gbgolf/optimizer/__init__.py` | `OptimizationResult` return | `return OptimizationResult(lineups=..., unused_cards=..., infeasibility_notices=...)` | WIRED | Lines 73-77 of __init__.py |

---

### Requirements Coverage

All Phase 2 requirements declared in plan frontmatter (`requirements: [OPT-01, OPT-02, OPT-03, OPT-04, OPT-06]`):

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| OPT-01 | 02-01, 02-02, 02-03 | Optimizer generates 3 optimal Tips lineups (6 golfers, $30k–$64k, max 3 Weekly/6 Core) | SATISFIED | `test_tips_lineup_count` PASS; `test_tips_salary_constraints` PASS; `test_tips_collection_limits` PASS |
| OPT-02 | 02-01, 02-03 | Optimizer generates 2 optimal Intermediate Tee lineups (5 golfers, $20k–$52k, max 2 Weekly/5 Core) | SATISFIED | `test_intermediate_lineup_count` PASS; live run confirms 2 lineups with 5-card roster |
| OPT-03 | 02-01, 02-03 | Tips fully optimized first; Intermediate Tee uses remaining cards only | SATISFIED | Sequential contest iteration in optimize(); Tips solved first per contest order; `test_no_card_reuse_across_contests` PASS |
| OPT-04 | 02-01, 02-02, 02-03 | Each card in at most one lineup across all contests | SATISFIED | id()-based pool mutation; `test_card_uniqueness_all_lineups` PASS; live 35=18+10+7 confirms accounting |
| OPT-06 | 02-01, 02-02, 02-03 | Optimizer respects both salary floor and cap per contest | SATISFIED | Both `>= salary_min` and `<= salary_max` constraints in engine.py; `test_tips_salary_constraints` PASS; `test_salary_floor_enforced` PASS |

**REQUIREMENTS.md cross-reference:** OPT-05 and OPT-07 are assigned to Phase 1 — correct, not claimed by Phase 2 plans. No orphaned requirements for this phase.

**Coverage:** 5/5 Phase 2 requirements SATISFIED.

---

### Anti-Patterns Found

No anti-patterns detected in optimizer files.

Scanned: `gbgolf/optimizer/__init__.py`, `gbgolf/optimizer/engine.py`, `tests/test_optimizer.py`

Patterns checked: TODO/FIXME/HACK, NotImplementedError, placeholder returns, empty implementations, console.log.

Result: Clean — no blockers, no warnings.

---

### Notable Observations (Non-Blocking)

**Infeasibility notice format deviation:** The plan spec (02-03 behavior block) specified the format `"Could not build lineup N for {contest.name}"`. The actual implementation uses `"{contest.name}: lineup {n} of {max} could not be built (infeasible)"`. The tests only verify that notices are strings and that the count is correct — all tests pass. The format is more informative than specified. No functional impact.

**Lineup computed fields:** `total_salary`, `total_projected_score`, `total_effective_value` are computed in `__post_init__` but not declared as dataclass fields with `field(init=False)` as specified in the plan. They are set as instance attributes directly. This works correctly in Python but is a minor deviation from the plan's dataclass pattern. No functional impact.

---

### Human Verification Required

None. All phase goal outcomes are verifiable programmatically via the test suite. The test suite is comprehensive (10 tests covering all constraint types), and live execution confirms correct behavior.

---

## Test Suite Results

```
Platform: win32, Python 3.11.9, pytest-9.0.2
Collected: 33 tests

tests/test_config.py        ...   (3)
tests/test_filters.py       .....  (5)
tests/test_matching.py      .....  (5)
tests/test_optimizer.py     .......... (10)
tests/test_pipeline.py      ....   (4)
tests/test_projections.py   ...   (3)
tests/test_roster.py        ...   (3)

33 passed in 1.19s
```

Phase 1 tests (23) remain GREEN. Phase 2 optimizer tests (10) all GREEN. No regressions.

---

## Gaps Summary

No gaps. All must-haves verified. Phase goal achieved.

---

_Verified: 2026-03-13_
_Verifier: Claude (gsd-verifier)_
