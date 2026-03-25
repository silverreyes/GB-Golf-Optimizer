# Pitfalls Research

**Domain:** Adding DataGolf API integration, PostgreSQL, and cron scheduling to an existing Flask DFS golf optimizer
**Researched:** 2026-03-25
**Confidence:** HIGH for cron/DB/API key pitfalls (well-documented failure modes); MEDIUM for DataGolf-specific behavior (API response format partially verified, off-week behavior unverified)

---

## Critical Pitfalls

### Pitfall 1: Cron Job Cannot See the DataGolf API Key

**What goes wrong:**
The cron fetcher script runs and immediately fails with a `KeyError` or `None` value when reading `os.environ["DATAGOLF_API_KEY"]`. The API key is set in `~/.bashrc` or in the systemd service unit for Gunicorn, but cron jobs do not inherit either of those environments. The script silently fails (cron swallows output by default), so no projections are fetched. The user discovers the problem days later when they notice stale data.

**Why it happens:**
Cron spawns a minimal shell with almost no environment variables. It does not source `~/.bashrc`, `~/.profile`, or `/etc/profile`. The Gunicorn systemd service has its own `Environment=` directives, but those apply only to the Gunicorn process, not to cron. Developers test the fetcher script manually from their interactive shell (where the env var is set) and assume it will work the same under cron.

**How to avoid:**
Store the API key in a dedicated env file and source it in the cron command:

```crontab
# /etc/cron.d/datagolf-fetch or user crontab
0 7 * * 2,3 . /opt/GBGolfOptimizer/.env && /opt/GBGolfOptimizer/venv/bin/python /opt/GBGolfOptimizer/fetch_projections.py >> /var/log/datagolf-fetch.log 2>&1
```

The `.env` file format:

```bash
export DATAGOLF_API_KEY="your-key-here"
```

Alternatively, define the variable directly in the crontab:

```crontab
DATAGOLF_API_KEY=your-key-here
0 7 * * 2,3 /opt/GBGolfOptimizer/venv/bin/python /opt/GBGolfOptimizer/fetch_projections.py >> /var/log/datagolf-fetch.log 2>&1
```

The `.env` file approach is better because the same file can be sourced by the systemd service via `EnvironmentFile=`, keeping the key in one place.

**Warning signs:**
- Projections table is empty or always stale
- `journalctl` and syslog show the cron job fired but there is no application log output
- Running the fetcher manually from SSH works fine

**Phase to address:**
Phase 1 (DataGolf fetcher + DB setup). The `.env` file and cron entry must be part of the same deployment step. Never deploy the fetcher script without verifying cron can see the API key.

---

### Pitfall 2: Cron Output Disappears Into the Void (Silent Failures)

**What goes wrong:**
The cron job runs the fetcher script, but stdout and stderr are not redirected. Cron attempts to email the output to the local user, but no MTA (mail transfer agent) is configured on the VPS. All output is discarded. When the DataGolf API returns an error, the script's error message is lost. The developer has no idea the fetcher has been failing for weeks.

**Why it happens:**
By default, cron captures stdout/stderr and tries to send it via local mail. Most VPS setups (including Hostinger KVM) do not have a working MTA configured. Without explicit output redirection in the crontab line, every `print()` and traceback is silently dropped.

**How to avoid:**
Always redirect both stdout and stderr to a log file in the crontab entry:

```crontab
0 7 * * 2,3 . /opt/GBGolfOptimizer/.env && /opt/GBGolfOptimizer/venv/bin/python /opt/GBGolfOptimizer/fetch_projections.py >> /var/log/datagolf-fetch.log 2>&1
```

Key details:
- Use `>>` (append), not `>` (overwrite), so logs accumulate across runs
- `2>&1` must come after the file redirect
- Add timestamps to log output inside the Python script (use `logging` module with a formatter, not bare `print()`)
- Set up log rotation with `logrotate` to prevent unbounded growth:

```
# /etc/logrotate.d/datagolf-fetch
/var/log/datagolf-fetch.log {
    weekly
    rotate 8
    compress
    missingok
    notifempty
}
```

