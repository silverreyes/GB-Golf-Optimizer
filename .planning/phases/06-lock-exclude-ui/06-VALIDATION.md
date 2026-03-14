---
phase: 6
slug: lock-exclude-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_web.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_web.py -x -q`
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 0 | UI-01 | integration | `pytest tests/test_web.py::test_player_pool_section_rendered -x` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 0 | UI-01 | integration | `pytest tests/test_web.py::test_player_pool_table_columns -x` | ❌ W0 | ⬜ pending |
| 6-01-03 | 01 | 0 | UI-01 | integration | `pytest tests/test_web.py::test_lock_exclude_checkboxes_in_form -x` | ❌ W0 | ⬜ pending |
| 6-01-04 | 01 | 0 | UI-01 | integration | `pytest tests/test_web.py::test_lock_golfer_first_row_only -x` | ❌ W0 | ⬜ pending |
| 6-01-05 | 01 | 0 | UI-01 | integration | `pytest tests/test_web.py::test_reoptimize_parses_lock_checkboxes -x` | ❌ W0 | ⬜ pending |
| 6-01-06 | 01 | 0 | UI-01 | integration | `pytest tests/test_web.py::test_reoptimize_parses_exclude_checkboxes -x` | ❌ W0 | ⬜ pending |
| 6-01-07 | 01 | 0 | UI-01 | integration | `pytest tests/test_web.py::test_reoptimize_parses_lock_golfer -x` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 0 | UI-03 | integration | `pytest tests/test_web.py::test_lineup_lock_column_header -x` | ❌ W0 | ⬜ pending |
| 6-02-02 | 02 | 0 | UI-03 | integration | `pytest tests/test_web.py::test_locked_card_shows_lock_icon -x` | ❌ W0 | ⬜ pending |
| 6-02-03 | 02 | 0 | UI-03 | integration | `pytest tests/test_web.py::test_nonlocked_card_blank_lock_column -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_web.py` — add ~10 new test functions covering UI-01 and UI-03 (existing file exists but lacks Phase 6 tests)
- [ ] No new fixture or conftest changes needed — existing `client` fixture is sufficient
- [ ] No framework install needed — pytest already configured in `pyproject.toml`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| JS conflict prevention (checking Lock disables Exclude and vice versa) | UI-01 | Browser-side JS interaction cannot be tested with pytest | Upload CSVs, check Lock for a card → verify Exclude is disabled; check Exclude → verify Lock is disabled |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
