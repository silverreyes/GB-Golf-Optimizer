# Architecture Research

**Domain:** Integrating DataGolf API fetcher + PostgreSQL into existing Flask/Gunicorn golf optimizer
**Researched:** 2026-03-25
**Confidence:** HIGH (codebase inspection + verified patterns from Flask/SQLAlchemy/PostgreSQL docs)

---

## Context: Current v1.1 Architecture (What Exists Today)

The app is a stateless Flask application with two routes. All state lives in-request (card pool serialized to a hidden form field) or in Flask's cookie session (lock/exclude constraints). There is no database, no background jobs, and no external API calls.

```
Browser
  |
  v  POST multipart/form-data
+----------------------------------------------------------------+
|  Flask Blueprint (gbgolf/web/routes.py)                        |
|                                                                |
|  POST /         upload roster CSV + projections CSV            |
|    -> validate_pipeline() -> optimize() -> render results      |
|                                                                |
|  POST /reoptimize   re-run with lock/exclude from form state   |
|    -> deserialize card_pool -> optimize() -> render results    |
+-----+-----------------------+---------------------------------+
      |                       |
      v                       v
+---------------+   +--------------------+
| gbgolf/data/  |   | gbgolf/optimizer/  |
| CSV parsing   |   | ILP engine (PuLP)  |
| validation    |   | constraints        |
| matching      |   | two-phase locks    |
+---------------+   +--------------------+
```

**Key characteristics of the current design:**
- `create_app()` in `gbgolf/web/__init__.py` is the application factory
- `wsgi.py` calls `create_app()` and exposes `app` for Gunicorn
- Gunicorn runs 2 workers, binding to a Unix socket, behind Nginx
- systemd manages the Gunicorn process
- Card pool roundtrips via a serialized JSON hidden field (not stored server-side)
- Projections come exclusively from user-uploaded CSV files
- No database dependency at all

---

## Target v1.2 Architecture

```
                                  +-------------------+
                                  | System Cron       |
                                  | (Tue/Wed 7am ET)  |
                                  +--------+----------+
                                           |
                                           v
                              +---------------------------+
                              | flask fetch-projections   |
                              | (Flask CLI command)       |
                              |                           |
                              | 1. HTTP GET DataGolf API  |
                              | 2. Parse JSON response    |
                              | 3. INSERT into PostgreSQL |
                              +------------+--------------+
                                           |
                                           v
+------+    +-------------------+    +-----------+
|      |    | Flask App         |    |           |
| Nginx+--->| (Gunicorn x2)    +--->| PostgreSQL|
|      |    |                  |    |           |
+------+    | POST /           |    +-----------+
            |   roster CSV +   |         ^
            |   source select  |         |
            |   -> if "datagolf"|--------+
            |      query DB    |    read projections
            |   -> if "csv"    |
            |      parse file  |
            |   -> optimize()  |
            |                  |
            | POST /reoptimize |
            |   (unchanged)    |
            +------------------+
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| Cron fetcher | Fetch DataGolf API, store in DB | Flask CLI command invoked by system crontab |
| PostgreSQL | Persistent projection storage | Single `projections` table + metadata |
| DB module | Connection management, queries | `gbgolf/db.py` using Flask-SQLAlchemy (SQLAlchemy Core, not ORM) |
| Source selector | Let user choose DataGolf vs CSV | New form field on existing upload page |
| Staleness display | Show age of DB projections | Query in route, Jinja2 rendering |

---

## Recommended Project Structure (New + Modified Files)

```
gbgolf/
  db.py                  # NEW: Flask-SQLAlchemy init, engine config
  fetch.py               # NEW: DataGolf API client + Flask CLI command
  data/
    projections.py       # MODIFIED: add load_projections_from_db() function
    models.py            # MODIFIED: no new Card fields needed (projections remain float)
    __init__.py          # MODIFIED: update validate_pipeline to accept projection source
  web/
    __init__.py          # MODIFIED: init db, register CLI command
    routes.py            # MODIFIED: source selector logic, staleness query
    templates/
      index.html         # MODIFIED: source selector UI, staleness label