**Warning signs:**
- No log file exists at the expected path
- Log file exists but has not been updated in days/weeks
- `grep CRON /var/log/syslog` shows the cron fired but there is no application output

**Phase to address:**
Phase 1 (cron setup). Logging and output redirection are part of the cron entry, not an afterthought.

---

### Pitfall 3: PostgreSQL Connection Shared Across Gunicorn Forked Workers

**What goes wrong:**
The Flask app creates a SQLAlchemy engine (or raw psycopg2 connection pool) at import time or during `create_app()`. Gunicorn then forks 2 worker processes. Both workers inherit the same file descriptors (TCP connections) to PostgreSQL. When both workers use these shared connections simultaneously, they corrupt each other's query streams. Symptoms: `psycopg2.OperationalError: SSL error: decryption failed or bad record mac`, or silently wrong query results, or intermittent connection resets.

**Why it happens:**
Gunicorn uses a pre-fork model: it imports the WSGI app (`wsgi:app`) in the master process, then forks workers. If the engine/pool is created during import, the pooled connections exist before the fork and are duplicated into each child. PostgreSQL TCP connections are not fork-safe.

**How to avoid:**
Use `pool_pre_ping=True` and ensure the engine is created inside the Flask app factory (which the current codebase already does via `create_app()`). With Gunicorn's default pre-fork behavior:

1. If using `--preload` (which pre-imports the app), add a Gunicorn `post_fork` hook that calls `engine.dispose()` in each worker:

```python
# gunicorn.conf.py
def post_fork(server, worker):
    from gbgolf.web import db_engine
    if db_engine:
        db_engine.dispose()
```

2. Better: do NOT use `--preload` (the current `gbgolf.service` does not use it). Each worker will call `create_app()` independently and get its own engine/pool. This is the simplest correct approach for 2 workers.

3. Set conservative pool sizes. With 2 Gunicorn workers and `pool_size=5` (default), you could open up to 10 connections to PostgreSQL. For a single-user app, `pool_size=2, max_overflow=3` per worker is more than sufficient.

