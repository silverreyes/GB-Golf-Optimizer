# Retrospective: GB Golf Optimizer

---

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-13
**Phases:** 3 | **Plans:** 10

### What Was Built

- CSV ingestion pipeline with NFKD name normalization and projection merging
- ILP optimizer (PuLP/CBC) enforcing salary ranges, collection limits, same-player and cross-contest card locking
- Flask web app with dual-CSV upload, lineup tables by contest, and unmatched player report
- Systemd + Nginx deployment config for Hostinger KVM 2 VPS
- Live app deployed and browser-verified at gameblazers.silverreyes.net/golf

### What Worked

- **TDD RED→GREEN discipline**: Every phase scaffolded failing stubs first, then implemented to green. Caught real bugs (test fixture undersizing in 02-03).
- **Pydantic at boundary only**: Validated external JSON at I/O, passed plain dataclasses internally — kept optimizer layer clean and fast.
- **Dependency chain ordering**: Data → Optimizer → Web/Deploy was the natural order; each phase produced independently testable output consumed by the next.
- **Pure formatting functions**: `report.py` returning strings instead of printing kept formatters testable and the CLI layer thin.
- **ILP upper-bound-only collection constraints**: Realized early that 0 Weekly Collection cards per lineup is legal — avoids infeasibility for edge-case pools.

### What Was Inefficient

- **Test fixture undersizing**: Phase 02-03 required expanding `TIPS_CARDS` (12→18) and `ALL_CARDS` (25→35) because initial fixtures couldn't satisfy disjoint pool requirements for multiple lineups. This was caught by tests but required rework.
- **Blockers listed in STATE.md that were already resolved**: Franchise/Rookie and same-golfer constraints were flagged as open blockers but resolved in Phase 1 context-gathering.

### Patterns Established

- **NFKD Unicode normalization** for golfer name matching (`Åberg == Aberg`) — essential for international golfer names.
- **Windows-safe temp file pattern**: Write inside with-block, pass path outside after close — avoids `NamedTemporaryFile` locking on Windows dev machines.
- **SCRIPT_NAME via systemd environment variable**: Flask/Werkzeug reads it automatically — zero code changes needed to support URL prefix under `/golf`.
- **Pool-size guard in pipeline**: `validate_pipeline()` uses `min(c.roster_size)` to fail fast before optimizer receives unusable data.

### Key Lessons

- **Confirm domain rules early**: The Franchise/Rookie flag question and same-golfer-per-lineup rule both needed user confirmation. Getting these in Phase 1 context prevented backtracking in Phase 2.
- **ILP infeasibility is a feature**: Returning a clear notice (not crashing) when constraints can't be satisfied is UX-critical for a tool users will run weekly with different card pools.
- **Human verification phases are legitimate**: Phase 03-03 was a purely human step (deploy + browser confirm). No code written. Worth a dedicated plan for traceability.

### Cost Observations

- Sessions: 1 intense session (all 3 phases in ~8 hours)
- Notable: Single-day delivery of full stack including VPS deployment

---

## Milestone: v1.1 — Manual Lock/Exclude

**Shipped:** 2026-03-25
**Phases:** 4 (04–07) | **Plans:** 10

### What Was Built

- Lock/exclude constraint engine — card-level and golfer-level locks enforced via ILP; pre-solve conflict and feasibility checks
- Two-phase lock placement algorithm — Phase 1 generates pure-optimal lineups; Phase 2 places each unsatisfied lock into the best remaining slot
- Re-optimize route — card pool serialized to hidden form field; users iterate on constraints without re-uploading CSVs
- Lock/exclude UI — player pool table with per-row checkboxes, lock markers in lineup output, clear-all button, active constraint count display
- Full aesthetic redesign — GameBlazers × SilverReyes dark theme (Prompt + JetBrains Mono, orange/gold palette)
- SSH+tar deploy pipeline (replaced rsync), app moved to /opt

### What Worked

- **Two-phase lock placement**: Separating "optimize freely" from "place locks greedily" made the algorithm tractable — pure ILP lock enforcement caused infeasibility on edge cases.
- **Re-optimize without re-upload**: Serializing card pool to hidden form field was a simple, low-risk pattern that gave users a strong iterative workflow.
- **Player-level exclusion (not card-level)**: Switching EXCL to exclude all cards for a golfer matched user mental model — they think in players, not individual cards.

### What Was Inefficient

- Lock/exclude session persistence is scoped to the form; clearing on re-upload is correct but users who upload a new roster lose their constraint setup.

### Patterns Established

- **Two-phase constraint placement**: Greedy phase handles locks that pure ILP can't guarantee feasibility for.
- **Hidden form field serialization**: Pool state transmitted via compressed hidden input — avoids session storage complexity.

