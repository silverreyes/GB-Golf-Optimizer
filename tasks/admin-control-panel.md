# Backlog: Administrator control panel

## Status: PROPOSED (2026-05-20) — not yet planned or scheduled

## Decisions made

- **Contest config moves into the database** (decided 2026-05-20). DB-backed
  config is the source of truth; it enables on-the-fly editing without a service
  restart and resolves the `deploy.sh` clobber problem (see design consideration
  #2). `contest_config.json` demotes to a one-time bootstrap seed. This resolves
  open question #1 below. Concretely this means: a `contests` table (with
  `collection_limits` as a JSON column or a child table), an alembic migration
  that creates it and seeds from the current JSON, `load_config` reading from the
  DB (still validated through the existing Pydantic model), config no longer
  cached at startup (read per-request or cache-with-invalidation-on-save), and
  `deploy.sh` no longer treating the JSON file as authoritative.

## Goal

A password-protected admin area for operating the optimizer without SSH or
manual file edits on the VPS. The originating request: edit contest
configurations from a UI (add/remove contests, max lineups/entries, salary
bounds, roster size, collection limits — everything currently in
`contest_config.json`).

## Requested feature (primary)

**Contest config management.** Full CRUD over contests:
- Add a new contest / remove an existing one.
- Edit every field: `name`, `salary_min`, `salary_max`, `roster_size`,
  `max_entries`, `collection_limits` (per-collection caps).
- Form validation should surface the rules already encoded in the Pydantic
  model `_ContestConfigModel` (`gbgolf/data/config.py`) — e.g. `salary_max >
  salary_min`. Reuse that model rather than re-implementing validation.

## Candidate additional capabilities (for discussion — not committed)

### Projections management
- **On-demand projection fetch.** Trigger the existing `flask fetch-projections`
  command (registered in `gbgolf/web/__init__.py`, runs `gbgolf.fetcher.run_fetch`)
  immediately, instead of waiting for the Tue/Wed cron. Show progress + result.
- **Fetch history.** Read the `fetches` table: timestamp, tournament name,
  DataGolf `datagolf_updated_at`, staleness. Currently only the single most
  recent fetch is surfaced (the home-page staleness label).
- **Delete / roll back a bad fetch.** Remove a fetch row so the app falls back
  to the previous good one (useful if a fetch pulls the wrong tournament or
  empty projections).
- **Inspect stored projections.** Drill into a fetch's `projections` rows; spot
  missing/zero scores before they cause "no projection found" exclusions.

### Operational visibility
- **Health dashboard.** App version (from `CHANGELOG.md` via
  `gbgolf.changelog.get_latest_version`), DB connectivity, last successful
  fetch, next scheduled cron run, gunicorn/service status. (Would have made the
  2026-05-06 "No route to host" DB outage obvious at a glance.)
- **Audit log.** Record who changed which contest setting / triggered which
  fetch, and when.

### Lower priority / maybe
- Trigger a dry-run optimizer preview from the panel.
- Manage manual projection CSV overrides (the public UI already supports upload;
  admin could view/clear what's stored).

## Critical design considerations (both surfaced during the 2026-05 sessions)

### 1. Contest config is loaded once at startup
`create_app()` does `app.config["CONTESTS"] = load_config(config_path)` at boot.
Editing `contest_config.json` does not take effect until the service restarts —
this is why a manual VPS edit required `systemctl restart gbgolf` (2026-05-20).

A UI editor must resolve this. Options:
- **Hot reload:** re-read the config source on each request (or on save) instead
  of caching at startup. Simplest if config stays a file.
- **Move config to the database:** a `contests` table, edited via the panel,
  read per-request (or cached with explicit invalidation on save). Cleaner
  long-term and removes the file-vs-DB ambiguity below.

### 2. `deploy.sh` clobbers VPS-side config edits
`deploy/deploy.sh` tar-syncs `contest_config.json` from the repo to the VPS. Any
edit made on the VPS — by hand or by a future admin panel — is overwritten on
the next deploy. If the panel writes config at runtime, the **source of truth
must move**:
- DB-backed config (recommended): the repo no longer ships the live config; the
  DB is authoritative. `contest_config.json` becomes a seed/bootstrap only.
- Or: stop syncing `contest_config.json` in `deploy.sh` and treat the VPS copy
  as authoritative (fragile — no version control of the live config).

This decision is a prerequisite for the contest-config editor and is the main
architectural fork in this whole feature.

### 3. Authentication is a prerequisite, not a nice-to-have
The site is fully public today (`gameblazers.silverreyes.net/golf`, no login).
An admin area that edits config and triggers fetches must be access-controlled
before it ships. Decide the mechanism (simple password gate / Flask-Login /
reverse-proxy basic-auth at nginx) early — it gates everything else.

## Open questions

1. ~~DB-backed config vs. hot-reloaded file?~~ **Resolved: DB-backed** (see
   Decisions made).
2. Auth mechanism and where it lives (app vs. nginx)?
3. Single admin user, or multiple with an audit trail?
4. Does the panel live under `/golf/admin` behind the same nginx vhost, or a
   separate subdomain?
5. `collection_limits` storage: JSON column on the `contests` row, or a
   normalized `contest_collection_limits` child table? (JSON is simpler and the
   data is small; child table is more queryable. Lean JSON unless there's a
   reason to query across limits.)

## Suggested phasing (if pursued)

1. Auth gate (prerequisite).
2. Resolve config source-of-truth (DB-backed config + migration off the JSON
   file; update `deploy.sh` accordingly).
3. Contest-config CRUD UI (the requested feature).
4. On-demand fetch + fetch history.
5. Health dashboard.
6. Audit log + remaining nice-to-haves.
