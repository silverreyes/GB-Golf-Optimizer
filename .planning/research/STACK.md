# Stack Research

**Domain:** Automated projection fetching (DataGolf API + PostgreSQL + cron) for Flask golf optimizer (v1.2)
**Researched:** 2026-03-25
**Confidence:** HIGH

## Scope

This is a SUBSEQUENT MILESTONE research file. It covers ONLY what is needed to add DataGolf API fetching, PostgreSQL storage, and scheduled cron jobs to the existing validated stack (Flask 3.x, PuLP/CBC, Pydantic v2, Jinja2/HTML/CSS, Gunicorn + Nginx + systemd on Ubuntu 24.04). The existing stack is NOT being re-evaluated.

## Recommended Stack Additions

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `httpx` | `>=0.28` | HTTP client for DataGolf API calls | Requests-compatible API but adds connection pooling, timeouts as first-class params, and HTTP/2. Lighter than `requests` for this use case (no session cookies needed). Built-in JSON response decoding. No external C dependencies. |
| `psycopg[binary]` | `>=3.2` | PostgreSQL driver (psycopg 3) | Psycopg 3 is the modern successor to psycopg2. Native Python typing, context-manager connections that auto-close, parameterized queries with `%s` or `$1` syntax. The `[binary]` extra bundles libpq so no system library install needed. 4-5x more memory efficient than psycopg2. |
| `SQLAlchemy` | `>=2.0` | ORM + schema definition + connection management | Provides table metadata for Alembic migrations, connection pooling via `create_engine`, and model classes for the projections table. The app only has 1-2 tables now, but v1.3 adds user accounts -- SQLAlchemy pays for itself when the schema grows. Flask-SQLAlchemy integrates it cleanly with the app factory. |
| `Flask-SQLAlchemy` | `>=3.1` | Flask integration for SQLAlchemy | Binds SQLAlchemy engine lifecycle to Flask app context. Handles session scoping per-request. Required by Flask-Migrate. |
| `Flask-Migrate` | `>=4.1` | Schema migrations via Alembic | Wraps Alembic with Flask CLI commands (`flask db init`, `flask db migrate`, `flask db upgrade`). Auto-detects column type changes since v4.0. Essential for v1.3 user accounts migration path. |
| systemd timer | (OS-level) | Scheduled fetcher (Tue/Wed mornings) | Already on Ubuntu 24.04. No Python process to keep alive. Logs via journalctl. Integrates with existing systemd deployment. Zero new dependencies. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-dotenv` | `>=1.0` | Load `.env` file for `DATAGOLF_API_KEY` and `DATABASE_URL` | At app startup and in the cron fetcher script. Keeps secrets out of code and systemd unit files. |
| `psycopg-pool` | (via `psycopg[pool]`) | Connection pooling for psycopg 3 | NOT needed if using SQLAlchemy (it has its own pool). Only install if going raw psycopg without SQLAlchemy. |
| `Alembic` | `>=1.14` | Database migration engine | Installed automatically as Flask-Migrate dependency. No direct install needed. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest-httpx` | Mock httpx calls in tests | Provides `httpx_mock` fixture for intercepting HTTP requests. Avoids hitting DataGolf API in CI. |
| `testing.postgresql` or manual `CREATE`/`DROP` | Test database fixtures | Use a real PostgreSQL instance in tests (not SQLite). SQLAlchemy dialect differences make SQLite-based tests unreliable for PostgreSQL-targeted schemas. |

## Installation

```bash
# Core additions for v1.2
pip install httpx "psycopg[binary]" SQLAlchemy Flask-SQLAlchemy Flask-Migrate python-dotenv

# Dev dependencies
pip install pytest-httpx
```

Updated `pyproject.toml` dependencies section:

```toml
dependencies = [
    "pydantic>=2.0",
    "python-dateutil>=2.9",
    "pulp>=3.3.0",
    "flask>=3.0",
    "gunicorn>=20.0",
    # v1.2 additions
    "httpx>=0.28",
    "psycopg[binary]>=3.2",
    "SQLAlchemy>=2.0",
    "Flask-SQLAlchemy>=3.1",
    "Flask-Migrate>=4.1",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "flask>=3.0", "pytest-httpx>=0.35"]
```

## Detailed Rationale

### HTTP Client: httpx (not requests, not the unofficial data_golf library)