4. Always enable `pool_pre_ping=True`:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=2,
    max_overflow=3,
    pool_pre_ping=True,
    pool_recycle=1800,  # recycle connections every 30 minutes
)
```

**Warning signs:**
- Intermittent `OperationalError` or `InterfaceError` in Gunicorn worker logs
- `pg_stat_activity` shows more connections than expected (2 workers x pool_size)
- Errors appear only under concurrent requests, never in single-request testing

**Phase to address:**
Phase 1 (PostgreSQL setup). Engine configuration must be correct from the first deployment. Testing with `gunicorn --workers 2` locally before deploying catches this.

---

### Pitfall 4: Player Name Mismatch Between DataGolf and GameBlazers Roster

**What goes wrong:**
DataGolf returns `player_name: "Ludvig Aberg"` (ASCII-ified). GameBlazers roster CSV has `Player: "Ludvig Aberg"` or possibly `"Ludvig Åberg"` (with diacritical). The existing `normalize_name()` in `matching.py` handles NFKD decomposition to strip combining marks, but the normalized forms must match across three sources: DataGolf API, GameBlazers CSV, and any manually uploaded projections CSV.

Additional name format risks:
- Suffixes: `"Davis Love III"` vs. `"Davis Love"` vs. `"Love III, Davis"`
- `"Si Woo Kim"` vs. `"S.W. Kim"` vs. `"Kim Si Woo"`
- `"Byeong Hun An"` vs. `"Ben An"`
- `"Min Woo Lee"` vs. `"Minwoo Lee"`
- Hyphens: `"Nicolai Hojgaard"` (DataGolf) vs. `"Nicolai Hoejgaard"` (some sources) vs. `"Nicolai Hojgaard"` (GameBlazers)
- Jr./Sr.: `"Harold Varner III"` with or without period

**Why it happens:**
Each data source has its own canonical name list. DataGolf uses DraftKings player names (since the endpoint is DraftKings-specific). GameBlazers has its own player database. There is no universal golf player ID shared across these platforms. The existing `normalize_name()` handles accents but not suffix variations or name order differences.

**How to avoid:**
1. Store the `dg_id` (DataGolf's numeric player identifier) alongside the player name when fetching projections. This is stable across weeks even if name formatting changes.

2. Build a name alias table for the 5-10 players whose names consistently differ between DataGolf and GameBlazers:

```python
# aliases.py — maps DataGolf name -> GameBlazers name (both normalized)
DATAGOLF_TO_GAMEBLAZERS = {
    "si woo kim": "si woo kim",  # verify actual formats
    "byeong hun an": "ben an",   # if GameBlazers uses nickname
    # Add as mismatches are discovered
}
```

3. Log every unmatched projection (the app already does this via `projection_warnings`). Review unmatched lists after each week's fetch to catch new mismatches.

4. Do NOT attempt fuzzy matching (Levenshtein, etc.) automatically. Golf has many players with similar names (e.g., "Tom Kim" vs. "Si Woo Kim"). Fuzzy matching will produce false positives. Use exact normalized match + explicit alias table.

**Warning signs:**
- `projection_warnings` list grows unexpectedly after switching to DataGolf source
- A well-known player shows `projected_score: None` despite being in the tournament field
- Unmatched player count is consistently higher with DataGolf than with manually uploaded CSV

**Phase to address:**
Phase 2 (projection matching integration). The alias table should be populated by running DataGolf projections against a real GameBlazers roster export and recording every mismatch in the first week of testing.

---

### Pitfall 5: "Current Week" Boundary Logic Errors

**What goes wrong:**
The cron fetches projections on Tuesday morning. The app labels them "current week." But the PGA Tour schedule has complications:
- **Monday finishes:** Some tournaments extend to Monday due to weather. Tuesday's fetch might contain projections for a tournament whose previous edition just ended on Monday.
- **Alternate events:** When two events run simultaneously (main tour + opposite field), the `tour=pga` parameter returns the main event, but the user might have cards for players in the opposite-field event (`tour=opp`).
- **Off-weeks:** During PGA Tour breaks (e.g., after The Masters, during the Olympics), the API may return projections for the next upcoming event or return no data at all. The app labels stale data as "current" because no new fetch replaced it.
- **Thursday-Sunday vs. Wednesday-Saturday events:** Some tournaments start on different days, shifting when "current week" projections become relevant.

**Why it happens:**
The concept of "current tournament week" is not a clean calendar boundary. Developers assume "this week's Tuesday = this week's tournament" but PGA Tour scheduling is irregular. DataGolf updates projections when tee times are released (typically Tuesday for Thursday-start events), but the timing varies.

**How to avoid:**
1. Store a `tournament_name` and `event_id` (if available from DataGolf response) alongside the fetch timestamp. Display the tournament name in the UI, not just a date.

2. Never infer "current week" from calendar arithmetic. Instead, check if the stored projections are for the same tournament the user is building lineups for. The simplest approach: show the tournament name from the projections and let the user confirm it matches their GameBlazers contest.

3. Handle the off-week case: if the DataGolf API returns an empty field or an HTTP error, do NOT overwrite the previous week's data. Log the failure and show a "No current projections available" message instead of silently serving stale data.

4. Include `fetch_timestamp` in the DB and display "Fetched X hours ago" in the UI. The staleness label (already planned in PROJECT.md) should use this timestamp, not a calendar comparison.

**Warning signs:**
- Projections show a tournament name that does not match the current GameBlazers contest
- During off-weeks, the staleness label says "5 days ago" but the app still offers to use the data
- User optimizes with projections from last week's tournament without realizing

**Phase to address:**
Phase 2 (projection source selector + staleness display). The tournament name must be stored in Phase 1 (DB schema), but the UI display and staleness logic belong in Phase 2.

---

### Pitfall 6: DataGolf API Key Exposed in Query String Logs

**What goes wrong:**
The DataGolf API requires the key as a query parameter (`?key=API_TOKEN`). If the fetcher script logs the full request URL (common with `requests` library debug logging or `httpx` trace logging), the API key appears in plaintext in log files. If Nginx access logs or Gunicorn logs capture outbound requests (unlikely but possible with custom middleware), the key leaks there too. If the key is committed to version control in a config file, it is permanently exposed in git history.

**Why it happens:**
DataGolf chose query-parameter authentication (simpler than headers but less secure). Developers logging request URLs for debugging inadvertently log the key. The `.env` file containing the key may be accidentally committed if `.gitignore` is not configured.

**How to avoid:**
1. Add `.env` to `.gitignore` immediately (before creating the file):

```gitignore
# API keys and secrets
.env
```

2. In the fetcher script, never log the full URL. Redact the key:

```python
import os
import requests

