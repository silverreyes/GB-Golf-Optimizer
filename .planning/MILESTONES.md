# Milestones

## v1.2 Automated Projection Fetching (Shipped: 2026-03-26)

**Phases completed:** 4 phases (08–11), 7 plans, 15 tasks

**Stats:** 4 phases · 7 plans · 3,831 LOC Python · 2026-03-25 → 2026-03-26

**Key accomplishments:**
- Two-table PostgreSQL schema (fetches + projections) with Flask-SQLAlchemy Core, Flask-Migrate migrations, and python-dotenv secrets loading
- DataGolf fetch pipeline (httpx API client, Pydantic boundary validation, atomic DELETE CASCADE + INSERT upsert, 30-player guard, file-append logging)
- Flask CLI command `flask fetch-projections` with cron scheduling (Tue/Wed) for automatic projection fetching — 134 players per fetch
- Projection source selector UI (DataGolf / Upload CSV radio buttons, staleness label, empty-state disabled state, unmatched player warnings)
- Production deployment with PRAGMA dialect guard for PostgreSQL safety, deploy.sh `.env` exclusion fix, and end-to-end verification of both sources on VPS

---

## v1.0 MVP (Shipped: 2026-03-14)

**Phases completed:** 3 phases, 10 plans, 0 tasks

**Key accomplishments:**
- CSV ingestion pipeline with NFKD name normalization and GameBlazers roster + projections merging
- ILP optimizer (PuLP/CBC) enforcing salary ranges, collection limits, same-player and cross-contest card locking
- Flask web app with dual-CSV upload, lineup tables by contest, and unmatched player report
- Systemd + Nginx deployment config for Hostinger KVM 2 VPS with SCRIPT_NAME prefix support
- Live app deployed and browser-verified at http://gameblazers.silverreyes.net/golf/

**Stats:** 3 phases · 10 plans · 1,407 LOC Python · 73 files · 44 commits · 1 day

---

## v1.1 Manual Lock/Exclude (Shipped: 2026-03-25)

**Phases completed:** 4 phases (04–07), 10 plans

**Key accomplishments:**
- Lock/exclude constraint engine — card-level and golfer-level locks enforced via ILP; pre-solve conflict and feasibility checks
- Two-phase lock placement algorithm — Phase 1 generates pure-optimal lineups; Phase 2 places each unsatisfied lock into the slot where it contributes most projected score
- Re-optimize route — card pool serialized to hidden form field; users iterate on constraints without re-uploading CSVs
- Lock/exclude UI — player pool table with per-row checkboxes, lock markers in lineup output, clear-all button, active constraint count display, sortable columns
- Exclusions switched to player-level (all cards for a golfer excluded together)
- Full aesthetic redesign — GameBlazers × SilverReyes theme (Prompt + JetBrains Mono, dark palette, orange accent, gold highlights)
- Deploy pipeline — app moved to /opt, SSH key auth, ssh+tar sync replacing rsync, passwordless sudo for service restart

**Stats:** 4 phases · 10 plans · 11 commits · live at http://gameblazers.silverreyes.net/golf

---

