---
phase: 2
slug: optimization-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_optimizer.py -x -q` |
| **Full suite command** | `python -m pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_optimizer.py -x -q`
- **After every plan wave:** Run `python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 0 | OPT-01 | unit | `python -m pytest tests/test_optimizer.py -x -q` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 1 | OPT-01 | unit | `python -m pytest tests/test_optimizer.py::test_tips_lineup_count -x` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 1 | OPT-01 | unit | `python -m pytest tests/test_optimizer.py::test_tips_salary_constraints -x` | ❌ W0 | ⬜ pending |
| 2-02-03 | 02 | 1 | OPT-01 | unit | `python -m pytest tests/test_optimizer.py::test_tips_collection_limits -x` | ❌ W0 | ⬜ pending |
| 2-02-04 | 02 | 1 | OPT-04 | unit | `python -m pytest tests/test_optimizer.py::test_same_player_once_per_lineup -x` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 1 | OPT-02 | unit | `python -m pytest tests/test_optimizer.py::test_intermediate_lineup_count -x` | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 | 1 | OPT-03 | unit | `python -m pytest tests/test_optimizer.py::test_no_card_reuse_across_contests -x` | ❌ W0 | ⬜ pending |
| 2-03-03 | 03 | 1 | OPT-04 | unit | `python -m pytest tests/test_optimizer.py::test_card_uniqueness_all_lineups -x` | ❌ W0 | ⬜ pending |
| 2-03-04 | 03 | 1 | OPT-06 | unit | `python -m pytest tests/test_optimizer.py::test_salary_floor_enforced -x` | ❌ W0 | ⬜ pending |
| 2-04-01 | 04 | 1 | OPT-01/02 | unit | `python -m pytest tests/test_optimizer.py::test_infeasibility_notice -x` | ❌ W0 | ⬜ pending |
| 2-04-02 | 04 | 1 | OPT-01/02 | unit | `python -m pytest tests/test_optimizer.py::test_partial_results -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_optimizer.py` — stubs for OPT-01, OPT-02, OPT-03, OPT-04, OPT-06
- [ ] `gbgolf/optimizer/__init__.py` — public API module skeleton
- [ ] `gbgolf/optimizer/engine.py` — ILP engine skeleton
- [ ] `pyproject.toml` — add `pulp>=3.3.0` to dependencies

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