API_KEY = os.environ["DATAGOLF_API_KEY"]
url = "https://feeds.datagolf.com/preds/fantasy-projection-defaults"
params = {"tour": "pga", "site": "draftkings", "slate": "main", "key": API_KEY}

logger.info("Fetching projections from %s (key=redacted)", url)
response = requests.get(url, params=params)
```

3. Do not enable `requests` debug logging (`logging.getLogger("urllib3").setLevel(logging.DEBUG)`) in production. This logs full URLs including query parameters.

4. On the VPS, restrict `.env` file permissions: `chmod 600 /opt/GBGolfOptimizer/.env` and `chown deploy:deploy /opt/GBGolfOptimizer/.env`.

**Warning signs:**
- `.env` file appears in `git status` output
- Log files contain the string `key=` followed by the actual API token
- DataGolf rate limit is hit unexpectedly (possible key compromise)

**Phase to address:**
Phase 1 (initial setup). The `.gitignore` entry and file permissions are day-one tasks.

---

### Pitfall 7: Fetcher Overwrites Good Data When DataGolf API Fails

**What goes wrong:**
The cron fetcher runs, the DataGolf API returns a 500 error or an empty response (off-week, maintenance, rate limit). The fetcher script does `DELETE FROM projections WHERE source = 'datagolf'` before inserting new rows. The insert has nothing to insert (empty response). Result: the projections table is now empty. The Flask app shows "No projections available" even though valid projections from the previous successful fetch existed.

**Why it happens:**
The "delete then insert" pattern is common for simple data refreshes. It works when the insert always succeeds. But when the external API is unreliable, the delete removes data that the insert cannot replace.

**How to avoid:**
Use a transactional "fetch, validate, then replace" pattern:

```python
def fetch_and_store():
    response = requests.get(url, params=params)
    response.raise_for_status()  # raises on 4xx/5xx

    data = response.json()
    if not data:
        logger.warning("DataGolf returned empty response. Keeping existing data.")
        return

    # Validate: must have at least N players to be a real field
    if len(data) < 20:
        logger.warning("DataGolf returned only %d players. Likely incomplete. Keeping existing data.", len(data))
        return

    # Atomic replace within a transaction
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM projections WHERE source = 'datagolf'"))
        conn.execute(insert_stmt, new_rows)
    # If anything above raises, the transaction rolls back and old data is preserved