deploy/
  gbgolf.service         # MODIFIED: add DATABASE_URL env var
  fetch-cron             # NEW: crontab entry file (documentation/install reference)

migrations/
  001_create_projections.sql  # NEW: schema DDL

tests/
  test_fetch.py          # NEW: DataGolf client tests (mocked HTTP)
  test_db.py             # NEW: DB read/write tests (test PostgreSQL or SQLite)
```

### Structure Rationale

- **`gbgolf/db.py`:** Centralizes database setup. Flask-SQLAlchemy's `db.init_app(app)` pattern fits the existing application factory. Keeps DB concerns out of route code.
- **`gbgolf/fetch.py`:** The fetcher is a standalone concern (HTTP client + DB write). Lives at package root, not inside `data/` or `web/`, because it is invoked by CLI, not by web requests.
- **`migrations/`:** Raw SQL migration files. No Alembic -- overkill for one table. Manual `psql -f` on the VPS.
- **`deploy/fetch-cron`:** Documentation artifact showing the crontab line. Not automatically installed.

---

## Architectural Patterns

### Pattern 1: Flask CLI Command for Cron (Not Standalone Script)

**What:** The DataGolf fetcher is a `@app.cli.command()` registered in the Flask app, invoked by system cron as `flask fetch-projections`.

**Why this over a standalone script:**
- Shares the app's database configuration (DATABASE_URL from environment)
- Runs inside Flask application context, so `db.session` / `db.engine` work identically to web request code
- No duplicated config loading, no separate DB connection setup
- Single source of truth for the DB connection string

**Why this over APScheduler / Celery:**
- Two cron runs per week is trivial scheduling -- no library needed
- APScheduler inside Gunicorn creates duplicate schedulers per worker (a known footgun)
- Celery requires a broker (Redis/RabbitMQ) -- massive overkill for 2 jobs/week

**Cron invocation:**
```bash
# /etc/cron.d/gbgolf-fetch or user crontab for deploy user
0 7 * * 2,3 cd /opt/GBGolfOptimizer && venv/bin/flask fetch-projections >> /var/log/gbgolf-fetch.log 2>&1
```

**Trade-offs:** Cron has no retry logic. If the DataGolf API is down at 7am Tuesday, that fetch is missed. Acceptable for this use case -- Wednesday is the backup, and stale data display handles the gap. If needed later, a simple wrapper script with `|| flask fetch-projections` retry at +30min is trivial.

### Pattern 2: Flask-SQLAlchemy with SQLAlchemy Core (Not ORM)

**What:** Use Flask-SQLAlchemy for connection lifecycle management (init_app, teardown, pool config), but write queries using SQLAlchemy Core `text()` or `Table` objects -- not the ORM (no mapped classes, no `db.Model`).

**Why Flask-SQLAlchemy at all (vs raw psycopg2):**
- Handles connection pool lifecycle with Gunicorn workers automatically (pool disposal on fork)
- `db.session` is a scoped session tied to Flask's application context -- auto-cleanup on request teardown
- `pool_pre_ping=True` handled via engine options, no manual keepalive code
- One-line setup: `db.init_app(app)` in the factory

**Why Core and not ORM:**
- The app has exactly one table with simple INSERT/SELECT queries
- No relationships, no lazy loading, no identity map -- ORM adds complexity for zero benefit
- Raw SQL or `text()` is clearer for the 3-4 queries this feature needs
- Keeps the codebase consistent with its current "plain dataclass" philosophy (Pydantic at boundary, dataclass internally)

**Example query pattern:**
```python
from sqlalchemy import text

def get_current_projections(db_session):
    """Fetch the most recent projection set from the database."""
    result = db_session.execute(text("""
        SELECT player_name, projected_score, salary, dg_id,
               fetched_at, event_name, tour
        FROM projections
        WHERE fetched_at = (SELECT MAX(fetched_at) FROM projections)
    """))
    return result.mappings().all()
