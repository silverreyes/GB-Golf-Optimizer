---
phase: 4
slug: constraint-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_constraints.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_constraints.py -x -q`
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | LOCK-01 | unit | `pytest tests/test_constraints.py::test_card_lock_places_card -x` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 0 | LOCK-01 | unit | `pytest tests/test_constraints.py::test_card_lock_missing_card -x` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 0 | LOCK-02 | unit | `pytest tests/test_constraints.py::test_golfer_lock_satisfied -x` | ❌ W0 | ⬜ pending |
| 4-01-04 | 01 | 0 | LOCK-02 | unit | `pytest tests/test_constraints.py::test_golfer_lock_fires_once -x` | ❌ W0 | ⬜ pending |
| 4-01-05 | 01 | 0 | LOCK-03 | unit | `pytest tests/test_constraints.py::test_presolve_salary_exceeded -x` | ❌ W0 | ⬜ pending |
| 4-01-06 | 01 | 0 | LOCK-03 | unit | `pytest tests/test_constraints.py::test_presolve_collection_exceeded -x` | ❌ W0 | ⬜ pending |
| 4-01-07 | 01 | 0 | LOCK-03 | unit | `pytest tests/test_constraints.py::test_presolve_message_content -x` | ❌ W0 | ⬜ pending |
| 4-01-08 | 01 | 0 | LOCK-04 | unit | `pytest tests/test_constraints.py::test_conflict_card_lock_exclude -x` | ❌ W0 | ⬜ pending |
| 4-01-09 | 01 | 0 | LOCK-04 | unit | `pytest tests/test_constraints.py::test_conflict_golfer_lock_exclude -x` | ❌ W0 | ⬜ pending |
| 4-01-10 | 01 | 0 | EXCL-01 | unit | `pytest tests/test_constraints.py::test_card_exclude_removes_card -x` | ❌ W0 | ⬜ pending |
| 4-01-11 | 01 | 0 | EXCL-02 | unit | `pytest tests/test_constraints.py::test_golfer_exclude_removes_all_cards -x` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | UI-04 | integration | `pytest tests/test_web.py::test_session_cleared_on_upload -x` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | UI-04 | integration | `pytest tests/test_web.py::test_reset_banner_shown -x` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 2 | — | unit | `pytest tests/test_optimizer.py -x -q` (updated) | ✅ needs update | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_constraints.py` — stubs for LOCK-01 through EXCL-02 (all new constraint unit tests)
- [ ] `gbgolf/optimizer/constraints.py` — ConstraintSet, PreSolveError, check_conflicts, check_feasibility (stub module)
- [ ] `tests/test_web.py` — add `test_session_cleared_on_upload` and `test_reset_banner_shown`
- [ ] Update `tests/test_optimizer.py` — update `test_no_card_reuse_across_contests` and `test_card_uniqueness_all_lineups` to verify composite key behavior

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Banner "Locks and excludes reset for new upload" is visible on page | UI-04 | Visual check in browser | Upload new CSVs; confirm banner appears in results page above or below lineup output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