```

Key principles:
- Validate the API response BEFORE touching the database
- Wrap delete+insert in a single transaction so rollback preserves old data
- Set a minimum player count threshold (a real PGA field has 120-156 players; fewer than 20 is suspicious)
- On any failure, log the error and exit without modifying the database

**Warning signs:**
- Projections table is empty on a day when it should have data
- Log shows "fetched 0 projections" but no error was raised
- UI says "No projections available" despite a successful fetch earlier in the week

**Phase to address:**
Phase 1 (fetcher script implementation). The transactional replace pattern is the core of the fetcher logic.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Raw SQL strings instead of SQLAlchemy ORM models | No ORM learning curve; fewer files | Harder to add Flask-Migrate later; no model-driven migrations | Acceptable for v1.2 if schema is simple (1-2 tables). Revisit for v1.3 user accounts. |
| Single `.env` file for all secrets (API key + DB password + Flask secret) | One file to manage | All secrets exposed if file leaks; no separation of concerns | Acceptable for single-user VPS. Use distinct env vars per secret within the file. |
| No schema migration tool (just `CREATE TABLE IF NOT EXISTS` in fetcher) | Zero migration infrastructure | No way to track schema changes; risky for v1.3 when adding user tables | Acceptable for v1.2 initial deployment. Add Alembic before v1.3. |
| Cron instead of systemd timer | Familiar syntax; one line to add | No built-in dependency on PostgreSQL service; no automatic retry on failure | Acceptable for a twice-weekly fetch. Systemd timer is better but not worth the complexity for 2 runs/week. |
| Storing projections as flat rows (no normalization) | Simple queries; single table | Duplicate tournament metadata per row; slightly larger table | Acceptable forever at this scale (150 rows per fetch, 2 fetches per week). |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| DataGolf API key | Hardcoded in script or committed to git | Store in `.env`, load via `os.environ`, add `.env` to `.gitignore` before first commit |
| DataGolf API response parsing | Assuming field names without testing (e.g., `projected_points` vs. `proj_points` vs. `proj_fantasy_pts`) | Make one live API call during development and record the exact response schema. DataGolf docs do not provide a complete JSON example. |
| DataGolf rate limit (45/min) | Calling the API from both the cron fetcher and the Flask app on demand | Fetch via cron only; Flask reads from the database. Never call the API from a web request. |
| PostgreSQL on Ubuntu 24.04 | Default `peer` authentication blocks password-based connections from the app | Edit `pg_hba.conf`: change `local all all peer` to `local all gbgolf scram-sha-256` (or `md5`), then `sudo systemctl restart postgresql` |
| PostgreSQL connection string | Using `localhost` in the connection string, which attempts TCP | For local Unix socket connection, use `postgresql://user:pass@/dbname`. For TCP (which `pg_hba.conf` `host` rules govern), use `postgresql://user:pass@127.0.0.1/dbname`. These are different `pg_hba.conf` rules. |
| Cron `PATH` | Script uses `python` but cron's `PATH` is `/usr/bin:/bin` — no venv | Always use the absolute venv Python path: `/opt/GBGolfOptimizer/venv/bin/python` |
| Cron timezone | Server set to UTC but developer expects Eastern time for "Tuesday morning" | Verify with `timedatectl` on the VPS. Convert desired local time to server timezone for the cron schedule. Or set `TZ=America/New_York` in the crontab (but test this on Ubuntu 24.04 — `CRON_TZ` has had compatibility issues). |
| Flask app reading DB | Creating a new engine per request instead of using the app-level engine | Create the engine once in `create_app()`, store on `app.config` or as a module-level singleton. Use `pool_pre_ping=True`. |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Opening a new DB connection per request (no pooling) | 200-500ms latency added per request; PostgreSQL `max_connections` exhausted | Use SQLAlchemy engine with connection pool (default behavior) | At 10+ concurrent requests; unlikely for single-user but still bad practice |
| Fetcher script holds DB connection open during API call | Connection idle for 2-5 seconds during HTTP request; blocks pool | Fetch data first, close HTTP, then open DB connection and insert | Never a real problem at this scale, but good hygiene |
| Loading all historical projections when only current week is needed | Query returns thousands of rows; slow page load | Always filter by `tournament_name` or `fetch_date >= threshold` in the SQL query | At 50+ weeks of historical data (~7,500 rows) |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| DataGolf API key in git history | Key compromised; anyone with repo access can use the API quota | `.gitignore` `.env` before creating it. If accidentally committed, rotate the key on DataGolf immediately and use `git filter-branch` or `BFG Repo-Cleaner` to purge history. |
| PostgreSQL password in `DATABASE_URL` committed to source | Database compromised if repo is public or shared | Same `.env` pattern: `DATABASE_URL=postgresql://user:pass@127.0.0.1/dbname` in `.env`, loaded via `os.environ` in `create_app()` |
| `.env` file readable by all users on VPS | Any process/user on the server can read secrets | `chmod 600 .env` and `chown deploy:deploy .env` immediately after creation |
| Cron log file contains API key (logged in URL) | Key exposure via log file access | Never log the full request URL. Redact the key parameter in all log output. |
| No input validation on DataGolf API response before DB insert | SQL injection if DataGolf response is somehow tampered (extremely unlikely but defensive) | Use parameterized queries (SQLAlchemy `text()` with `:param` syntax or ORM insert). Never use f-strings or string formatting for SQL. |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No indication of which tournament the projections are for | User optimizes with projections from last week's tournament | Display tournament name prominently: "Projections: The Masters (fetched 3 hours ago)" |
| Staleness label shows date only, not age | "Fetched 2026-03-18" means nothing without context; user must do mental math | Show relative age: "Fetched 2 days ago" alongside the absolute date |
| DataGolf source selected but no data available — blank results | User thinks the app is broken | Show an explicit message: "No DataGolf projections available for this week. Upload a CSV or check back Tuesday." |
| Projection source selector resets on page reload | User selects DataGolf, optimizes, reloads page, source resets to default | Store the last-used source in Flask session. Pre-select it on next visit. |
| Switching projection source requires re-uploading roster | User already uploaded roster, switches from CSV to DataGolf, app demands roster again | Roster should persist in session (already does via `card_pool_json`). Switching projection source re-matches against the existing roster card pool. |

