---
name: GB Golf Optimizer project context
description: Key facts about the GBGolfOptimizer project — platform rules, contest specs, tech decisions, current state
type: project
---

GameBlazers fantasy golf lineup optimizer. Live at https://gameblazers.silverreyes.net/golf/

**Why:** User plays on gameblazers.com and wants to optimize weekly lineups for cash contests.

**How to apply:** Use this context when continuing work on this project.

## Platform Rules
- Roster exported as CSV from GameBlazers (columns: Player, Positions, Team, Multiplier, Overall, Franchise, Rookie, Tradeable, Salary, Collection, Status, Expires)
- Overall column = RUC card-burning system only, irrelevant to optimization
- Franchise/Rookie columns = boolean flags only, no optimizer constraints
- $0 salary = player not in tournament field, auto-exclude
- Same player can have multiple cards (different multipliers/salaries) — each card is a distinct ILP variable
- One golfer may appear at most once per lineup (regardless of how many cards owned)
- Each card locked to exactly one lineup — cannot reuse a card across lineups or contests

## Contests
- **The Tips** (cash, priority): 6 golfers, salary $30K–$64K, max 3 Weekly Collection / max 6 Core, 3 entries
- **The Intermediate Tee** (non-cash, packs/credits): 5 golfers, salary $20K–$52K, max 2 Weekly / max 5 Core, 2 entries
- Scoring: birdies +4, eagles +8, double eagle +15, pars -0.5, bogeys -1, double bogeys -3, birdie streak +3, bogey-free round +2, hole-in-one +5, plus finish position bonuses
- Contest config stored in editable JSON file (not scraped)

## Optimization Strategy
- Cash contest optimized first (maximize prize money)
- Non-cash contest built from remaining cards
- Effective value = projected_score × multiplier

## Projection Sources (v1.2+)
Three modes selectable per session:
- **Auto**: DataGolf `fantasy-projection-defaults` API, fetched automatically Tue/Wed via cron, stored in PostgreSQL. Shows tournament name + staleness label.
- **Hybrid**: User uploads partial CSV; DataGolf DB fills gaps for unmatched players. CSV takes priority on conflict.
- **Upload CSV**: Full manual CSV only — DataGolf not used at all. Acceptable column names: player/name/golfer + projected_score/score/projection/projectedpoints.
- Auto and Hybrid disabled when DB is empty (no projections fetched yet).

## Lock / Exclude Behavior
- **Lock Card**: forces a specific card (player+salary+multiplier+collection) into at least one lineup
- **Lock Golfer**: forces a player (by name, any card) into at least one lineup
- Lock algorithm: Phase 1 generates all lineups optimally with no constraints. Phase 2 checks each lock — if not naturally satisfied, substitutes lock into the slot where it contributes most projected score.
- **Exclude Golfer**: removes ALL cards for that player from every lineup (player-level only, no per-card exclusion)
- Lock and Exclude are mutually exclusive per player.
- Player pool section is collapsed by default after lineups are generated.

## Tech Stack
- Python + Flask, PuLP (ILP/CBC), Pydantic v2, httpx, Flask-SQLAlchemy Core, Flask-Migrate
- Jinja2 templates, custom dark CSS (GameBlazers × SilverReyes theme — Prompt + JetBrains Mono, orange/gold palette)
- PostgreSQL (production), SQLite in-memory (tests/dev)
- Deployed: Hostinger KVM 2 VPS — SSH user `deploy`, path `/opt/GBGolfOptimizer`, host `193.46.198.60`
- Deploy: `bash deploy/deploy.sh` (tar sync → flask db upgrade → systemd restart, excludes .env)
- Nginx reverse proxy, Gunicorn, systemd service, SCRIPT_NAME=/golf via env var

## Milestones Shipped
- **v1.0** (2026-03-13): CSV ingestion, ILP optimizer, Flask web app, VPS deployment
- **v1.1** (2026-03-25): Lock/exclude constraints, re-optimize route, full dark theme redesign
- **v1.2** (2026-03-26): DataGolf auto-fetch, PostgreSQL, projection source selector (Auto/CSV)

## Post-v1.2 QoL Improvements (2026-03-26)
- Hybrid projection source mode: partial CSV + DataGolf backfill (validate_pipeline_hybrid)
- CSV format hint inline with radio buttons showing acceptable column header names
- Per-mode description hints: Hybrid explains backfill behavior; CSV explains no backfill
- Player pool collapsed by default after lineup generation; summary bar explains lock/exclude semantics
- Mirror workflow: NatoJenkins/GB-Golf-Optimizer auto-mirrors to silverreyes/GB-Golf-Optimizer on push

## Post-v1.2 QoL Improvements (2026-04-01)
- Staleness label timestamps now show in user's browser local timezone (e.g. "2:00 PM MDT") instead of server timezone. Routes pass raw UTC ISO strings as data attributes; JS reformats client-side using toLocaleString with timeZoneName: 'short'.