```

### Pattern 3: Projection Source Branching in the Upload Route

**What:** The existing `POST /` route gains a `projection_source` form field. When "datagolf" is selected, projections come from the DB instead of a CSV upload. When "csv" is selected, the existing CSV upload flow is unchanged.

**Why modify the existing route (not a new route):**
- The upload route already handles the full pipeline: parse roster -> merge projections -> filter -> optimize -> render
- A new route would duplicate the roster parsing, optimization, and rendering logic
- The only branching point is "where do projections come from?" -- a single `if/else` at line ~100 in routes.py
- The reoptimize route needs zero changes (it already works from serialized card_pool)

**Branching logic:**
```python
# In POST / handler:
projection_source = request.form.get("projection_source", "csv")

if projection_source == "datagolf":
    # Query DB for current-week projections
    projections_dict, fetch_metadata = load_projections_from_db(db.session)
    if not projections_dict:
        return render_template("index.html", error="No DataGolf projections available.")
else:
    # Existing CSV upload flow (unchanged)
    projections_file = request.files.get("projections")
    ...
```

**Impact on validate_pipeline():** The `validate_pipeline` function currently takes a `projections_path` string (file path). For DB-sourced projections, we need to pass a `dict[str, float]` directly. Two clean options:

1. **Split validate_pipeline** into roster-only validation + separate projection merge -- cleanest, most testable
2. **Accept either path or dict** via an overloaded parameter -- simpler but less clean

Recommendation: Option 1. Split `validate_pipeline` so the roster validation and projection merge are separate steps. The route orchestrates them. This avoids coupling the data layer to "file vs DB" concerns.

---

## Data Flow

### Flow 1: Cron Fetch (Background, No User Interaction)

```
System Cron (Tue/Wed 7am)
    |
    v
flask fetch-projections
    |
    v
HTTP GET https://feeds.datagolf.com/preds/fantasy-projection-defaults
    ?tour=pga&site=draftkings&slate=main&file_format=json&key=...
    |
    v
Parse JSON response -> list of player projection dicts
    |
    v
INSERT INTO projections (dg_id, player_name, projected_score, salary,
    proj_ownership, event_name, tour, fetched_at)
    -- Use INSERT ON CONFLICT (upsert) keyed on (dg_id, fetched_at::date)
    -- so re-running the same day is idempotent
    |
    v
COMMIT + log success/failure
```

### Flow 2: User Optimization with DataGolf Source

```
Browser: User uploads roster CSV, selects "DataGolf" radio, submits
    |
    v
POST / (routes.py index())
    |
    +-> Parse roster CSV (existing flow, unchanged)
    |
    +-> projection_source == "datagolf"
    |     |
    |     v
    |   load_projections_from_db(db.session)
    |     -> SELECT player_name, projected_score FROM projections
    |        WHERE fetched_at = (SELECT MAX(fetched_at) FROM projections)
    |     -> Returns dict[str, float] + metadata (event_name, fetched_at, age)
    |
    +-> match_projections(cards, projections_dict)  # existing function
    |
    +-> apply_filters(enriched_cards)               # existing function
    |
    +-> optimize(valid_cards, contests, constraints) # existing function
    |
    v
render_template("index.html", result=..., projection_source="datagolf",
    fetch_info={event_name, fetched_at, staleness_label})
```

### Flow 3: User Optimization with CSV Source (Unchanged)

```
Browser: User uploads roster CSV + projections CSV, selects "CSV", submits
    |
    v
POST / (routes.py index())  -- existing flow, zero changes to CSV path
```

### Flow 4: Stale Data Display

```
Browser: GET / or page load
    |
    v
Query: SELECT event_name, fetched_at FROM projections
       ORDER BY fetched_at DESC LIMIT 1
    |
    v
Calculate staleness: datetime.now() - fetched_at
    |
    v
Jinja2 renders:
  - If < 24h: "DataGolf projections for [event] (updated today)"
  - If 1-6 days: "DataGolf projections for [event] (updated X days ago)"
  - If > 6 days: "DataGolf projections for [event] (X days old -- may be stale)"
  - If no data: "No DataGolf projections available (upload CSV instead)"