---

## "Looks Done But Isn't" Checklist

- [ ] **Cron environment:** Run the fetcher script via cron at least once on the VPS and verify the log file shows a successful fetch with data. Do not rely on manual SSH execution as proof.
- [ ] **PostgreSQL auth:** Connect to the database from the Flask app using the same user/password as the fetcher script. Test both `create_app()` startup and an actual query. Peer auth will silently fail for non-matching Linux users.
- [ ] **Off-week behavior:** Manually test what the DataGolf API returns when no event is active. Does it return 200 with an empty array? 404? 200 with last week's data? The fetcher must handle all three cases without corrupting stored data.
- [ ] **Player name matching end-to-end:** Run DataGolf projections through `normalize_name()` and compare against a real GameBlazers roster export. Count unmatched players. If more than 2-3 are unmatched, investigate name format differences.
- [ ] **Connection pool under Gunicorn:** Start the app with `gunicorn --workers 2` and make 10 rapid requests. Check `pg_stat_activity` for connection count. It should be <= `2 * pool_size`, not growing unboundedly.
- [ ] **Log rotation:** Verify `/etc/logrotate.d/datagolf-fetch` exists and works. Without it, the log file grows forever on a VPS with limited disk.
- [ ] **Stale data label:** Wait until projections are 3+ days old and verify the UI shows a staleness warning, not a "current" label.
- [ ] **Transaction rollback:** Kill the fetcher script mid-execution (Ctrl+C during insert). Verify the projections table still has the previous valid data, not a partial or empty state.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| API key committed to git | MEDIUM | Rotate key on DataGolf dashboard. Purge from git history with `BFG Repo-Cleaner`. Update `.env` on VPS. |
| Cron silently failing for weeks | LOW | Check `/var/log/datagolf-fetch.log`. Fix the issue (usually missing env var or wrong Python path). Run fetcher manually to backfill. |
| Projections table emptied by bad fetch | LOW | If using transactions: automatic rollback means data was never lost. If not: re-run fetcher manually or upload CSV as fallback. |
| PostgreSQL connection exhaustion | LOW | Restart Gunicorn (`sudo systemctl restart gbgolf`). Fix pool configuration. Connections are released on process exit. |
| Player name mismatches discovered post-deploy | LOW | Add entries to alias table. Re-run matching against stored projections. No data re-fetch needed. |
| Wrong timezone in cron schedule | LOW | Edit crontab, fix the hour. Run fetcher manually to catch up for the missed window. |
| Schema needs to change after initial deployment | MEDIUM | If no migration tool: write a manual `ALTER TABLE` script. If using Alembic: generate migration. Either way, back up the database first with `pg_dump`. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Cron cannot see API key | Phase 1: Fetcher + cron setup | Run `sudo -u deploy crontab -l` to verify entry, then check log after next scheduled run |
| Silent cron failures (no logging) | Phase 1: Cron setup | Verify log file exists and contains timestamped output after first cron execution |
| Connection pool shared across forked workers | Phase 1: PostgreSQL + engine setup | `gunicorn --workers 2`, query `pg_stat_activity`, confirm connection count is bounded |
| Player name mismatches | Phase 2: Projection matching integration | Run DataGolf data through `normalize_name()` + match against real roster, count unmatched |
| "Current week" boundary errors | Phase 2: Staleness display + source selector | Test during off-week and on Monday (post-tournament) to verify correct labels |
| API key in logs or git | Phase 1: Initial `.env` setup | `grep -r "key=" /var/log/datagolf-fetch.log` returns nothing; `.env` not in `git ls-files` |
| Fetcher overwrites good data on API failure | Phase 1: Fetcher script | Simulate API failure (wrong key or network disconnect), verify DB retains previous data |
| PostgreSQL peer auth blocks app connection | Phase 1: PostgreSQL setup | Flask app starts without `FATAL: Peer authentication failed` in Gunicorn logs |
| No schema migration path for v1.3 | Phase 1: DB schema design | Schema uses `CREATE TABLE IF NOT EXISTS` with columns designed for future expansion; document the schema for Alembic adoption in v1.3 |

