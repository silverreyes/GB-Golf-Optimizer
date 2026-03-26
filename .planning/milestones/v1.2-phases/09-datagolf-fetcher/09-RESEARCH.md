# Phase 9: DataGolf Fetcher - Research

**Researched:** 2026-03-25
**Domain:** HTTP API integration, Flask CLI commands, database upsert patterns
**Confidence:** HIGH

## Summary

Phase 9 builds a Flask CLI command (`flask fetch-projections`) that calls the DataGolf `fantasy-projection-defaults` API endpoint, validates and normalizes the response, and writes it to the existing `fetches` + `projections` tables using an atomic DELETE-then-INSERT pattern. A system cron job triggers this command on Tuesday and Wednesday mornings.

The technical implementation is straightforward: httpx for the HTTP call, Pydantic v2 for response boundary validation, `parse_datagolf_name()` for "Last, First" to "First Last" conversion (chained with the existing `normalize_name()` NFKD pipeline), and raw SQL via `db.session.execute(text(...))` for database writes. The main uncertainty is the exact DataGolf API response field names, which cannot be determined from public documentation and require a live discovery call at phase start.

**Primary recommendation:** Structure the implementation as: (1) live API discovery call to log raw response and finalize field names, (2) Pydantic boundary model + `parse_datagolf_name()`, (3) atomic DB write with DELETE CASCADE + batch INSERT, (4) Flask CLI command wiring, (5) cron documentation. The fetcher module should live at `gbgolf/fetcher.py`, separate from the web layer.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Minimum viable player count threshold: **30 players** -- fewer than 30 = failure, exit 0, preserve existing data
- Log file at `logs/fetch.log` -- one-liner per fetch, human-readable, no rotation
- Log format: `2026-03-25 08:01:22 UTC | OK | Masters Tournament | 89 players | fetch_id=42`
- Error format: `2026-03-25 08:01:22 UTC | ERROR | <reason> | existing data preserved`
- Cron: Tuesday and Wednesday at 8:00 AM Eastern -- `0 13 * * 2,3` (winter) or `0 12 * * 2,3` (summer)
- Phase 11 deployment verifies VPS timezone and sets correct UTC offset
- httpx for all DataGolf API calls with timeout as first-class parameter
- `DATAGOLF_API_KEY` from `.env` via python-dotenv
- `parse_datagolf_name()` converts "Last, First" to "First Last", then existing `normalize_name()` NFKD pipeline
- DB write: INSERT `fetches` row, capture `fetch_id`, bulk-INSERT `projections` -- replace stale data via DELETE FROM fetches WHERE tournament_name + tour (CASCADE deletes projections)
- SQLAlchemy Core `text()` queries only -- no ORM
- API field discovery via live call at phase start -- log full raw JSON, finalize Pydantic model from actual field names
- `logs/` directory must be in `.gitignore`

### Claude's Discretion
- Exact Pydantic model field names (determined from live API discovery call)
- Transaction boundary -- whether DELETE + INSERT is wrapped in a single DB transaction
- How `flask fetch-projections` reports success to stdout when run manually
- Whether to create `gbgolf/fetcher.py` or put logic in `gbgolf/web/routes.py` (fetcher.py recommended)

