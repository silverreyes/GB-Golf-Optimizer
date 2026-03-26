# Phase 8: Database Foundation - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire PostgreSQL into the Flask app: configure the connection, define the `fetches` and `projections` tables via Flask-SQLAlchemy Core (no ORM), and set up Flask-Migrate so Phase 9 can immediately write projection data. No data fetching, no UI changes. Phase 8 is complete when the app starts cleanly with a DB connection and the schema is applied.

</domain>

<decisions>
## Implementation Decisions

### Table schema — `fetches` table
- Serial integer `id` as surrogate primary key
- `tournament_name` VARCHAR NOT NULL — name of the event from DataGolf
- `fetched_at` TIMESTAMPTZ NOT NULL — always inserted as UTC; Python uses `datetime.now(UTC)`
- `player_count` INTEGER NOT NULL — number of rows written in this batch (for fetch log / validation)
- `source` VARCHAR NOT NULL — hardcoded `'datagolf'` for v1.2; reserved for multi-source in v1.3
- `tour` VARCHAR NOT NULL — hardcoded `'pga'` for v1.2; reserved for multi-tour in v1.3+

### Table schema — `projections` table
- Serial integer `id` as surrogate primary key
- `fetch_id` INTEGER NOT NULL REFERENCES `fetches(id)` — FK linking each row to its batch
- `player_name` VARCHAR NOT NULL — normalized "First Last" format (FETCH-06 handled in Phase 9)
- `projected_score` REAL NOT NULL — REAL/FLOAT type; PuLP converts to float anyway, NUMERIC precision not needed

### Schema design rationale
- Two-table design (fetches + projections) enables atomic batch operations: Phase 9 inserts a `fetches` row first, then bulk-inserts all `projections` with the new `fetch_id`. Deleting stale data = delete from `fetches` WHERE id = X (cascades to projections via FK)
- No `user_id` column — defer to v1.3 migration (Flask-Migrate makes this a trivial one-liner ALTER TABLE)
- `source` and `tour` columns are cheap insurance; Phase 9 hardcodes their values; v1.3+ can query by them

### Stack decisions (already locked in STATE.md)
- Flask-SQLAlchemy Core (no ORM) — tables declared as `sqlalchemy.Table` objects, queries via `db.session.execute(text(...))`
- Flask-Migrate for schema migrations — migration scripts committed to version control
- python-dotenv for `.env` secrets — `DATABASE_URL` and `DATAGOLF_API_KEY`
- No APScheduler/Celery — system cron calls `flask fetch-projections` CLI

### Claude's Discretion
- Where `db = SQLAlchemy()` lives (recommended: `gbgolf/db.py` to keep DB code isolated from app factory and web blueprint)
- Exact migration script structure and Flask-Migrate init location
- ON DELETE CASCADE vs application-level delete ordering
- `.env.example` contents and wording
- Connection pool sizing for Gunicorn forked workers (NullPool vs pre-ping approach)
- Test setup for DB integration (not discussed — Claude decides appropriate approach)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — FETCH-05 (columns required for projections table: player name, projected score, tournament name, fetch timestamp)

### Project decisions
- `.planning/PROJECT.md` — Key Decisions table (Flask-SQLAlchemy Core, Flask-Migrate, python-dotenv, httpx, no APScheduler)
- `.planning/STATE.md` — Accumulated Context > Decisions section (DATABASE_URL, DATAGOLF_API_KEY, name normalization pipeline)

No external specs — requirements are fully captured in decisions above and the referenced planning files.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gbgolf/__init__.py`: currently minimal — the app factory lives here; this is where `db.init_app(app)` and `Migrate(app, db)` calls should be added
- `gbgolf/web/routes.py`: Flask Blueprint pattern — DB code should follow the same blueprint/app-factory separation

### Established Patterns
- Pydantic at boundary only, plain dataclasses internally — DB query results should return plain Python objects (dicts or dataclasses), not SQLAlchemy Row proxies leaked into business logic
- `python-dotenv` not yet installed — Phase 8 adds it; `DATABASE_URL` loaded via `os.environ` or `dotenv.load_dotenv()` in the app factory
- `pyproject.toml` is the dependency manifest — new deps (flask-sqlalchemy, flask-migrate, psycopg2-binary or psycopg[binary], python-dotenv) go here

### Integration Points
- App factory (`gbgolf/__init__.py`): add `db.init_app(app)`, `Migrate(app, db)`, and `app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]`
- `.env` file (new, git-ignored): `DATABASE_URL=postgresql://...` and `DATAGOLF_API_KEY=...`
- `.gitignore`: ensure `.env` is excluded; add `.env.example` as a committed template

</code_context>

<specifics>
## Specific Ideas

- No specific UI or interaction references — this is a pure infrastructure phase
- The two-table design (fetches + projections) is the key structural decision; Phase 9 must insert a `fetches` row first, then bulk-insert projections referencing that `fetch_id`

</specifics>

<deferred>
## Deferred Ideas

- Module organization (`gbgolf/db.py` vs `__init__.py`) — left to Claude's discretion; not discussed
- Testing approach for DB integration — left to Claude's discretion; not discussed
- v1.3 `user_id` column — explicitly deferred to a v1.3 Flask-Migrate migration

</deferred>

---

*Phase: 08-database-foundation*
*Context gathered: 2026-03-25*
