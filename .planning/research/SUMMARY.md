# Project Research Summary

**Project:** GB Golf Optimizer v1.2 — Automated Projection Fetching
**Domain:** DataGolf API integration + PostgreSQL storage + cron scheduling for Flask DFS golf optimizer
**Researched:** 2026-03-25
**Confidence:** HIGH

## Executive Summary

GBGolfOptimizer v1.2 extends a validated, stateless Flask optimizer (already running on Ubuntu 24.04 with Gunicorn + Nginx + systemd) by adding automated projection fetching from the DataGolf API, PostgreSQL-backed projection storage, and a UI source selector so users can choose between DataGolf projections and their own CSV uploads. The research shows this is a well-scoped addition: one new external dependency (the DataGolf `fantasy-projection-defaults` endpoint), one new storage layer (PostgreSQL with a single `projections` table), and a handful of targeted code changes to the existing upload route. The existing optimizer, constraints engine, and card pool logic remain entirely untouched.

The recommended approach is to add PostgreSQL via Flask-SQLAlchemy (Core queries only, no ORM), drive the scheduled fetch via a system cron invoking a Flask CLI command, and use `httpx` for the single HTTP call to DataGolf. This stack minimizes new dependencies while setting the foundation for v1.3 user accounts (SQLAlchemy + Flask-Migrate will already be in place). The critical design insight from architecture research is that the projection source abstraction — returning `dict[str, float]` from either DB or CSV — keeps the optimizer completely isolated from where projections came from.

The primary risks are operational, not architectural: the cron job must see the API key (which lives in a `.env` file, not in `~/.bashrc`), cron output must be explicitly redirected to a log file (no MTA on the VPS), the fetcher must never overwrite valid data on API failure (transactional replace pattern), and the DataGolf API response field names are not fully documented and require a discovery call before finalizing the Pydantic model and DB schema. All of these are avoidable with deliberate setup steps in Phase 1.

---

## Key Findings

### Recommended Stack

The v1.2 additions are minimal and targeted. The existing stack (Flask 3.x, PuLP/CBC, Pydantic v2, Gunicorn + Nginx + systemd) is unchanged. New dependencies are `httpx>=0.28` for the single DataGolf API call, `psycopg[binary]>=3.2` as the PostgreSQL driver (psycopg 3 is the modern successor to psycopg2, with bundled libpq so no system library install is needed), `SQLAlchemy>=2.0` + `Flask-SQLAlchemy>=3.1` for connection lifecycle and future Alembic migrations, `Flask-Migrate>=4.1` for schema migration support (critical for the v1.3 user accounts milestone), and `python-dotenv>=1.0` to load `DATAGOLF_API_KEY` and `DATABASE_URL`. Scheduling is handled entirely by the existing systemd/cron infrastructure — no APScheduler, no Celery, no Redis.

**Core technologies:**
- `httpx>=0.28`: HTTP client for DataGolf API — built-in timeout as first-class param, connection pooling, no external C deps; preferred over `requests` for cron context
- `psycopg[binary]>=3.2`: PostgreSQL driver — bundles libpq, active development (psycopg2 is maintenance-only), 4-5x more memory efficient, works as SQLAlchemy 2.0 dialect via `postgresql+psycopg://`
- `SQLAlchemy>=2.0` + `Flask-SQLAlchemy>=3.1`: ORM/Core + connection management — `db.init_app(app)` handles pool lifecycle with Gunicorn workers; Core queries (`text()`) keep things simple for one table
- `Flask-Migrate>=4.1`: Schema migration tooling — wraps Alembic with Flask CLI commands; auto-detects column changes since v4.0; essential bridge to v1.3 user accounts
- `python-dotenv>=1.0`: Secrets management — loads `.env` file for API key and `DATABASE_URL`; Flask auto-loads `.env` when installed; single file to manage on the VPS
- `systemd timer` (OS-level): Scheduler — zero new dependencies; runs Tue/Wed mornings; logs via journalctl; no Python process must stay alive between runs

**Version compatibility note:** `Flask-SQLAlchemy>=3.1` requires `SQLAlchemy>=2.0`. The SQLAlchemy connection string must use `postgresql+psycopg://` (not `psycopg2`).

### Expected Features