### Deferred Ideas (OUT OF SCOPE)
- Manual projection refresh from UI (MGMT-01) -- future milestone
- Fetch status dashboard in UI (MGMT-02) -- future milestone
- Logrotate.d for `logs/fetch.log` -- too small to need rotation now
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FETCH-01 | System fetches player projections from DataGolf `fantasy-projection-defaults` API (PGA Tour, DraftKings scoring, main slate) and writes them to PostgreSQL | httpx client pattern, API endpoint URL/params, Pydantic boundary model, DB write pattern with text() queries |
| FETCH-02 | Cron job on VPS triggers fetcher on Tuesday and Wednesday mornings | Flask CLI command registration via `@app.cli.command()`, crontab line format, FLASK_APP env var |
| FETCH-03 | Fetch activity logged to file (player count, tournament name, timestamp, errors) | Python file-append logging pattern, `logs/fetch.log` format |
| FETCH-04 | Existing projections preserved if API error or fewer than 30 players | Guard-before-write pattern: validate response count before any DB mutation |
| FETCH-06 | DataGolf "Last, First" names normalized to "First Last" before storage | `parse_datagolf_name()` + existing `normalize_name()` from `gbgolf/data/matching.py` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | HTTP client for DataGolf API | Locked decision; sync API, timeout as first-class param, no C deps |
| pydantic | 2.12.5 | API response boundary validation | Already installed; project pattern is Pydantic at boundary only |
| flask | 3.x | CLI command framework (`@app.cli.command()`) | Already installed; CLI commands get app context automatically |
| flask-sqlalchemy | 3.1+ | Database access via `db.session` | Already installed; Phase 8 foundation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.0+ | Load DATAGOLF_API_KEY from .env | Already installed and wired in app factory |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | httpx already decided; timeout API is cleaner than requests |
| Raw file logging | Python `logging` module | One-liner append is simpler for this use case; `logging` adds unnecessary config |
| Pydantic model | Manual dict access | Pydantic catches field drift/type errors at the boundary; worth the 5 lines |

**Installation:**
```bash
pip install httpx>=0.28
```

httpx is the only new dependency. All others are already in `pyproject.toml`.

**Version verification:**
- httpx: 0.28.1 (latest on PyPI as of 2024-12-06, confirmed via web search)
- pydantic: 2.12.5 (already installed locally)
- flask: 3.x (already installed)
- flask-sqlalchemy: 3.1+ (already installed)

## Architecture Patterns

### Recommended Project Structure
```
gbgolf/
  fetcher.py          # NEW: fetch logic, parse_datagolf_name(), write_projections()
  db.py               # Existing: fetches + projections table definitions
  data/
    matching.py        # Existing: normalize_name() reused by fetcher
  web/
    __init__.py        # Existing: app factory -- register CLI command here
logs/
  fetch.log            # NEW: fetch activity log (git-ignored)
tests/
  test_fetcher.py      # NEW: unit tests for fetcher module
```

### Pattern 1: Boundary Validation with Pydantic
**What:** Parse the raw DataGolf JSON response through a Pydantic model at the HTTP boundary, then convert to plain dicts for DB insertion.
**When to use:** Immediately after receiving the API response, before any business logic.
**Example:**
```python
# Source: Existing project pattern in gbgolf/data/config.py
from pydantic import BaseModel

class _DataGolfPlayer(BaseModel):
    """Field names TBD from live API discovery call."""
    player_name: str       # Confirmed: DataGolf uses "player_name" field
    # projected_score field name unknown -- could be fantasy_points, proj_points, etc.
    # salary, ownership, dg_id -- available but not needed for v1.2

class _DataGolfResponse(BaseModel):
    """Top-level response -- structure TBD from live discovery."""
    # Likely a list of player objects, possibly with event metadata
    pass
```

### Pattern 2: Atomic DB Write (DELETE + INSERT in Transaction)
**What:** Delete stale data for the same tournament/tour, then insert fresh batch, all in one transaction.
**When to use:** Every fetch operation.
**Example:**
```python
# Source: Established project pattern from tests/test_db.py
from sqlalchemy import text
from datetime import datetime, UTC

def write_projections(session, tournament_name: str, tour: str, players: list[dict]) -> int:
    """Atomic upsert: delete old data for this tournament, insert fresh batch."""
    # DELETE cascades to projections via FK
    session.execute(
        text("DELETE FROM fetches WHERE tournament_name = :tn AND tour = :tour"),
        {"tn": tournament_name, "tour": tour},
    )
    # INSERT new fetch row
    result = session.execute(
        text("""INSERT INTO fetches (tournament_name, fetched_at, player_count, source, tour)
                VALUES (:tn, :fa, :pc, :src, :tour) RETURNING id"""),
        {"tn": tournament_name, "fa": datetime.now(UTC), "pc": len(players),
         "src": "datagolf", "tour": tour},
    )
    fetch_id = result.scalar_one()
    # Bulk INSERT projections
    for p in players:
        session.execute(
            text("""INSERT INTO projections (fetch_id, player_name, projected_score)
                    VALUES (:fid, :pn, :ps)"""),
            {"fid": fetch_id, "pn": p["player_name"], "ps": p["projected_score"]},
        )
    session.commit()
    return fetch_id
```

