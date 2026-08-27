# GBGolfOptimizer VPS State

Canonical project-local VPS state for GBGolfOptimizer.

Last updated: 2026-06-22 by Claude (Opus 4.8) — gameblazers TLS migrated off the
broken wildcard cert; see Change Log. (Prior split: 2026-06-09 by Codex.)

Global VPS state: `/home/deploy/VPS_STATE.md` on `deploy@193.46.198.60`.
Legacy source archive: `/home/deploy/vps_state_legacy/VPS_STATE_legacy_2026-06-09.md`
with SHA-256 `0acd9c4fa5c112bbcfb4c00d97f2ac2a8f3ed5d64982e6538530fc80530b4b8b`.

## Scope

Use this file for GBGolfOptimizer-specific VPS state: app deploys, project
database migrations, project cron behavior, project-owned Docker resources,
runtime notes, validation history, and cleanup notes.

Update `/home/deploy/VPS_STATE.md` when a change affects shared resources:
nginx, TLS, host ports, systemd units, host cron entries, Docker networks or
volumes, credentials locations, or cross-project cleanup.

## Entry Format

- Date/time in UTC.
- Actor/session.
- Change summary.
- VPS resources touched.
- Validation performed.
- Rollback or follow-up.
- Global impact: `none` or a note saying `/home/deploy/VPS_STATE.md` was also
  updated.

## Current Deployment

| Item | Value |
|---|---|
| Status | **Offseason (2026-08-26)** — `/golf` serves a static placeholder; `gbgolf.service` stopped + disabled; projection cron paused. DB container left running. Returns 2027 — see `deploy/RETURN-TO-SERVICE.md`. |
| Local canonical file | `E:\ClaudeCodeProjects\GBGolfOptimizer\GBGolfOptimizer_VPS_STATE.md` |
| Local repo | `E:\ClaudeCodeProjects\GBGolfOptimizer` |
| VPS path | `/opt/GBGolfOptimizer` |
| Git origin | `https://github.com/NatoJenkins/GB-Golf-Optimizer.git` locally |
| Runtime | Host Gunicorn service plus Docker Compose Postgres |
| Systemd service | `gbgolf.service` |
| Compose file | `/opt/GBGolfOptimizer/docker-compose.yml` |
| Compose project | `gbgolfoptimizer` |
| Public URL | `https://gameblazers.silverreyes.net` |
| Host nginx upstream | `unix:/opt/GBGolfOptimizer/gbgolf.sock` |

## Current Runtime

As of the 2026-06-09 read-only audit:

| Resource | Value |
|---|---|
| App service | `gbgolf.service`, running as `deploy:www-data` |
| Gunicorn bind | `unix:/opt/GBGolfOptimizer/gbgolf.sock` |
| DB container | `gbgolfoptimizer-db-1`, `postgres:16-alpine`, healthy |
| DB host exposure | `127.0.0.1:5437 -> 5432` |
| DB volume | `gbgolfoptimizer_pgdata` |
| Project env | `/opt/GBGolfOptimizer/.env`, should remain `chmod 600` |

## Host Cron

The deploy user's crontab runs `fetch-projections` from `/opt/GBGolfOptimizer`:

- Tue/Wed at 14:00, 16:00, 18:00, 20:00, and 22:00 UTC.
- Wed/Thu at 00:00 UTC.
- Wed/Thu at 02:00 UTC.

**PAUSED 2026-08-26 (offseason).** All three lines are commented out with a dated
`OFFSEASON` marker; re-enable at the 2027 golf season restart (`deploy/RETURN-TO-SERVICE.md`,
Step 3). Pre-pause crontab backup: `/home/deploy/crontab-backup-offseason-20260826.txt`.
The crontab is shared — the NFL-odds, chalkbook, and GBNFLOptimizer-backup lines
were left untouched.

Because this is host cron, changes to this schedule should be reflected in both
this file and `/home/deploy/VPS_STATE.md`.

## Historical Record

Source pointer in the legacy global file: former section dated 2026-05-20,
"GBGolfOptimizer gets a dedicated Postgres".

Condensed history:

- 2026-05-20: GBGolfOptimizer was decoupled from GamePredictor's Postgres and
  given its own dedicated `gbgolfoptimizer-db-1` container.
- Data migrated via `pg_dump`; legacy record noted `fetches=9`,
  `projections=959`, and alembic head `b7c4e9f12a03`.
- Migration backup retained at `/home/deploy/gbgolf-migration-20260520.sql`.
- `.env` backup retained at `/opt/GBGolfOptimizer/.env.bak-20260520`.
- Old `gbgolf` database and role inside `gamepredictor-postgres-1` were left as
  a fallback at migration time and still require deliberate cleanup only after
  verification.

## Change Log

### 2026-08-26 UTC — golf taken offseason (static placeholder; app + cron stopped)