### Key Lessons

- **Feasibility checks before solve**: Running pre-solve conflict detection (lock+exclude same player, lock infeasible salary) gives actionable errors rather than solver "infeasible" returns.
- **CSS design tokens first**: Establishing the dark theme spacing/color tokens in Phase 7 before building components prevented visual inconsistency.

### Cost Observations

- Sessions: Multiple short sessions across 2026-03-14 to 2026-03-25
- Notable: Theme redesign (Phase 7) was low-code but high visual impact

---

## Milestone: v1.2 — Automated Projection Fetching

**Shipped:** 2026-03-26
**Phases:** 4 (08–11) | **Plans:** 7

### What Was Built

- PostgreSQL schema (fetches + projections tables) with Flask-SQLAlchemy Core, Flask-Migrate, and python-dotenv
- DataGolf fetch pipeline: httpx API client, Pydantic boundary model, atomic DELETE CASCADE + INSERT upsert, 30-player safety guard, file-append logging
- Flask CLI command `flask fetch-projections` with cron scheduling (Tue/Wed) — confirmed 134 players per live fetch
- Projection source selector: DataGolf / Upload CSV radio buttons, staleness label (tournament name + days ago), empty-state disabled, unmatched player warnings
- Production deployment: PRAGMA dialect guard for PostgreSQL safety, deploy.sh `.env` exclusion fix, end-to-end verification both sources

### What Worked

- **Live API discovery before planning**: Running a real DataGolf API call in Phase 9 Plan 1 confirmed `proj_points_total` (not `fantasy_points` or `proj_points`) and `event_name` — zero wasted implementation from bad field assumptions.
- **Separate validate_pipeline_auto()**: Adding a second pipeline entry point (zero modifications to the CSV path) gave confidence that the existing feature was never at risk.
- **_db_template_vars() injected everywhere**: Forcing all render_template calls to include DB context prevented missing-variable errors on error paths — a simple pattern that eliminated an entire class of bug.
- **TDD throughout**: All 7 plans used RED→GREEN. Phase 11 caught the dialect guard bug (session.bind vs session.get_bind()) before production hit it.
- **Milestone audit before closing**: The audit validated 11/11 requirements from 3 sources (REQUIREMENTS.md, SUMMARY frontmatter, VERIFICATION.md) — no surprises.

### What Was Inefficient

- **deploy.sh .env overwrite**: Local `.env` was syncing to VPS on every deploy, silently overwriting the production database URL with the SQLite dev value. This caused 500 errors after deployment and required manual VPS env restoration. Adding `--exclude='./.env'` to the tar command fixed it, but it should have been caught in Phase 11 plan design.
- **Nyquist VALIDATION.md stubs not completed**: All 4 phases have draft-status VALIDATION.md files. Not a functional gap, but `/gsd:validate-phase` was never run — worth completing before v1.3 if test coverage depth matters.

### Patterns Established

- **Dialect guard**: `session.get_bind().dialect.name` (not `session.bind.dialect.name`) for Flask-SQLAlchemy scoped session compatibility — `.bind` returns None.
- **db_client test fixture + _seed_projections helper**: Reusable DB-backed web test infrastructure for any future routes that need projection data.
- **DEPLOY.md with real values**: Production infrastructure guide uses actual VPS IP, user, paths — only secrets get CHANGEME markers. Avoids ambiguity during deployments.

### Key Lessons

- **Deployment excludes matter**: Any file that differs between dev and prod environments should be excluded from the deploy tar. Secrets/config files are the obvious case — make this a checklist item.
- **DataGolf API field names require live discovery**: Documentation is sparse; always run a real call early to confirm field names before writing Pydantic models.
- **Cron vs scheduled time**: The cron was registered as `0 14,22 * * 2,3` (14:00 and 22:00 UTC) to catch DataGolf publish timing reliably. Document the actual registered schedule, not the intended schedule.

### Cost Observations

- Sessions: 2 sessions across 2026-03-25 to 2026-03-26
- Notable: All 7 plans completed in ~35 minutes of execution time; most time was human verification during Phase 11 deployment

---

## Cross-Milestone Trends

| Milestone | Phases | Plans | LOC | Days | Key Win |
|-----------|--------|-------|-----|------|---------|
| v1.0 MVP | 3 | 10 | 1,407 | 1 | TDD + ILP delivered working optimizer in one session |
| v1.1 Lock/Exclude | 4 | 10 | ~2,200 | 11 | Two-phase lock placement + dark theme redesign |
| v1.2 Auto-Fetch | 4 | 7 | 3,831 | 2 | Live API discovery + atomic upsert + source selector |