**Note on RETURNING clause:** SQLite (used in tests) supports `RETURNING` since version 3.35.0 (2021-03-12). Python 3.11 ships with SQLite 3.39+, so this works in both test (SQLite) and production (PostgreSQL) environments.

### Pattern 3: Flask CLI Command with App Context
**What:** Register a CLI command via `@app.cli.command()` that automatically gets Flask app context (database connection, config, etc.).
**When to use:** For the `flask fetch-projections` command.
**Example:**
```python
# Source: Flask official docs - CLI commands
import click

# In app factory (gbgolf/web/__init__.py):
@app.cli.command("fetch-projections")
def fetch_projections_cmd():
    """Fetch player projections from DataGolf API."""
    from gbgolf.fetcher import run_fetch
    result = run_fetch()
    click.echo(result.summary)
```

### Pattern 4: Name Normalization Pipeline
**What:** Two-stage normalization: `parse_datagolf_name()` handles format conversion, then `normalize_name()` handles Unicode/case normalization.
**When to use:** Before storing any player name from DataGolf.
**Example:**
```python
from gbgolf.data.matching import normalize_name

def parse_datagolf_name(raw: str) -> str:
    """Convert 'Last, First' to 'First Last'. Pass through if no comma."""
    if "," in raw:
        parts = raw.split(",", 1)
        return f"{parts[1].strip()} {parts[0].strip()}"
    return raw.strip()

# Usage in fetcher pipeline:
display_name = parse_datagolf_name(api_player["player_name"])  # "Scheffler, Scottie" -> "Scottie Scheffler"
# For DB storage, store the display name (First Last format)
# For matching against roster, use normalize_name(display_name) which lowercases + NFKD
```

### Anti-Patterns to Avoid
- **Deleting projections before validating the API response:** Always validate player count >= 30 BEFORE any DB mutation. The guard must run on the parsed response, not after writing.
- **Using ORM models:** This project uses SQLAlchemy Core with `text()` queries exclusively. Do not introduce ORM patterns.
- **Importing fetcher logic in routes.py:** Keep fetch logic in `gbgolf/fetcher.py`, not in the web blueprint. The CLI command is registered in the app factory, calling into the fetcher module.
- **Using Python's `logging` module for fetch.log:** The spec calls for a simple one-liner append to a flat file. Python's logging module adds unnecessary complexity (handlers, formatters, log levels) for what is essentially `file.write(line + "\n")`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP requests with timeouts | urllib/socket code | httpx with `timeout=` param | Connection pooling, proper timeout handling, clean API |
| JSON response validation | Manual dict key checking | Pydantic BaseModel | Type coercion, missing field detection, clear error messages |
| Unicode name normalization | Custom accent stripping | Existing `normalize_name()` with NFKD | Already tested, handles edge cases (Aberg, Hojgaard) |
| Database migrations | Manual ALTER TABLE | Flask-Migrate (already set up) | Schema versioning, rollback capability |
| Environment variable loading | Manual os.environ | python-dotenv (already wired) | `.env` file support, consistent with existing codebase |

**Key insight:** Nearly all infrastructure for this phase already exists from Phase 8. The new code is: httpx call + Pydantic model + `parse_datagolf_name()` + DB write function + CLI command registration + log file append. No new infrastructure.