**Why httpx over requests:**
- Built-in timeout parameter (not a bolted-on kwarg) -- critical for a cron job that must not hang
- Connection pooling via `httpx.Client()` context manager
- Identical API surface to requests (`response.json()`, `response.raise_for_status()`)
- No external C dependencies (pure Python + httpcore)
- The app is synchronous Flask, so only the sync client is needed -- no async complexity

**Why NOT the unofficial `data_golf` PyPI library:**
- Version 0.5.1, beta status, last updated June 2024
- The DataGolf API call is trivially simple: one GET request with 4 query params
- Adding a wrapper library for a single endpoint adds dependency risk with no benefit
- We control the exact request, error handling, and retry logic

**httpx usage pattern for the fetcher:**
```python
import httpx

with httpx.Client(timeout=30.0) as client:
    resp = client.get(
        "https://feeds.datagolf.com/preds/fantasy-projection-defaults",
        params={"tour": "pga", "site": "draftkings", "slate": "main", "key": api_key},
    )
    resp.raise_for_status()
    data = resp.json()
```

### PostgreSQL Driver: psycopg 3 (not psycopg2)

**Why psycopg 3:**
- Active development (v3.3.3 released Feb 2026), psycopg2 in maintenance-only mode
- Native Python typing and context manager support
- The `[binary]` wheel bundles libpq -- no need to `apt install libpq-dev` on the VPS
- 4-5x more memory efficient for result sets
- Works seamlessly as SQLAlchemy's PostgreSQL dialect driver

**SQLAlchemy connection string with psycopg 3:**
```
postgresql+psycopg://user:pass@localhost:5432/gbgolf
```
Note: the dialect is `psycopg` (not `psycopg2`). SQLAlchemy 2.0+ supports psycopg 3 natively.

### ORM: SQLAlchemy (not raw psycopg queries)

**Why SQLAlchemy despite being a small app:**
1. **Migration path to v1.3:** User accounts will add `users`, `sessions`, and possibly `saved_lineups` tables. SQLAlchemy + Alembic makes schema evolution safe and repeatable.
2. **Flask-Migrate integration:** `flask db migrate` auto-generates migration scripts from model changes. Raw SQL migrations are manual and error-prone.
3. **Connection pooling built in:** `create_engine()` pools connections by default. No need for separate psycopg-pool.
4. **Projection queries are simple:** 2-3 queries total (insert batch, select latest, select by tournament week). SQLAlchemy Core (not ORM session patterns) handles these cleanly without the "heavy ORM" overhead people complain about.

**Why NOT raw psycopg queries:**
- No migration tooling (must write raw `ALTER TABLE` scripts)
- Must manage connection lifecycle manually
- Must implement own connection pooling
- Gains (2x faster simple selects) are irrelevant -- the app runs <10 queries/request

**SQLAlchemy usage style:** Use SQLAlchemy Core for queries (table objects + `select()`/`insert()`) rather than the ORM session pattern. This keeps things lightweight while preserving Alembic migration support. Define models with `db.Model` for Flask-SQLAlchemy integration but query with Core expressions.

### Schema Migrations: Flask-Migrate (wrapping Alembic)

**Why Flask-Migrate (not standalone Alembic, not raw SQL files):**
- Integrates with Flask CLI: `flask db init`, `flask db migrate -m "add projections"`, `flask db upgrade`
- Auto-generates migration scripts by diffing model definitions against live database
- Since v4.0: auto-enables `compare_type=True` (detects column type changes) and `render_as_batch=True` (safe migrations)
- The v1.3 user accounts milestone will add 2-3 tables -- migrations will be essential
- Alembic (v1.18.4) is installed automatically as a dependency

**Migration workflow on VPS:**
```bash
# After deploy, run migrations
cd /opt/GBGolfOptimizer
source venv/bin/activate
flask db upgrade
```

### Scheduler: systemd timer (not APScheduler, not Celery)

**Why systemd timer:**
- Already on Ubuntu 24.04, zero new dependencies
- The fetch job runs 2x/week (Tuesday + Wednesday mornings) -- absurdly simple for cron
- Runs as an independent process: if it crashes, systemd logs it and tries next scheduled run
- Logs visible via `journalctl -u gbgolf-fetch.timer`
- No Python process must stay alive between runs
- Integrates with existing `gbgolf.service` deployment pattern

**Why NOT APScheduler:**
- Requires a persistent Python process (embed in Gunicorn workers or run separately)
- If Gunicorn restarts, scheduler state can be lost
- With multiple Gunicorn workers, the scheduler runs multiple times unless you add file locks or DB-backed job stores
- Solves a problem we don't have (dynamic job scheduling at runtime)