```

---

## Database Schema

### `projections` Table

```sql
CREATE TABLE projections (
    id              SERIAL PRIMARY KEY,
    dg_id           INTEGER NOT NULL,           -- DataGolf's player identifier
    player_name     TEXT NOT NULL,               -- Display name from API
    projected_score NUMERIC(6,2) NOT NULL,       -- Fantasy points projection
    salary          INTEGER,                     -- DraftKings salary (informational)
    proj_ownership  NUMERIC(5,2),                -- Projected ownership % (informational)
    event_name      TEXT NOT NULL,               -- e.g. "THE PLAYERS Championship"
    tour            TEXT NOT NULL DEFAULT 'pga',  -- pga, euro, opp, alt
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Uniqueness: one projection per player per fetch-day
    -- Allows re-fetches on same day to upsert
    UNIQUE (dg_id, fetched_at::date)
);

-- Index for the most common query: "get latest projections"
CREATE INDEX idx_projections_fetched_at ON projections (fetched_at DESC);

-- Index for potential future query: "get projections for specific event"
CREATE INDEX idx_projections_event ON projections (event_name, fetched_at DESC);
```

**Schema design notes:**
- `dg_id` is DataGolf's stable player identifier. More reliable than name matching for future features.
- `player_name` is stored as-is from the API. Name normalization happens at match time (existing `normalize_name()` function).
- `salary` and `proj_ownership` are stored for informational display but are NOT used in optimization. The optimizer uses roster CSV salaries (which reflect the user's actual card salaries, not DraftKings salaries).
- `fetched_at` uses TIMESTAMPTZ for timezone-aware timestamps.
- The UNIQUE constraint on `(dg_id, fetched_at::date)` makes same-day re-runs idempotent via `INSERT ... ON CONFLICT DO UPDATE`.
- **v1.3 user accounts compatibility:** This schema is user-independent. When user accounts arrive, projections remain shared (all users see the same DataGolf data). No `user_id` column needed on this table.

**DataGolf API response fields (LOW confidence -- needs verification via test API call):**
The exact JSON field names from the `fantasy-projection-defaults` endpoint could not be confirmed from public documentation. Based on DataGolf's website UI and unofficial libraries, the response likely includes fields like `dg_id`, `player_name`, `salary`, `proj_ownership`, and a projected points field. The fetcher implementation should include a discovery step: make one test API call and log the raw response to confirm field names before writing the parser.

---

## Connection Management with Gunicorn

### The Problem

Gunicorn with `--workers 2` forks after the master process loads the app (when using `--preload`, which this project does NOT currently use). Even without preload, each worker independently calls `create_app()` and gets its own engine/pool. The risk is low with the current setup, but connection hygiene matters.

### Recommended Configuration

```python
# gbgolf/db.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(engine_options={
    "pool_pre_ping": True,     # Verify connections are alive before checkout
    "pool_size": 2,            # 2 persistent connections per worker
    "max_overflow": 3,         # Allow up to 5 total per worker under burst
    "pool_recycle": 1800,      # Recycle connections every 30 minutes
})
```

**Why these values:**
- `pool_size=2`: Each Gunicorn worker handles one request at a time (sync workers). Two connections per worker is sufficient (one active + one spare). Total across 2 workers = 4 persistent connections.
- `max_overflow=3`: The cron fetcher runs in a separate process with its own pool. 5 total connections per process is generous for single-threaded sync workers.
- `pool_pre_ping=True`: PostgreSQL may close idle connections (depending on `idle_in_transaction_session_timeout`). Pre-ping avoids stale connection errors after overnight idle.
- `pool_recycle=1800`: Safety net for long-lived connections. 30 minutes is conservative.

**Total PostgreSQL connections:** 2 workers x 2 pool = 4 persistent + occasional cron = 5 max. Well within PostgreSQL's default `max_connections=100`.

### Application Factory Integration

```python
# gbgolf/web/__init__.py
from gbgolf.db import db

def create_app() -> Flask:
    app = Flask(...)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "postgresql://gbgolf:password@localhost/gbgolf"
    )

    db.init_app(app)

    # Register CLI commands
    from gbgolf.fetch import register_cli
    register_cli(app)

    from gbgolf.web.routes import bp
    app.register_blueprint(bp)

    return app