## Common Pitfalls

### Pitfall 1: Deleting Data Before Validating the New Batch
**What goes wrong:** If you DELETE existing projections first, then the API call fails or returns < 30 players, you've destroyed good data with nothing to replace it.
**Why it happens:** Natural code flow is "clear old data, fetch new data, insert." But the guard must come first.
**How to avoid:** Fetch and validate the full API response BEFORE touching the database. Only proceed to DELETE + INSERT if the response passes all guards (HTTP 200, valid JSON, >= 30 players).
**Warning signs:** Any DB write statement appearing before the API response validation.

### Pitfall 2: SQLite RETURNING Clause in Tests
**What goes wrong:** Older SQLite versions don't support `RETURNING id`. Tests would fail with syntax error.
**Why it happens:** SQLite added RETURNING in 3.35.0 (March 2021).
**How to avoid:** Python 3.11 ships with SQLite 3.39+, so this is safe. If any test environment uses Python < 3.10, use a fallback: `INSERT` then `SELECT last_insert_rowid()`.
**Warning signs:** `OperationalError: near "RETURNING": syntax error` in test output.

### Pitfall 3: Name Format Assumptions
**What goes wrong:** Assuming ALL DataGolf names follow "Last, First" format. Some names may have suffixes ("Jr.", "III") or no comma at all.
**Why it happens:** Not all name formats are documented.
**How to avoid:** `parse_datagolf_name()` should handle: (a) "Last, First" standard case, (b) "Last Jr., First" with suffix, (c) no comma = pass through unchanged. The live discovery call will reveal actual formats.
**Warning signs:** Names stored as "Scheffler, Scottie" (unnormalized) or "Jr. Scottie" (bad split).

### Pitfall 4: Forgetting to Enable FK Constraints in SQLite Tests
**What goes wrong:** CASCADE delete doesn't work in SQLite tests because foreign key enforcement is off by default.
**Why it happens:** SQLite requires `PRAGMA foreign_keys = ON` per connection.
**How to avoid:** Either (a) enable FK pragma in test setup, or (b) test CASCADE behavior separately (already done in `test_db.py::test_cascade_delete`).
**Warning signs:** DELETE from fetches succeeds but orphaned projection rows remain.

### Pitfall 5: Cron Environment Missing FLASK_APP
**What goes wrong:** `flask fetch-projections` fails on the VPS because cron doesn't load the user's shell environment.
**Why it happens:** Cron jobs run in a minimal environment. `FLASK_APP` and `DATAGOLF_API_KEY` won't be set.
**How to avoid:** Cron entry must either: (a) source the `.env` file before running flask, or (b) set env vars inline in the crontab. Phase 11 handles the actual crontab setup, but Phase 9 must document the required environment.
**Warning signs:** `Error: Could not locate a Flask application` when cron fires.

### Pitfall 6: httpx Default Timeout of 5 Seconds
**What goes wrong:** DataGolf API may be slow under load; the default 5-second timeout triggers a `TimeoutException`.
**Why it happens:** httpx defaults to 5 seconds for all timeout types.
**How to avoid:** Set an explicit timeout (e.g., `timeout=30.0`) on the httpx client or request. The CONTEXT.md says "timeout configured as a first-class parameter."
**Warning signs:** Intermittent `httpx.TimeoutException` errors in fetch.log.

## Code Examples

Verified patterns from official sources and existing codebase:

### httpx Synchronous GET with Timeout
```python
# Source: https://www.python-httpx.org/quickstart/
import httpx

response = httpx.get(
    "https://feeds.datagolf.com/preds/fantasy-projection-defaults",
    params={
        "tour": "pga",
        "site": "draftkings",
        "slate": "main",
        "file_format": "json",
        "key": api_key,
    },
    timeout=30.0,
)
response.raise_for_status()  # Raises httpx.HTTPStatusError for 4xx/5xx
data = response.json()
```

