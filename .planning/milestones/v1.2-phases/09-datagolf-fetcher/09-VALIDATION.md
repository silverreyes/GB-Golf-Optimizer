---
phase: 9
slug: datagolf-fetcher
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ (already configured) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/test_fetcher.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_fetcher.py -x -q`
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 9-W0-01 | 01 | 0 | FETCH-01 | unit | `pytest tests/test_fetcher.py::test_fetch_writes_to_db -x` | ❌ W0 | ⬜ pending |
| 9-W0-02 | 01 | 0 | FETCH-02 | unit | `pytest tests/test_fetcher.py::test_cli_command_registered -x` | ❌ W0 | ⬜ pending |
| 9-W0-03 | 01 | 0 | FETCH-03 | unit | `pytest tests/test_fetcher.py::test_fetch_log_written -x` | ❌ W0 | ⬜ pending |
| 9-W0-04 | 01 | 0 | FETCH-04 | unit | `pytest tests/test_fetcher.py::test_low_count_preserves_data -x` | ❌ W0 | ⬜ pending |
| 9-W0-05 | 01 | 0 | FETCH-04 | unit | `pytest tests/test_fetcher.py::test_api_error_preserves_data -x` | ❌ W0 | ⬜ pending |
| 9-W0-06 | 01 | 0 | FETCH-06 | unit | `pytest tests/test_fetcher.py::test_parse_datagolf_name -x` | ❌ W0 | ⬜ pending |
| 9-W0-07 | 01 | 0 | FETCH-06 | unit | `pytest tests/test_fetcher.py::test_name_edge_cases -x` | ❌ W0 | ⬜ pending |
| 9-W0-08 | 01 | 0 | FETCH-01 | unit | `pytest tests/test_fetcher.py::test_idempotent_fetch -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_fetcher.py` — stubs for FETCH-01, FETCH-02, FETCH-03, FETCH-04, FETCH-06
- [ ] `pyproject.toml` — add `httpx>=0.28` dependency
- [ ] `.gitignore` — add `logs/` entry

*Wave 0 must complete before any implementation tasks run.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cron job fires on VPS at correct time | FETCH-02 | Requires live VPS environment with crontab installed | SSH to VPS, run `crontab -l` to verify entry; check `logs/fetch.log` after scheduled run |
| Live DataGolf API response structure discovery | FETCH-01 | Requires valid API key and live network call | Run discovery script, log raw JSON, confirm field names match Pydantic model |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
