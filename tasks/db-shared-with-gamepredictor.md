# Backlog: GBGolf shares its Postgres with the GamePredictor stack

## Status: RESOLVED (2026-05-20)

Decoupled via Option A. GBGolf now has a dedicated Postgres:

- `docker-compose.yml` added at the repo root → deployed to `/opt/GBGolfOptimizer/`.
  Stack `gbgolfoptimizer`: container `gbgolfoptimizer-db-1` (`postgres:16-alpine`,
  `restart: unless-stopped`), network `gbgolfoptimizer_default`, volume
  `gbgolfoptimizer_pgdata`, bound `127.0.0.1:5437` (host-local only; the host
  gunicorn connects over it).
- Data migrated with `pg_dump` from `gamepredictor-postgres-1` (gbgolf db:
  `fetches`=9, `projections`=959, alembic head `b7c4e9f12a03`). Backup retained
  on VPS at `/home/deploy/gbgolf-migration-20260520.sql`.
- `.env` `DATABASE_URL` repointed from `@172.18.0.2:5432` to `@127.0.0.1:5437`
  (same gbgolf credentials reused; `.env` backed up at `.env.bak-20260520`,
  chmod 600). `POSTGRES_USER/PASSWORD/DB` added for Compose.
- gbgolf service restarted; home page verified 200; app's live connection
  confirmed landing on the new container.
- VPS_STATE.md updated (port-table row for 5437, dated §13 entry, next-available
  port bumped to 5438).

**Deferred cleanup:** the `gbgolf` database + role still exist inside
`gamepredictor-postgres-1` as a fallback. Drop them once the dedicated container
is confirmed stable (give it a few days / one projection cron cycle). Tracked in
VPS_STATE.md §13.

The rest of this file is retained as the historical record of the problem and
the decision.

---

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
