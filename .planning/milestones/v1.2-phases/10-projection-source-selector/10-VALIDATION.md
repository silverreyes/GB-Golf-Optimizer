---
phase: 10
slug: projection-source-selector
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_web.py -x -q` |
| **Full suite command** | `python -m pytest -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_web.py -x -q`
- **After every plan wave:** Run `python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | SRC-01 | unit (web) | `python -m pytest tests/test_web.py::test_source_selector_rendered -x` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 0 | SRC-01 | unit (web) | `python -m pytest tests/test_web.py::test_projection_source_hidden_input -x` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 0 | SRC-02 | integration | `python -m pytest tests/test_web.py::test_post_auto_source_uses_db -x` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 0 | SRC-02 | unit | `python -m pytest tests/test_web.py::test_load_projections_from_db -x` | ❌ W0 | ⬜ pending |
| 10-01-05 | 01 | 0 | SRC-03 | unit (web) | `python -m pytest tests/test_web.py::test_staleness_label_rendered -x` | ❌ W0 | ⬜ pending |
| 10-01-06 | 01 | 0 | SRC-04 | unit (web) | `python -m pytest tests/test_web.py::test_auto_disabled_empty_db -x` | ❌ W0 | ⬜ pending |
| 10-01-07 | 01 | 0 | SRC-04 | unit (web) | `python -m pytest tests/test_web.py::test_auto_source_empty_db_error -x` | ❌ W0 | ⬜ pending |
| 10-01-08 | 01 | 0 | SRC-05 | integration | `python -m pytest tests/test_web.py::test_auto_source_unmatched_players -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_web.py` — 8 new test stubs covering SRC-01 through SRC-05 (test functions listed in map above)
- [ ] DB seed helper in `tests/test_web.py` or `tests/conftest.py` — seeds fetch + projection rows for web tests (similar pattern to `test_fetcher.py`)
- [ ] No new test files needed — all tests extend existing `tests/test_web.py`

*Existing `tests/conftest.py` in-memory SQLite app fixture covers all DB needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Source selector visual layout (radio buttons, label positioning) | SRC-01 | CSS/visual verification | Load `/` in browser, confirm two radio options are visible and styled correctly in dark theme |
| Disabled state styling on DataGolf option when no projections | SRC-04 | CSS disabled state visual | Load `/` with empty DB, confirm DataGolf radio appears visually disabled |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