The v1.2 feature set is clean and well-bounded. Research confirms the DataGolf `fantasy-projection-defaults` endpoint returns current-week projections for the PGA Tour, refreshed when tee times are released (typically Tuesday). The endpoint uses query-parameter authentication with a Scratch Plus subscription key. Rate limits (45 req/min) are irrelevant for a twice-weekly cron fetch.

**Must have (table stakes — v1.2 launch):**
- DataGolf API fetcher (PROJ-01) — HTTP GET `fantasy-projection-defaults`, parse response, handle errors; core purpose of v1.2
- PostgreSQL projection storage (PROJ-03) — `projections` table with `dg_id`, `player_name`, `projected_score`, `event_name`, `fetched_at`; designed for v1.3 compatibility (no `user_id` needed on this table)
- Cron scheduler (PROJ-02) — systemd timer or crontab Tue/Wed mornings; invokes `flask fetch-projections` CLI command
- Projection source selector (PROJ-04) — radio button on existing upload page; "DataGolf (from DB)" or "Upload CSV"
- Stale data indicator (PROJ-05) — tournament name + relative age label; prevents user confusion with off-week data
- Player name normalization (DataGolf "Last, First" to GameBlazers "First Last") — extend existing `normalize_name()` pipeline with a `parse_datagolf_name()` step

**Should have (competitive — v1.2.x after validation):**
- Manual "Refresh Projections" button — triggers fetcher on demand from the UI; useful before Tuesday cron runs
- Fetch status dashboard — last fetch time, player count, error log; builds user confidence in automation
- Unmatched player report for DataGolf source — reuses existing `projection_warnings` pattern

**Defer (v1.3+):**
- Multi-source projection averaging — explicitly scoped to v2.0; requires multiple API integrations and weighting logic
- Projection comparison view (DataGolf vs CSV side-by-side) — nice-to-have; not needed for core workflow
- DataGolf player ID cross-reference table — name normalization is sufficient for 95%+ of players at v1.2 scale

**Anti-features confirmed:** Do not use DraftKings salary data from DataGolf (GameBlazers has its own salary system), do not store historical projection snapshots (only latest per event), and do not attempt fuzzy player name matching (golf has too many similar names; exact normalized match + explicit alias table is the correct approach).

### Architecture Approach

The v1.2 architecture adds a new background path (cron fetcher) and a DB read path to the existing stateless web request cycle, while keeping the optimizer completely isolated. The key isolation property: `gbgolf/optimizer/` receives `list[Card]` with `projected_score` already set and has zero knowledge of whether those projections came from the DB or a CSV upload. All DB integration is contained within three new/modified files: `gbgolf/db.py`, `gbgolf/fetch.py`, and `gbgolf/data/projections.py`. The existing route gains a single `if/else` branch on `projection_source` form field value.

**Major components:**
1. `gbgolf/db.py` (NEW) — Flask-SQLAlchemy init, engine config (`pool_size=2`, `max_overflow=3`, `pool_pre_ping=True`, `pool_recycle=1800`); registered in `create_app()` via `db.init_app(app)`
2. `gbgolf/fetch.py` (NEW) — DataGolf HTTP client + Flask CLI command (`flask fetch-projections`); invoked by cron; shares app config via Flask app context; uses transactional upsert (`INSERT ON CONFLICT`) keyed on `(dg_id, fetched_at::date)`
3. `gbgolf/data/projections.py` (MODIFIED) — gains `load_projections_from_db()` returning `dict[str, float]` — same interface as the existing CSV parser, so the optimizer is unaffected
4. `gbgolf/web/routes.py` (MODIFIED) — `POST /` branches on `projection_source` form field; calls DB or CSV path accordingly; passes `fetch_metadata` to template for staleness display
5. PostgreSQL `projections` table — single table, flat rows (no normalization), designed with v1.3 expansion in mind
6. systemd timer / crontab — runs `flask fetch-projections` Tue/Wed 7am (UTC-adjusted); redirects output to `/var/log/datagolf-fetch.log`

**Build order:** DB foundation first (fetcher writes to it), fetcher second (UI reads from it), source selector + staleness display third, deploy + verify fourth. This respects all dependency chains.

### Critical Pitfalls

