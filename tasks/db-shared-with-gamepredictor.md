# Backlog: GBGolf shares its Postgres with the GamePredictor stack

## Context

GBGolf's production `DATABASE_URL` (in `/opt/GBGolfOptimizer/.env` on the VPS) points at:

```
postgresql://gbgolf:***@172.18.0.2:5432/gbgolf
```

`172.18.0.2` is an IP inside the **`gamepredictor_default`** Docker network (confirmed via `docker network inspect`). The `gbgolf` user and `gbgolf` database live inside the `gamepredictor-postgres-1` container — i.e., GBGolf's data is hosted by GamePredictor's Postgres, even though the two projects are otherwise unrelated.

**This was not intentional design** — GBGolf was set up at some past point against an existing Postgres instance that happened to be GamePredictor's. The coupling has been silently in place ever since.

## How it surfaced

Discovered 2026-05-06 when the GBGolf home page started returning a 500. Traceback in `journalctl -u gbgolf.service`:

```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError)
  connection to server at "172.18.0.2", port 5432 failed: No route to host
  Is the server running on that host and accepting TCP/IP connections?
```

Cause: `gamepredictor-postgres-1` exited 6 days prior (Apr 30 ~16:22 UTC) along with the rest of the GamePredictor stack. With its host down, GBGolf's Postgres connection failed at request time.

Immediate workaround: restart `gamepredictor-postgres-1`. Restores GBGolf, but re-couples it to GamePredictor's lifecycle — same outage will recur the next time GamePredictor is brought down.

## Why this needs to be fixed

1. **Lifecycle coupling.** GBGolf goes down whenever GamePredictor does, for reasons unrelated to GBGolf's code or infrastructure.
2. **Confusing ownership.** VPS_STATE.md (§3, §4, §5) lists no GBGolf containers, networks, or volumes. Anyone reading the doc would conclude GBGolf has no Postgres, when in fact it has one inside someone else's stack.
3. **Hardcoded container IP.** Docker bridge IPs are not stable across `docker-compose down/up`, even within the same stack. Using `172.18.0.2` directly (rather than a hostname like `postgres` inside a shared compose) is fragile by design.
4. **Backup boundary unclear.** A backup of GamePredictor's volume (`gamepredictor_pgdata`) is also implicitly a backup of GBGolf data, but neither project's docs say so. Restoring either project from backup risks clobbering the other.

## Fix options

Three viable paths, in increasing order of effort:

### Option A — Stand up a dedicated `gbgolf-postgres` container (recommended)

Add a `docker-compose.yml` to `/opt/GBGolfOptimizer/` defining only a Postgres service (not the gunicorn app — that stays as a host-level systemd service hitting the Postgres via host port).

- Compose stack name: `gbgolf` (creates network `gbgolf_default`, volume `gbgolf_pgdata`).
- Image: `postgres:16-alpine` (matches fleet convention per VPS_STATE §11 step 3).
- Bind only to `127.0.0.1` on a fleet-allocated port (5437–5445 range per VPS_STATE §2 convention).
- Update `.env` `DATABASE_URL` to use `127.0.0.1:<chosen-port>` instead of a Docker network IP.
- Migrate data: `pg_dump` from `gamepredictor-postgres-1` (filtered to the `gbgolf` database), restore into the new container.
- Update VPS_STATE.md §3 to add `gbgolf` as its own stack entry.

Estimated effort: 2-3 hours including data migration and VPS_STATE updates.

### Option B — Migrate to the host MySQL on port 3306

VPS_STATE.md §2 and §8 tentatively note that the host `mysqld` (port 3306) is "Likely Ghost or GBGolfOptimizer," suggesting an earlier intent. Move GBGolf to MySQL:

- Switch SQLAlchemy URL to `mysql+pymysql://...`.
- Add `pymysql` to `pyproject.toml` dependencies (and remove `psycopg2-binary` if unused elsewhere).
- Re-run alembic migrations against MySQL — verify each migration is dialect-portable; rewrite any Postgres-specific SQL.
- Migrate data via `pg_dump → mysql`-compatible conversion (or one-time scripted export/import of the small `fetches` and `projections` tables).

Estimated effort: half a day; bigger surface area than Option A because Postgres-specific SQLAlchemy features (e.g., dialect-specific upserts) may need rework.

### Option C — Move GBGolf into a full Docker stack (gunicorn + Postgres)

Containerize the gunicorn app alongside its own Postgres. Bigger architectural change; abandons the host-socket model that nginx currently reverse-proxies to. Likely overkill for what GBGolf is.

Not recommended unless there's another reason to containerize.

## Recommendation

Do Option A. It's the smallest delta from the current architecture (host gunicorn stays untouched), it gives GBGolf a clean ownership boundary in VPS_STATE.md, and the data migration is straightforward (the `gbgolf` database in `gamepredictor-postgres-1` is small — `fetches` and `projections` only).

## Related

- VPS_STATE.md §10.1 — GamePredictor partial outage (related but distinct concern)
- `tasks/deploy-script-deps.md` — `deploy/deploy.sh` doesn't install Python deps; if Option A or B touches dependencies, that limitation will bite during the redeploy. Fix `deploy.sh` first or include a manual `pip install` step in the migration runbook.