### Flask CLI Command Registration in App Factory
```python
# Source: Flask docs - https://flask.palletsprojects.com/en/stable/cli/
# In gbgolf/web/__init__.py, inside create_app():
import click

@app.cli.command("fetch-projections")
def fetch_projections_cmd():
    """Fetch player projections from DataGolf and store in database."""
    from gbgolf.fetcher import run_fetch
    result = run_fetch()
    click.echo(result)
```

### File-Based Fetch Logging
```python
# Simple append to log file -- no logging module needed
import os
from datetime import datetime, UTC

def write_fetch_log(log_dir: str, line: str) -> None:
    """Append one line to logs/fetch.log. Creates directory if needed."""
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "fetch.log")
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {line}\n")
```

### Pydantic Boundary Model (Template -- Field Names TBD)
```python
# Source: Existing pattern in gbgolf/data/config.py
from pydantic import BaseModel

class _DataGolfPlayerProjection(BaseModel):
    """Validate one player record from DataGolf API response.

    IMPORTANT: Field names below are HYPOTHETICAL.
    Must be finalized from live API discovery call.
    DataGolf uses snake_case convention (confirmed from raw-data-notes).
    """
    player_name: str       # Confirmed field name from DataGolf docs
    dg_id: int             # Confirmed field name from DataGolf docs
    # The projected fantasy points field name is UNKNOWN -- possibilities:
    #   fantasy_points, proj_points, proj_fantasy_points, fantasy_points_proj
    # salary and ownership fields exist but are not needed for v1.2
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| requests library | httpx | 2023+ | Better timeout API, HTTP/2 support, no C deps |
| Pydantic v1 | Pydantic v2 (2.12.5) | 2023-06 | `model_validate()` replaces `parse_obj()`, faster validation |
| `with_appcontext` decorator | Automatic with `@app.cli.command()` | Flask 2.0+ | No need to manually wrap CLI commands |

**Deprecated/outdated:**
- `flask.cli.with_appcontext`: Still works but unnecessary when using `@app.cli.command()` -- app context is automatic
- Pydantic v1 `parse_obj()`: Replaced by `model_validate()` in v2

## Open Questions

1. **DataGolf API Response Field Names**
   - What we know: The API uses snake_case field names. `player_name` and `dg_id` are confirmed field names across DataGolf endpoints. The response contains projected fantasy points, salary, ownership, and other DFS-relevant fields.
   - What's unclear: The exact field name for the projected fantasy points score (could be `fantasy_points`, `proj_points`, `proj_fantasy_points`, or something else). Also unclear whether the response is a flat list of player objects or a nested structure with event metadata (tournament name).
   - Recommendation: **Live discovery call is mandatory.** Make one GET request with a valid API key, log the full raw JSON response, then finalize the Pydantic model. This is already flagged in the ROADMAP and CONTEXT.md as a phase-start task.
   - Confidence: LOW on exact field names -- must be resolved from live data

2. **Tournament Name Source**
   - What we know: The `fetches` table requires `tournament_name`. The fantasy projections web page shows the tournament name.
   - What's unclear: Whether the API response JSON includes the tournament/event name as a top-level field or whether it must be inferred from a separate endpoint (e.g., `/field-updates` which has `event_name`).
   - Recommendation: Check the live discovery response for an event/tournament name field. If absent, consider calling `/field-updates` as a secondary source, or extracting from the CSV format's header if the JSON structure omits it.
   - Confidence: MEDIUM -- DataGolf likely includes event context, but unconfirmed

3. **RETURNING Clause Cross-DB Compatibility**
   - What we know: PostgreSQL fully supports `RETURNING`. SQLite supports it since 3.35.0. Python 3.11 ships with SQLite 3.39+.
   - What's unclear: Whether the exact SQLAlchemy `text()` + `RETURNING` pattern works identically in both backends through Flask-SQLAlchemy.
   - Recommendation: Use `RETURNING id` in the INSERT statement. If SQLite test issues arise, fall back to `SELECT last_insert_rowid()`. Test this early.
   - Confidence: HIGH -- both backends support it at the current Python version

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ (already configured) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `pytest tests/test_fetcher.py -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FETCH-01 | Fetcher calls API and writes projections to DB | unit (mocked httpx) | `pytest tests/test_fetcher.py::test_fetch_writes_to_db -x` | Wave 0 |
| FETCH-02 | CLI command `flask fetch-projections` is registered and callable | unit | `pytest tests/test_fetcher.py::test_cli_command_registered -x` | Wave 0 |
| FETCH-03 | Fetch activity written to log file | unit | `pytest tests/test_fetcher.py::test_fetch_log_written -x` | Wave 0 |
| FETCH-04 | Guard: < 30 players preserves existing data | unit | `pytest tests/test_fetcher.py::test_low_count_preserves_data -x` | Wave 0 |
| FETCH-04 | Guard: API error preserves existing data | unit | `pytest tests/test_fetcher.py::test_api_error_preserves_data -x` | Wave 0 |
| FETCH-06 | "Last, First" normalized to "First Last" | unit | `pytest tests/test_fetcher.py::test_parse_datagolf_name -x` | Wave 0 |
| FETCH-06 | Edge cases: suffixes, no comma, accented names | unit | `pytest tests/test_fetcher.py::test_name_edge_cases -x` | Wave 0 |
| -- | Idempotent fetch (run twice = same result, no duplicates) | unit | `pytest tests/test_fetcher.py::test_idempotent_fetch -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_fetcher.py -x -q`
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_fetcher.py` -- covers FETCH-01, FETCH-02, FETCH-03, FETCH-04, FETCH-06
- [ ] httpx dependency in `pyproject.toml` -- `httpx>=0.28`
- [ ] `logs/` added to `.gitignore`

## Sources

### Primary (HIGH confidence)
- DataGolf API docs (https://datagolf.com/api-access) -- endpoint URL, parameters, authentication method
- DataGolf raw data notes (https://datagolf.com/raw-data-notes) -- snake_case field convention, `player_name` and `dg_id` confirmed field names
- httpx official docs (https://www.python-httpx.org/advanced/timeouts/) -- timeout configuration, exception handling
- Flask CLI docs (https://flask.palletsprojects.com/en/stable/appcontext/) -- `@app.cli.command()` automatic app context
- Existing codebase: `gbgolf/data/config.py` -- Pydantic boundary validation pattern
- Existing codebase: `gbgolf/data/matching.py` -- `normalize_name()` function signature and behavior
- Existing codebase: `gbgolf/db.py` -- `fetches` and `projections` table schemas
- Existing codebase: `tests/test_db.py` -- SQLAlchemy Core `text()` query patterns, cascade delete test

### Secondary (MEDIUM confidence)
- DataGolf fantasy projections page (https://datagolf.com/fantasy-projections) -- visible column headers suggest projected points, salary, ownership fields exist in API
- Unofficial Python wrapper (https://github.com/coreyjs/data-golf-api) -- confirms endpoint path `/preds/fantasy-projection-defaults`, parameter names

### Tertiary (LOW confidence)
- Exact API response field names for projected fantasy points score -- NOT confirmed from any public source; must be resolved via live discovery call
- Tournament name field in API response -- likely present but unconfirmed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries are already installed or decided; httpx version confirmed
- Architecture: HIGH -- follows established project patterns exactly (Pydantic boundary, text() queries, app factory CLI)
- Pitfalls: HIGH -- common patterns well documented; cron/env pitfalls are standard DevOps knowledge
- API field names: LOW -- requires live discovery call; no public documentation available

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable domain; DataGolf API is versioned and unlikely to change field names)