1. **Cron cannot see the API key** — Cron spawns a minimal shell that does NOT inherit `~/.bashrc` or systemd `Environment=` directives. Store the key in `/opt/GBGolfOptimizer/.env` with `export DATAGOLF_API_KEY=...` and source it in the crontab entry: `. /opt/GBGolfOptimizer/.env && flask fetch-projections`. Verify by running the cron job via cron (not manually from SSH) and checking the log file.

2. **Fetcher overwrites good data when DataGolf API fails** — A "DELETE then INSERT" pattern leaves the table empty if the API returns an error or empty response. Use a transactional replace: validate the response first (minimum 20 players for a real field), then wrap `DELETE + INSERT` in a single transaction with automatic rollback on failure. Never delete existing data before confirming valid new data exists.

3. **PostgreSQL connection pool shared across Gunicorn forked workers** — If the engine is created before Gunicorn forks, workers share TCP connections and corrupt each other's query streams. The current `gbgolf.service` does NOT use `--preload`, so each worker calls `create_app()` independently and gets its own pool. Keep `--preload` out of the Gunicorn config. Set `pool_pre_ping=True` to handle idle connection drops.

4. **DataGolf API response field names are not fully documented** — The `fantasy-projection-defaults` endpoint documentation does not provide a complete JSON schema. The exact name for the projected points field (e.g., `proj_points`, `total_pts`, `projected_pts`) is unknown without a live API call. Build the Pydantic model with `model_config = ConfigDict(extra="allow")` initially, make a discovery call before the sprint begins, and document the exact field names before writing the DB schema.

5. **Player name mismatches between DataGolf and GameBlazers** — DataGolf uses "Last, First" format and DraftKings name conventions; GameBlazers uses "First Last". After `parse_datagolf_name()` reordering and `normalize_name()` NFKD normalization, the vast majority of players match. Edge cases (suffixes like Jr./Sr., alternate transliterations like "Hoejgaard" vs "Hojgaard", nickname differences like "Ben An" vs "Byeong Hun An") require a small explicit alias table populated from the first week of live testing. Do not use fuzzy matching.

---

## Implications for Roadmap

Based on research, the dependency chain is clear: DB schema must exist before the fetcher can write, the fetcher must work before the UI can read from it, and the source selector must follow both. This maps to a 4-phase build.

### Phase 1: Database Foundation

**Rationale:** All subsequent work depends on PostgreSQL being available and the Flask app connecting to it correctly. Connection pool configuration, `pg_hba.conf` auth, and the `.env` secrets file must be in place before the fetcher or UI work begins. This is also the phase where the most operationally dangerous pitfalls occur (wrong pool config, API key not visible to cron, secrets in version control).

**Delivers:** Running PostgreSQL instance on VPS with `gbgolf` database and user; `gbgolf/db.py` with Flask-SQLAlchemy init registered in `create_app()`; `projections` table created via migration DDL; `DATABASE_URL` in `.env` (not committed to git); Flask app starts cleanly with DB connection.

**Addresses:** PROJ-03 (PostgreSQL storage schema design)

**Avoids:** Pitfall 3 (Gunicorn forked worker pool sharing), Pitfall 6 (API key in git history), PostgreSQL peer auth blocking app connection

**Research flag:** Standard patterns — PostgreSQL + Flask-SQLAlchemy setup is well-documented. Skip `/gsd:research-phase`.

### Phase 2: DataGolf API Fetcher + Cron

**Rationale:** The fetcher depends on the DB (Phase 1) being ready. This phase has the highest density of gotchas: API key visibility to cron, silent cron failures with no log output, transactional data replacement, and the API response field name discovery. All must be solved before the UI work (Phase 3) begins, or the UI will be built against an untested data pipeline.

**Delivers:** `gbgolf/fetch.py` with `flask fetch-projections` CLI command; cron entry on VPS with log redirection; first successful automated fetch verified via log file; upsert logic confirmed idempotent; API response field names documented and Pydantic model finalized.

**Addresses:** PROJ-01 (DataGolf API fetcher), PROJ-02 (cron scheduler)

**Avoids:** Pitfall 1 (API key invisible to cron), Pitfall 2 (silent cron failures), Pitfall 7 (fetcher overwrites good data on API failure)

**Research flag:** The API response field names require a live discovery call before implementation. This is a known gap — not a research-phase issue, but an implementation prerequisite. Do the discovery call at the start of this phase.

### Phase 3: Projection Source Selector + Staleness Display