**Why NOT Celery / Celery Beat:**
- Requires a message broker (Redis or RabbitMQ) -- entirely new infrastructure
- Designed for distributed task queues across multiple workers
- Massive overkill for "fetch one API endpoint twice a week"
- Adds 3 new processes to manage (broker, worker, beat)

**systemd timer implementation:**

`/etc/systemd/system/gbgolf-fetch.timer`:
```ini
[Unit]
Description=Fetch DataGolf projections (Tue/Wed mornings)

[Timer]
# Tuesday and Wednesday at 8:00 AM ET
OnCalendar=Tue,Wed *-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

`/etc/systemd/system/gbgolf-fetch.service`:
```ini
[Unit]
Description=DataGolf projection fetcher (one-shot)
After=network.target postgresql.service

[Service]
Type=oneshot
User=deploy
WorkingDirectory=/opt/GBGolfOptimizer
ExecStart=/opt/GBGolfOptimizer/venv/bin/python -m gbgolf.fetch
Environment="PATH=/opt/GBGolfOptimizer/venv/bin"
```

### Environment / Secrets: python-dotenv + .env file

**Why python-dotenv:**
- Load `DATAGOLF_API_KEY` and `DATABASE_URL` from `.env` file
- Keeps secrets out of systemd unit files and source code
- Already a Flask ecosystem standard (Flask's `flask run` auto-loads `.env`)
- Single file to manage on the VPS: `/opt/GBGolfOptimizer/.env`

**`.env` file on VPS:**
```
DATAGOLF_API_KEY=your_key_here
DATABASE_URL=postgresql+psycopg://gbgolf:password@localhost:5432/gbgolf
SECRET_KEY=production-secret-here
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `httpx` | `requests` | If httpx causes import issues on the VPS (unlikely). requests 2.32.5 is fine but adds no benefit over httpx for this use case. |
| `psycopg[binary]` (v3) | `psycopg2-binary` | If VPS has Python <3.8 or if psycopg 3 has driver compatibility issues. psycopg2 is battle-tested but maintenance-only. |
| SQLAlchemy + Flask-Migrate | Raw psycopg queries + manual SQL files | If the app will NEVER grow beyond 1 table (but v1.3 user accounts contradicts this). Raw queries are faster to write initially but painful to migrate. |
| systemd timer | APScheduler | If the schedule needs to be user-configurable at runtime (it doesn't -- Tue/Wed is fixed). APScheduler would also work but adds complexity for no gain. |
| systemd timer | crontab | Both work. systemd timers are preferred on modern Ubuntu because they integrate with journalctl logging and `systemctl` management. crontab is fine too -- no strong preference. |
| `python-dotenv` | OS environment variables directly | If you prefer setting env vars in the systemd unit file via `Environment=` directives. python-dotenv is cleaner for managing multiple secrets. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `data_golf` PyPI library | Beta (0.5.1), unmaintained since June 2024, wraps a trivial single-endpoint call | Direct `httpx.get()` -- 5 lines of code |
| Celery + Redis/RabbitMQ | Requires message broker infrastructure for a 2x/week cron job | systemd timer (zero dependencies) |
| APScheduler | Requires persistent Python process; multi-worker Gunicorn causes duplicate runs | systemd timer |
| `psycopg2-binary` | Maintenance-only, no new features, C extension build issues | `psycopg[binary]` (v3) |
| SQLite | Not suitable for concurrent access from Gunicorn workers + cron fetcher | PostgreSQL |
| Django ORM / Peewee / Tortoise | Wrong ecosystem (Flask), or async-only, or too opinionated | SQLAlchemy with Flask-SQLAlchemy |
| `aiohttp` | Async HTTP client -- this is a sync Flask app, no event loop | `httpx` (sync mode) |
| Flask-APScheduler | Embeds scheduler in Flask process; breaks with multiple Gunicorn workers | systemd timer |
| MongoDB / Redis for projection storage | Projections are tabular data with relational queries (by tournament week, by fetch date). PostgreSQL is the right tool. | PostgreSQL |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `Flask-SQLAlchemy>=3.1` | `SQLAlchemy>=2.0`, `Flask>=3.0` | v3.1 requires SQLAlchemy 2.0+ |
| `Flask-Migrate>=4.1` | `Flask-SQLAlchemy>=3.0`, `Alembic>=1.14` | Auto-installs Alembic as dependency |
| `SQLAlchemy>=2.0` | `psycopg>=3.2` (via `postgresql+psycopg` dialect) | Must use `postgresql+psycopg://` connection string (not `postgresql+psycopg2://`) |
| `psycopg[binary]>=3.2` | PostgreSQL 12+ | Ubuntu 24.04 ships PostgreSQL 16; fully compatible |
| `httpx>=0.28` | Python 3.8+ | Stable release; v1.0 still in dev preview |
| `python-dotenv>=1.0` | Flask 3.x | Flask auto-loads `.env` if python-dotenv is installed |
| `pytest-httpx>=0.35` | `httpx>=0.28`, `pytest>=8.0` | Match httpx version range |

## DataGolf API Integration Notes

**Endpoint:** `GET https://feeds.datagolf.com/preds/fantasy-projection-defaults`

**Parameters for this project:**
- `tour=pga` (PGA Tour)
- `site=draftkings` (DraftKings scoring/salary)
- `slate=main` (main slate only)
- `file_format=json` (default)
- `key=<API_KEY>` (query parameter auth, required)

**Rate limit:** 45 requests/minute across all endpoints. Exceeding triggers a 5-minute suspension. The cron job makes 1 request per run, so rate limits are irrelevant.

**Authentication:** API key passed as query parameter (`&key=...`). Requires DataGolf Scratch Plus subscription.

**Response fields:** Exact JSON field names need to be discovered via a test API call during implementation. Expected fields based on the DataGolf Fantasy Projections page include player name, DraftKings salary, projected fantasy points, and ownership percentage. The fetcher should log and store the full response structure on first successful call.

**Staleness handling:** If the fetcher runs on Tuesday but DataGolf hasn't published current-week projections yet (e.g., tournament field not finalized), the API may return last week's data or an empty response. The fetcher should store the tournament/event identifier from the response and the UI should compare it against the current week to determine staleness.

## VPS Infrastructure Notes

**PostgreSQL on Ubuntu 24.04:**
```bash
# Install PostgreSQL (Ubuntu 24.04 ships v16)
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres createuser gbgolf
sudo -u postgres createdb gbgolf -O gbgolf
sudo -u postgres psql -c "ALTER USER gbgolf WITH PASSWORD 'secure_password';"
```

**No libpq-dev needed:** The `psycopg[binary]` wheel bundles its own libpq. No system-level C library installation required.

**Systemd timer activation:**
```bash
sudo systemctl enable gbgolf-fetch.timer
sudo systemctl start gbgolf-fetch.timer
# Verify
systemctl list-timers | grep gbgolf
```

## Sources

- [DataGolf API Access](https://datagolf.com/api-access) -- endpoint documentation, auth method, rate limits (HIGH confidence)
- [psycopg PyPI](https://pypi.org/project/psycopg/) -- v3.3.3, Feb 2026 (HIGH confidence)
- [psycopg 3 docs: differences from psycopg2](https://www.psycopg.org/psycopg3/docs/basic/from_pg2.html) -- migration guidance (HIGH confidence)
- [httpx PyPI](https://pypi.org/project/httpx/) -- v0.28.1 stable (HIGH confidence)
- [Flask-Migrate docs](https://flask-migrate.readthedocs.io/) -- v4.1.0, Alembic wrapper (HIGH confidence)
- [Flask-SQLAlchemy PyPI](https://pypi.org/project/Flask-SQLAlchemy/) -- v3.1.1 (HIGH confidence)
- [SQLAlchemy PyPI](https://pypi.org/project/SQLAlchemy/) -- v2.0.48, Mar 2026 (HIGH confidence)
- [Alembic PyPI](https://pypi.org/project/alembic/) -- v1.18.4, Feb 2026 (HIGH confidence)
- [data_golf PyPI](https://pypi.org/project/data_golf/) -- v0.5.1 beta, June 2024, evaluated and rejected (HIGH confidence)
- [Tiger Data psycopg benchmark](https://www.tigerdata.com/blog/psycopg2-vs-psycopg3-performance-benchmark) -- performance comparison (MEDIUM confidence)
- [Scheduling comparison: cron vs APScheduler vs Celery](https://leapcell.io/blog/scheduling-tasks-in-python-apscheduler-vs-celery-beat) -- scheduler trade-offs (MEDIUM confidence)

---
*Stack research for: GB Golf Optimizer v1.2 -- Automated Projection Fetching*
*Researched: 2026-03-25*
