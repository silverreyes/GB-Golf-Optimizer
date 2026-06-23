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
| Status | Running |
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