---

## Sources

### HIGH confidence
- [Crontab environment variables](https://cronitor.io/guides/cron-environment-variables) -- cron does not inherit interactive shell environment
- [SQLAlchemy 2.0 Connection Pooling docs](https://docs.sqlalchemy.org/en/20/core/pooling.html) -- `pool_pre_ping`, `pool_size`, forking behavior, `engine.dispose()` in post_fork
- [Handling Timezone Issues in Cron Jobs (2025)](https://dev.to/cronmonitor/handling-timezone-issues-in-cron-jobs-2025-guide-52ii) -- `CRON_TZ` compatibility issues, DST pitfalls
- [Install and configure PostgreSQL on Ubuntu](https://documentation.ubuntu.com/server/how-to/databases/install-postgresql/) -- default peer auth, `pg_hba.conf` configuration
- [DataGolf API Access docs](https://datagolf.com/api-access) -- key as query parameter, 45 req/min rate limit, `fantasy-projection-defaults` endpoint parameters
- [PSA: API Rate Limits (DataGolf Forum)](https://forum.datagolf.com/t/psa-api-rate-limits/2511) -- rate limit enforcement details
- Existing codebase: `gbgolf/data/matching.py` `normalize_name()` -- current name normalization logic (NFKD + combining mark removal)
- Existing codebase: `deploy/gbgolf.service` -- Gunicorn worker count (2), no `--preload` flag
- Existing codebase: `gbgolf/web/__init__.py` -- `create_app()` factory pattern, no DB engine currently

### MEDIUM confidence
- [SQLAlchemy connection pool within multiple threads and processes](https://davidcaron.dev/sqlalchemy-multiple-threads-and-processes/) -- practical Gunicorn + SQLAlchemy patterns
- [How to Add Flask-Migrate to an Existing Project](https://blog.miguelgrinberg.com/post/how-to-add-flask-migrate-to-an-existing-project) -- migration bootstrapping for existing apps
- [DataGolf FAQ](https://datagolf.com/frequently-asked-questions) -- projection update timing (re-run when tee times released, typically Tuesday)
- [Ubuntu cron logs guide](https://last9.io/blog/ubuntu-cron-logs/) -- syslog cron logging, output redirection patterns

### LOW confidence (needs live verification)
- DataGolf API response field names: documentation confirms `player_name` field exists but complete JSON structure requires a live API call to verify
- DataGolf off-week behavior: no documentation found on what the API returns when no event is active; must be tested empirically
- GameBlazers player name format: no public documentation; must be compared against actual roster export

---
*Pitfalls research for: Adding DataGolf API, PostgreSQL, and cron to GB Golf Optimizer*
*Researched: 2026-03-25*