**Rationale:** Depends on Phase 1 (DB) and Phase 2 (data in DB). This is the user-facing deliverable — the UI change that makes v1.2 visible to the user. The `validate_pipeline()` refactor (splitting roster validation from projection merging) is the main structural code change; it should be done cleanly to preserve testability.

**Delivers:** `load_projections_from_db()` in `gbgolf/data/projections.py` returning `dict[str, float]`; refactored `validate_pipeline()` that accepts projection dict directly (not just file path); source selector radio buttons on `index.html`; staleness label showing tournament name and relative age; player name alias table populated from first live test.

**Addresses:** PROJ-04 (source selector), PROJ-05 (stale data display), player name normalization

**Avoids:** Pitfall 4 (player name mismatches), Pitfall 5 (wrong staleness labeling for off-week data), UX pitfalls (no tournament name shown, source resets on reload)

**Research flag:** Player name normalization edge cases are partially known but require live testing. Populate the alias table during this phase after running DataGolf projections against a real GameBlazers roster export.

### Phase 4: Deploy + Verification

**Rationale:** Integration testing in the deployed environment catches the pitfalls that only surface under production conditions: cron actually running on the VPS (not just working manually from SSH), Gunicorn workers connecting to PostgreSQL without pool issues, log rotation working, and the staleness display showing correct labels for both current-week and stale data states.

**Delivers:** Cron running and verified on VPS; both projection sources working end-to-end in the deployed app; stale data label verified; fetch log confirmed populating correctly; `pg_stat_activity` verified showing bounded connection count.

**Addresses:** All operational pitfalls from the "Looks Done But Isn't" checklist in PITFALLS.md

**Research flag:** Standard verification work. No research needed.

### Phase Ordering Rationale

- DB before fetcher: the fetcher's `INSERT` needs a table to write to, and the `DATABASE_URL` and pool configuration must be tested before any code depends on it.
- Fetcher before UI: the source selector needs real data in the DB to be meaningful; building the UI before the fetcher works means testing against empty tables, which masks important staleness and no-data-available states.
- Source selector before deploy verification: the full user-facing flow must be assembled before end-to-end verification makes sense.
- This order also front-loads the highest-risk pitfalls (cron environment, connection pooling, transactional data safety) into Phases 1 and 2, so Phases 3 and 4 are lower-risk by design.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2 (Fetcher):** DataGolf API response field names are the only unresolved technical gap. Not a research-phase issue — handle with a discovery API call at phase start before writing any code. The exact JSON structure for `fantasy-projection-defaults` must be logged and documented before finalizing the Pydantic model and DB schema.

Phases with standard patterns (skip research-phase):
- **Phase 1 (DB Foundation):** Flask-SQLAlchemy + PostgreSQL setup is thoroughly documented with official sources. Connection pool configuration values are well-established.
- **Phase 3 (Source Selector):** The branching architecture and `validate_pipeline()` refactor follow clear Flask patterns. The name normalization approach is an extension of existing code.
- **Phase 4 (Deploy + Verify):** Standard verification checklist from PITFALLS.md. No novel territory.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified against PyPI and official docs. Version compatibility matrix confirmed. psycopg 3 and Flask-SQLAlchemy 3.1 both actively maintained as of March 2026. |
| Features | HIGH for API structure and integration patterns; MEDIUM for exact API response fields | DataGolf endpoint parameters, auth method, and rate limits confirmed from official docs. Fantasy-projection-defaults response field names extrapolated from historical endpoint sample — requires live API call to confirm. |
| Architecture | HIGH | Based on direct codebase inspection plus official Flask, SQLAlchemy, and Gunicorn docs. Component boundaries and data flow are clear. |
| Pitfalls | HIGH for cron/DB/security pitfalls; MEDIUM for DataGolf-specific behavior | Cron environment, connection pooling, and secrets management pitfalls are universally documented failure modes. DataGolf off-week API behavior and exact response schema are unverified and require empirical testing. |

**Overall confidence:** HIGH — with one known gap that must be resolved at implementation start.

### Gaps to Address

- **DataGolf API response field names:** The exact JSON field name for the projected fantasy points value is unconfirmed. During Phase 2, make one live API call before writing any parsing code, log the full raw response, and update the Pydantic model and DB schema accordingly. The `projected_score` column name in the schema is a placeholder until the actual field name is confirmed.