- Actor/session: Claude (Opus 4.8), user NatoJenkins — offseason-shutdown errand
  under the Head Coach protocol. Each production command took its own Owner
  approval; sudo commands were Owner-run.
- Reason: Gameblazers shut its golf game down for the NFL season (Owner ruling,
  scouting report addendum 2026-08-04, ruling 2). The Owner ruled `/golf` offline
  for the offseason, returning at the 2027 season restart.
- Change summary:
  - `/golf` nginx block swapped from `proxy_pass` (Gunicorn socket) to a static
    HTTP-200 placeholder (`root /opt/GBGolfOptimizer; try_files /offseason.html`).
    Placeholder file: `/opt/GBGolfOptimizer/offseason.html` (md5 `8a11c841…`,
    tracked in repo at `deploy/offseason.html`).
  - `gbgolf.service` stopped and **disabled** (survives host reboot).
  - Projection cron paused (3 golf lines commented; see Host Cron above).
  - **DB container `gbgolfoptimizer-db-1` left running** (Owner decision) — idle
    cost is negligible; stopping it saves little while risking a `docker` command
    next to the one-character-apart `gbnfloptimizer-db-1` / `gbnfloptimizer_pgdata`
    and adding a restore step. Data preserved intact.
- VPS resources touched:
  - `/etc/nginx/sites-enabled/gameblazers.silverreyes.net` — **only** the `/golf`
    location block. `/nfl/` (GBNFLOptimizer, live), the port-80 block, and the
    shared TLS lines left byte-identical. Backup:
    `/etc/nginx/gameblazers.silverreyes.net.bak-offseason-20260826`.
  - deploy-user crontab (3 golf lines). Backup:
    `/home/deploy/crontab-backup-offseason-20260826.txt`.
  - `systemd` unit `gbgolf.service` disabled.
- Validation performed:
  - `nginx -t` passed; `/golf` and `/golf/changelog` return HTTP 200 `text/html`
    placeholder with the app fully down and the socket removed; `/nfl/` still 200.
  - `sudo certbot renew --dry-run`: `gameblazers.silverreyes.net (success)` —
    **TLS renewal survives the placeholder change.** (The live cert had already
    auto-renewed to 2026-11-20 via the snap certbot timer; the scouting report's
    2026-09-20 expiry was stale.) Unrelated pre-existing failures for
    `mlbforecaster`/`nostradamus` (NXDOMAIN) flagged to the Owner, out of scope.
- Rollback/return-to-service: `deploy/RETURN-TO-SERVICE.md` (DataGolf key check
  first, nginx restore, service start, cron re-enable, contest-config decision).
- Global impact: `/home/deploy/VPS_STATE.md` updated (nginx + cron are shared).

### 2026-06-22 ~23:15 UTC — gameblazers TLS moved off broken wildcard

- Actor/session: Claude (Opus 4.8), user NatoJenkins.
- Change summary: `gameblazers.silverreyes.net` was migrated from the expired
  wildcard cert (`silverreyes.net-0001`) to a dedicated single-host Let's
  Encrypt cert issued via the nginx authenticator (HTTP-01,
  `certbot --nginx -d gameblazers.silverreyes.net`). The wildcard had expired
  2026-06-20 because it used certbot's `--manual` DNS plugin with no auth hook
  and so could never renew unattended. The orphaned `silverreyes.net-0001`
  lineage was then deleted with `certbot delete`.
- VPS resources touched:
  - New cert lineage `/etc/letsencrypt/live/gameblazers.silverreyes.net/`
    (expires 2026-09-20, auto-renewing via the snap certbot timer).
  - `/etc/nginx/sites-enabled/gameblazers.silverreyes.net` `ssl_certificate`
    and `ssl_certificate_key` lines rewritten by certbot to the new lineage.
  - Deleted cert lineage `silverreyes.net-0001`.
- Validation performed:
  - `openssl s_client` confirms the live cert is now
    `CN=gameblazers.silverreyes.net`, valid 2026-06-22 → 2026-09-20.
  - `certbot renew --dry-run` (full and isolated) passes for all remaining
    lineages. A one-off `silverreyes.net` "authorization must be pending" error
    in the full dry-run was a transient staging hiccup and cleared on the
    isolated re-run.
- Rollback/follow-up: see Open Follow-ups re: the stale `sites-available` copy.
- Global impact: `/home/deploy/VPS_STATE.md` must be updated (TLS is shared);
  the prior "`silverreyes.net-0001` manual-plugin renewal fails dry-run" warning
  there is now resolved by deletion.

## Open Follow-ups

- Sync `/etc/nginx/sites-available/gameblazers.silverreyes.net` to the active
  `sites-enabled` copy. It still references the now-deleted
  `silverreyes.net-0001` cert and would break `nginx -t` if ever re-enabled.
- Confirm whether the old `gbgolf` database and role inside the inactive
  GamePredictor Postgres volume are still needed before removing them.
- Keep host cron changes synchronized with the global VPS state file.