```

**No preload concern:** The current `gbgolf.service` does NOT use `--preload`. Each Gunicorn worker calls `create_app()` independently, meaning each worker creates its own engine and pool. No `engine.dispose()` or fork-safety hooks are needed with this setup. If `--preload` is added later for faster restarts, a `post_worker_init` hook in the Gunicorn config would be needed to dispose the inherited engine.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| DataGolf API | HTTP GET with API key in query string | Rate limit: 45 req/min with 5-min suspension. Fetcher makes 1 request per run, no concern. |
| PostgreSQL | Flask-SQLAlchemy (SQLAlchemy Core) | Local socket or TCP. Managed by Ubuntu's `postgresql` service. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Cron fetcher -> DB | Flask CLI command -> `db.session.execute()` -> COMMIT | Fetcher is a Flask CLI command, shares app context |
| Web route -> DB | `db.session.execute()` read-only | Route reads projections; never writes |
| Web route -> data layer | `match_projections(cards, proj_dict)` | Existing function works with dict from either CSV or DB |
| Web route -> optimizer | `optimize(valid_cards, contests, constraints)` | Completely unchanged -- optimizer is projection-source-agnostic |
| DB module -> models | Returns `dict[str, float]` (same as CSV parser) | No new model types needed for projections |

### Key Isolation Property

The optimizer (`gbgolf/optimizer/`) has ZERO knowledge of where projections came from. It receives `list[Card]` with `projected_score` and `effective_value` already set. This means the entire DB integration is contained within `gbgolf/db.py`, `gbgolf/fetch.py`, `gbgolf/data/projections.py`, and `gbgolf/web/routes.py`. The optimizer, engine, and constraint modules are untouched.

---

## Anti-Patterns

### Anti-Pattern 1: APScheduler Inside Gunicorn

**What people do:** Embed APScheduler in the Flask app to run the fetcher on a schedule.
**Why it's wrong:** Gunicorn spawns multiple workers. Each worker runs its own APScheduler instance. With 2 workers, the fetcher runs twice at the same time, causing duplicate inserts (or worse, race conditions). The standard "fix" (BackgroundScheduler with a file lock) adds fragile complexity.
**Do this instead:** System cron + Flask CLI command. One invocation, guaranteed single execution, no worker duplication.

### Anti-Pattern 2: Separate Config for Cron Script

**What people do:** Write a standalone Python script for the cron job with its own `DATABASE_URL` hardcoded or read from a separate `.env` file.
**Why it's wrong:** Configuration drift. The web app and cron script fall out of sync on DB credentials, connection settings, or schema assumptions.
**Do this instead:** Flask CLI command (`flask fetch-projections`) that inherits all app config from the same `create_app()` factory.

### Anti-Pattern 3: ORM Model for One Table

**What people do:** Create a `db.Model` subclass with `SQLAlchemy.Column` definitions for the projections table.
**Why it's wrong for this project:** The app has one table with 3-4 simple queries. ORM adds a mapped class, session identity map complexity, lazy loading confusion, and a migration tool dependency (Alembic). All for zero benefit when the queries are trivial `INSERT` and `SELECT`.
**Do this instead:** SQLAlchemy Core with `text()` queries. Write raw SQL that's immediately readable.

### Anti-Pattern 4: Storing Card Pool in Database

**What people do:** Move the card pool from the hidden form field to a database table, thinking it's "more proper."
**Why it's wrong for this project:** The card pool is per-session, ephemeral, and changes every time the user uploads a new roster CSV. Storing it in the DB adds a cleanup problem (when to delete old pools?), a user identification problem (no user accounts in v1.2), and gains nothing over the current hidden field approach.
**Do this instead:** Keep the hidden form field for card pool serialization. It works, it's stateless, and it'll naturally transition to user-account-scoped storage in v1.3.

### Anti-Pattern 5: New Route for DataGolf Optimization

**What people do:** Create a separate `POST /optimize-datagolf` route instead of modifying the existing upload route.
**Why it's wrong:** Duplicates roster parsing, optimization, rendering, and template logic. Two routes that do 90% the same thing diverge over time.
**Do this instead:** Add `projection_source` form field to the existing `POST /` route. The branching is one `if/else` at the projection loading step.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (1-5 users) | 2 Gunicorn workers, pool_size=2, single PostgreSQL instance. More than sufficient. |
| 10-50 users | No changes needed. PostgreSQL handles concurrent reads easily. ILP solve time is the bottleneck (~100ms per lineup), not DB. |
| 100+ users | Consider server-side session storage (Redis or DB) instead of cookie sessions. Card pool hidden field size could become a concern with large rosters. This is a v1.3+ concern. |

### What Breaks First

1. **Cookie session size** (4KB limit): With many lock/exclude constraints, the cookie approaches its limit. Not a v1.2 concern (locks are small), but worth monitoring.
2. **Hidden form field size**: A large roster (200+ cards) serialized to JSON could slow page rendering. Not realistic for current GameBlazers roster sizes (~50-80 cards).
3. **ILP solve time**: PuLP/CBC solves in <100ms for current roster sizes. Would only be a concern at 500+ cards, which GameBlazers doesn't produce.

None of these are v1.2 concerns. The DB integration adds no new scaling bottleneck.

---

## Build Order (Suggested Phases for v1.2)

The build order respects dependencies: DB before fetcher (fetcher writes to DB), fetcher before UI (UI reads from DB).

### Phase 1: Database Foundation
1. Install PostgreSQL on VPS, create `gbgolf` database and user
2. Create `gbgolf/db.py` with Flask-SQLAlchemy setup
3. Write `migrations/001_create_projections.sql`
4. Modify `create_app()` to call `db.init_app(app)`
5. Add `DATABASE_URL` to systemd service environment
6. Tests: verify DB connection in test fixture, basic read/write

### Phase 2: DataGolf Fetcher
1. Create `gbgolf/fetch.py` with API client and Flask CLI command
2. Implement API response parsing (confirm field names via test call first)
3. Implement upsert logic (INSERT ON CONFLICT)
4. Register CLI command in `create_app()`
5. Tests: mock HTTP responses, verify DB writes
6. Deploy: add crontab entry on VPS

### Phase 3: Projection Source Selector + Staleness
1. Add `load_projections_from_db()` to `gbgolf/data/projections.py`
2. Refactor `validate_pipeline()` to accept projection dict directly (not just file path)
3. Modify `POST /` route to branch on `projection_source` form field
4. Add projection source radio buttons to `index.html`
5. Implement staleness label (query latest `fetched_at`, compute age)
6. Tests: full integration test with both sources

### Phase 4: Deploy + Verify
1. Run migration on VPS PostgreSQL
2. Deploy updated app code
3. Verify cron fetcher runs successfully
4. Verify both projection sources work in the UI
5. Test stale data display with old and current data

---

## Sources

- [Flask Application Factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/) -- official Flask docs
- [Flask CLI Commands](https://flask.palletsprojects.com/en/stable/cli/) -- official Flask docs
- [Flask + Gunicorn Deployment](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/) -- official Flask docs
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html) -- official SQLAlchemy 2.0 docs (HIGH confidence)
- [Flask-SQLAlchemy Configuration](https://flask-sqlalchemy.readthedocs.io/en/stable/config/) -- official Flask-SQLAlchemy docs (HIGH confidence)
- [SQLAlchemy with Forked Processes](https://davidcaron.dev/sqlalchemy-multiple-threads-and-processes/) -- David Caron analysis (MEDIUM confidence, verified against SQLAlchemy docs)
- [Flask Cron Jobs Architecture](https://blog.miguelgrinberg.com/post/run-your-flask-regularly-scheduled-jobs-with-cron) -- Miguel Grinberg (MEDIUM confidence)
- [DataGolf API Access](https://datagolf.com/api-access) -- official DataGolf docs (HIGH confidence for endpoint/params, LOW confidence for response fields)

---
*Architecture research for: GBGolfOptimizer v1.2 -- DataGolf API + PostgreSQL integration*
*Researched: 2026-03-25*