- **DataGolf off-week API behavior:** What the `fantasy-projection-defaults` endpoint returns when no PGA Tour event is active (200 + empty array? 404? 200 + last week's stale data?) has no documented behavior. The fetcher's guard logic (minimum player count threshold, don't overwrite on empty response) handles the likely cases, but this must be tested empirically — ideally by checking the API on a Monday before projections drop or during an off-week.

- **GameBlazers player name format edge cases:** The alias table for players whose names differ between DataGolf and GameBlazers (e.g., "Ben An" vs "Byeong Hun An", suffix variations) can only be populated by running real DataGolf data against a real GameBlazers roster export. Plan for 1-2 rounds of alias table updates in the first week of production use.

- **PostgreSQL `pg_hba.conf` auth mode on production VPS:** Ubuntu 24.04 defaults to `peer` authentication for local connections, which blocks password-based app connections. Changing the `pg_hba.conf` entry for the `gbgolf` user to `scram-sha-256` (or `md5`) is a required setup step. This is documented in PITFALLS.md but must be executed during Phase 1 deployment.

---

## Sources

### Primary (HIGH confidence)
- [DataGolf API Access Documentation](https://datagolf.com/api-access) — endpoint parameters, authentication method, rate limits
- [DataGolf Raw Data Notes](https://datagolf.com/raw-data-notes) — field naming conventions, player_name format warning, event_id behavior
- [DataGolf Historical DFS Sample (JSON)](https://feeds.datagolf.com/historical-dfs-data/sample?site=draftkings&file_format=json) — verified response structure with actual field names
- [DataGolf Forum - PSA: API Rate Limits](https://forum.datagolf.com/t/psa-api-rate-limits/2511) — 45 req/min, 5-minute suspension enforcement
- [psycopg PyPI](https://pypi.org/project/psycopg/) — v3.3.3, Feb 2026; confirmed active maintenance
- [httpx PyPI](https://pypi.org/project/httpx/) — v0.28.1 stable
- [Flask-Migrate docs](https://flask-migrate.readthedocs.io/) — v4.1.0, Alembic wrapper with auto-compare_type
- [Flask-SQLAlchemy PyPI](https://pypi.org/project/Flask-SQLAlchemy/) — v3.1.1
- [SQLAlchemy 2.0 Connection Pooling docs](https://docs.sqlalchemy.org/en/20/core/pooling.html) — pool_pre_ping, pool_size, forking behavior
- [Flask CLI Commands](https://flask.palletsprojects.com/en/stable/cli/) — official Flask docs for CLI command pattern
- [Crontab environment variables](https://cronitor.io/guides/cron-environment-variables) — cron minimal shell, no ~/.bashrc inheritance
- [Install and configure PostgreSQL on Ubuntu](https://documentation.ubuntu.com/server/how-to/databases/install-postgresql/) — default peer auth, pg_hba.conf
- Existing codebase: `gbgolf/data/matching.py`, `gbgolf/web/__init__.py`, `deploy/gbgolf.service` — confirmed no --preload, no DB engine, normalize_name() exists

### Secondary (MEDIUM confidence)
- [Tiger Data psycopg benchmark](https://www.tigerdata.com/blog/psycopg2-vs-psycopg3-performance-benchmark) — psycopg 3 memory efficiency figures
- [SQLAlchemy connection pool within multiple threads and processes](https://davidcaron.dev/sqlalchemy-multiple-threads-and-processes/) — practical Gunicorn + SQLAlchemy fork safety patterns
- [Scheduling comparison: cron vs APScheduler vs Celery](https://leapcell.io/blog/scheduling-tasks-in-python-apscheduler-vs-celery-beat) — scheduler trade-off analysis
- [Flask Cron Jobs Architecture](https://blog.miguelgrinberg.com/post/run-your-flask-regularly-scheduled-jobs-with-cron) — Flask CLI command as cron target pattern
- [DataGolf FAQ](https://datagolf.com/frequently-asked-questions) — projection release timing (Monday/Tuesday before Thursday events)

### Tertiary (LOW confidence — needs live verification)
- DataGolf `fantasy-projection-defaults` exact JSON response schema — field name for projected points is unconfirmed; requires live API call
- DataGolf off-week API behavior — no documentation; must be tested empirically
- GameBlazers player name format for edge cases — no public documentation; requires comparison against actual roster export

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
