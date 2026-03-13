# Project Research Summary

**Project:** GB Golf Optimizer
**Domain:** DFS Fantasy Golf Lineup Optimizer (GameBlazers-specific, ILP-based)
**Researched:** 2026-03-13
**Confidence:** MEDIUM

## Executive Summary

The GB Golf Optimizer is a single-user, server-side web tool that solves an Integer Linear Programming (ILP) problem: given a player card roster (with multipliers and salaries) and uploaded projections, generate optimal lineups for two GameBlazers contest types (Tips cash contest and Intermediate Tee non-cash contest) while respecting hard constraints including salary floors/ceilings, collection type limits, and a cross-lineup card exclusivity rule. The recommended approach is a minimal Python monolith: FastAPI serving Jinja2 templates, PuLP with its bundled CBC solver for the ILP engine, and pandas for CSV ingestion — deployed directly via systemd/Nginx/Certbot on the Hostinger KVM 2 VPS with no Docker and no database. This stack is deliberately lean; every alternative (SPA frontend, OR-Tools, ORM, task queue, Docker) was evaluated and rejected as disproportionate to the scope.

The dominant technical risk is in the ILP formulation itself. GameBlazers has two properties that break assumptions from standard DFS optimizer tutorials: (1) the same player can appear on multiple cards with different multipliers and salaries — each card must be its own binary decision variable, not each player; and (2) a card used in any lineup (across both contests) cannot appear in any other lineup, requiring a global exclusion set that is passed sequentially from the Tips solve into the Intermediate Tee solve. Getting these two constraints wrong produces silently incorrect lineups. The second most critical data risk is player name normalization — the roster CSV and projections CSV will have name mismatches that must be caught visibly, not silently dropped.

Build order should mirror the dependency chain. The data model and parser must be correct before the optimizer is written, the optimizer must be validated with unit tests before the API layer, and the API must exist before the frontend. The architectural recommendation is to build and test the ILP formulation entirely with hardcoded data before any HTTP or UI work begins. This keeps the highest-risk, highest-value component isolated and verifiable early.

---

## Key Findings

### Recommended Stack

A single-process Python application is the right fit for this scope. FastAPI handles HTTP and file uploads via `UploadFile`; Jinja2 renders server-side HTML (no JS framework); PuLP with its bundled CBC solver handles ILP optimization with zero system-level dependencies; pandas handles CSV ingestion with header-name-based access and BOM-safe encoding. Tailwind CSS via CDN provides styling without a build pipeline. The VPS deployment is Nginx (TLS/proxy) → Uvicorn (2 workers matching 2 vCPUs) → FastAPI app, managed by systemd. No Docker, no database, no ORM, no task queue.

**Core technologies:**
- **Python 3.12** — runtime; avoid 3.13 until confirmed stable on target VPS
- **FastAPI ~0.115** — HTTP API and file upload handling; Pydantic validation reduces boilerplate
- **Uvicorn ~0.30** — ASGI server; 2 workers for the 2-vCPU KVM 2
- **PuLP ~2.8 + bundled CBC** — ILP model and solver; `pip install pulp` produces a working solver with no system dependencies; handles < 500 variables in milliseconds
- **pandas ~2.2** — CSV parsing with encoding safety and column-name-based access
- **Jinja2 ~3.1** — server-side HTML templates; eliminates JS build toolchain entirely
- **Nginx + Certbot** — TLS termination and reverse proxy on the VPS
- **systemd** — process management and auto-restart
- **pytest + ruff + pip-tools** — test runner, linter/formatter, and dependency pinning

See `.planning/research/STACK.md` for full comparison tables and rejected alternatives.

### Expected Features

The full feature set is documented in `.planning/research/FEATURES.md`. Summary below.

**Must have (table stakes):**
- CSV roster upload and parsing (with $0 salary filtering and duplicate card handling)
- Projections CSV upload (with player name normalization and unmatched-player report)
- Contest configuration file (salary floor + ceiling, roster size, collection limits per contest type)
- Optimal lineup generation: ILP with salary range, collection upper bounds, cross-lineup card exclusion
- Cash-first priority ordering (Tips optimized first; Intermediate Tee uses remaining card pool)
- Effective value display (projected_score × multiplier per card)
- Lineup display with per-card stats and per-lineup totals
- Error handling for malformed CSV input

**Should have (differentiators, Phase 2):**
- Card-vs-card comparison for same player (unique to GameBlazers card system; low complexity)
- Manual player lock/exclude (force a card into or out of a lineup)
- Remaining card pool visualization (shows what is available after Tips lineups are built)
- Lineup export / copy-paste format (reduces manual re-entry friction)
- Projection adjustment interface (tweak individual projections in-browser before optimizing)

**Advanced (Phase 3):**
- Multi-lineup diversity / exposure limits (limit a golfer to at most N of K lineups)
- Sensitivity analysis (which players nearly made the lineup and by how much)

**Defer indefinitely:**
- Historical results tracking
- Ownership percentage integration
- Automatic projection scraping
- GameBlazers scraping for contest data
- Any social or multi-user features

### Architecture Approach

The architecture is a three-layer monolith: Frontend (static HTML/JS served by FastAPI) → FastAPI API layer → Python optimization modules. There is no database; CSV data lives in server memory per session and the only persistent state is the contest configuration JSON file on disk. The core algorithmic approach is sequential ILP with cumulative exclusion: solve all Tips lineups in order (maintaining a `used_card_ids` set), then solve all Intermediate Tee lineups using the remaining card pool. Each ILP call is a clean independent optimization (binary variables, maximize effective_value sum, subject to roster size, salary range, collection upper bounds, and card exclusion constraints).

**Major components:**
1. **Card dataclass + CSV Parser** — validates and parses roster and projections CSVs into typed `Card` objects; normalizes player names; filters ineligible cards
2. **Card Inventory** — holds parsed cards in memory; merges projections to compute `effective_value = projected_score * multiplier`
3. **Contest Config Manager** — loads/saves contest definitions (salary ranges, roster sizes, collection limits) from `config/contests.json`
4. **Optimization Engine** — runs PuLP ILP solves sequentially per contest entry; maintains global `used_card_ids` exclusion; returns structured lineup results
5. **FastAPI App** — exposes upload, optimize, and config endpoints; renders results via Jinja2 templates
6. **Frontend (HTML/JS/CSS)** — file upload UI, lineup display, optional config editing

See `.planning/research/ARCHITECTURE.md` for the full ILP formulation, data flow diagram, project structure, and build order.

### Critical Pitfalls

The full pitfall catalog (16 pitfalls, rated Critical/Moderate/Minor) is in `.planning/research/PITFALLS.md`. The five most dangerous:

1. **Duplicate player cards treated as identical players** — Each card must have a unique `card_id` (row index or composite key), not keyed on player name. Model `x_card_id` not `x_player_name`. If same golfer cannot appear twice in one lineup, add a per-player sum constraint. Address in Phase 1 (data model), not later.

2. **Cross-contest card locking not enforced globally** — The Tips and Intermediate Tee solves are separate ILP calls. Cards used in Tips must be explicitly removed from the candidate pool before running Intermediate Tee. Failure produces lineups with reused cards. Add a post-solve validation: total unique card IDs == sum of all lineup sizes.

3. **Player name matching failures (silent drops)** — Normalize both CSVs (lowercase, strip whitespace, remove periods/suffixes) before joining. Use fuzzy matching (`rapidfuzz`) as fallback. Always display an explicit unmatched-player report — never silently exclude a card. Address in Phase 1.

4. **Salary floor missing from ILP** — GameBlazers has both a salary floor and ceiling. Most DFS tutorials only model the cap (upper bound). Model as a two-sided constraint: `min_salary <= sum(salary_i * x_i) <= max_salary`. Add post-solve validation. Address in Phase 2 (optimizer core).

5. **Collection constraints modeled as exact counts instead of independent upper bounds** — "Max 3 Weekly" and "Max 6 Core" are independent upper bounds, not a partition. Model them as separate `<= constraints`, one per collection type. Verify whether Franchise/Rookie columns are additional collection types or boolean flags — this must be clarified before coding constraints.

---

## Implications for Roadmap

### Phase 1: Foundation and Data Integrity

**Rationale:** The optimizer is only as good as its input data. Player name mismatches and $0 salary cards produce incorrect lineups silently. The data model (unique card IDs) is an architectural decision that cannot be changed later without rewriting the optimizer. The card-level data model and CSV parsing layer must be correct and tested before any optimization work begins. Pitfalls 1, 3, 4, 11, and 13 all belong here.

**Delivers:** A tested CSV ingestion pipeline that produces validated `Card` objects with unique IDs, effective values, and explicit unmatched-player reporting. Also delivers the contest configuration file schema and PuLP/CBC verified working on the target VPS.

**Addresses features:** CSV roster upload and parsing; projections upload; contest configuration file; player field filtering; error handling for bad CSV input.

**Avoids:** Duplicate card confusion (Pitfall 1), silent name drop (Pitfall 3), $0 salary cards in optimizer (Pitfall 4), CSV encoding/header brittleness (Pitfall 11), solver binary failure on VPS (Pitfall 13).

**Research flag:** Standard patterns — no additional research needed. CSV parsing with pandas, PuLP installation, and contest config-as-JSON are all well-documented.

### Phase 2: Optimizer Core

**Rationale:** The ILP formulation is the highest-risk, highest-value component. It must be built and unit tested with synthetic card data before any API or UI work begins. This phase validates the mathematical model (salary range, collection bounds, card exclusion, effective value objective) and the sequential multi-lineup algorithm. Pitfalls 2, 5, 6, 7, 8, 9, 10, and 12 all belong here.

**Delivers:** A fully tested `solve_lineup()` function and a multi-lineup generation loop with global card exclusion. Covers Tips (3 lineups) and Intermediate Tee (2 lineups) with correct priority ordering. Includes infeasibility diagnostics.

**Addresses features:** Optimal lineup generation with all constraints; cash-first priority ordering; cross-lineup card locking; collection constraint enforcement; salary cap + floor enforcement; effective value display.

**Avoids:** Salary floor omission (Pitfall 5), collection constraint modeling errors (Pitfall 6), cross-contest card reuse (Pitfall 7), multiplier missing from objective (Pitfall 8), non-binary variables (Pitfall 9), silent infeasibility (Pitfall 10), near-identical lineup generation (Pitfall 2).

**Research flag:** Standard ILP patterns are well-documented. The GameBlazers-specific constraint combination (salary range + collection bounds + global card exclusion) should be verified with unit tests, not additional research.

### Phase 3: API Layer and Web UI

**Rationale:** Once the optimizer engine is proven correct in isolation, wire it to FastAPI endpoints and Jinja2 templates. The UI is a form-submit-and-display workflow — server-side rendering is correct for this pattern. This phase also adds deployment hardening (upload validation, rate limiting, config drift protection).

**Delivers:** A working web application: file upload UI, optimization trigger, and lineup display pages. Contest config viewable and editable in the browser. Deployment-ready with Nginx/systemd configuration.

**Addresses features:** Lineup display with per-card stats and totals; salary utilization display; unmatched-player report in UI; contest config display and editing.

**Avoids:** No upload size validation (Pitfall 14), contest config drift (Pitfall 15), projections/roster asymmetry silent drops (Pitfall 16).

**Research flag:** Standard FastAPI + Jinja2 + Tailwind patterns — no additional research needed. Nginx/systemd deployment is well-documented for Ubuntu.

### Phase 4: Usability Enhancements

**Rationale:** The core optimizer is complete. This phase layers on the differentiator features identified in FEATURES.md that reduce friction and add decision-making value. All are incremental additions to the working baseline.

**Delivers:** Card-vs-card comparison for same player; manual player lock/exclude; remaining card pool visualization after Tips; lineup export/copy-paste format; projection adjustment interface in-browser.

**Addresses features:** The full Phase 2 feature list from FEATURES.md (differentiators with low-to-medium complexity).

**Research flag:** No additional research needed. Manual lock/exclude is a standard ILP constraint addition (`x_i = 1` or `x_i = 0` forced). Remaining pool visualization is a display feature.

### Phase 5: Advanced Optimization

**Rationale:** Diversity constraints and sensitivity analysis require changes to the ILP formulation and are reserved until the baseline optimizer has been used in practice. Real-world usage will clarify whether near-identical lineups are actually a problem (card locking already provides natural diversity) before investing in joint multi-lineup optimization.

**Delivers:** Configurable exposure limits per golfer across lineups; optional minimum-difference constraints between lineups; sensitivity/shadow price analysis.

**Addresses features:** Multi-lineup correlation awareness; lineup diversity controls; sensitivity analysis ("how close").

**Research flag:** This phase warrants deeper research before implementation. Joint multi-lineup ILP (solving all Tips lineups simultaneously) is a meaningfully different formulation from sequential ILP. The tradeoffs between sequential sub-optimality (Pitfall 12) and implementation complexity should be evaluated with real-world data from Phase 4 usage.

### Phase Ordering Rationale

- Data integrity before optimization: Name matching and card ID bugs produce silent incorrect output that is hard to detect later. Catching them at ingestion is much cheaper than debugging optimizer output.
- Optimizer before API: The ILP formulation is the riskiest component. Test it with unit tests and hardcoded data first. Building the UI before the optimizer is tested leads to hard-to-debug integration problems.
- API before frontend: The Jinja2 templates render the API response; they cannot be tested without working endpoints.
- Usability before advanced optimization: Diversity constraints require real-world feedback to justify. Build the baseline, use it for a tournament cycle, then decide if diversity enhancement is needed.
- The ARCHITECTURE.md component build order (Config Manager + CSV Parser → Card Inventory + Optimization Engine → FastAPI endpoints → Frontend) maps directly to this phase structure.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 5 (Advanced Optimization):** Joint multi-lineup ILP and exposure-limit formulations are meaningfully more complex than the baseline. Worth a targeted research spike before planning this phase, using real roster data to evaluate whether sequential sub-optimality is materially significant.

Phases with standard patterns (skip research-phase):
- **Phase 1:** CSV parsing with pandas, PuLP/CBC installation, JSON config file — all standard, well-documented Python patterns.
- **Phase 2:** Single-lineup ILP with PuLP is thoroughly documented. The GameBlazers-specific constraints are novel combinations of standard patterns, testable via unit tests.
- **Phase 3:** FastAPI + Jinja2 + Tailwind + Nginx/systemd deployment is standard and well-documented.
- **Phase 4:** All usability features are incremental UI and constraint additions with no novel research needed.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | All libraries are mature and stable. Version numbers are from training data (cutoff ~mid 2025); confirm latest via PyPI before installing. API capabilities described are accurate. |
| Features | MEDIUM | Table stakes and differentiators derived from DFS optimizer ecosystem (FantasyLabs, SaberSim, etc.) plus GameBlazers-specific rules from PROJECT.md. Core feature set is stable; GameBlazers-specific rules confirmed from project documentation. |
| Architecture | HIGH | Three-layer monolith + sequential ILP + stateless request pipeline are proven patterns for this problem class. ILP formulation derived from operations research fundamentals. The sequential-vs-joint optimization tradeoff is well-understood. |
| Pitfalls | MEDIUM-HIGH | ILP formulation pitfalls (binary variables, constraint modeling, infeasibility) are well-established in OR literature. GameBlazers-specific pitfalls (duplicate cards, cross-contest exclusion) derived from project requirements with high confidence. Name normalization and CSV encoding pitfalls are well-known Python/pandas patterns. |

**Overall confidence:** MEDIUM — sufficient to begin implementation. The main uncertainty is exact library versions (verify via PyPI) and two unresolved GameBlazers rule questions noted below.

### Gaps to Address

- **Franchise and Rookie CSV columns:** PITFALLS.md flags that the roster CSV has `Collection`, `Franchise`, and `Rookie` columns. It is unclear whether Franchise/Rookie are separate collection types (requiring their own ILP constraints) or boolean flags. This must be verified against a real GameBlazers export before Phase 2 ILP constraints are coded. If they are collection types, the collection constraint model needs to expand to handle them.

- **Same-golfer-in-same-lineup rule:** PITFALLS.md flags uncertainty about whether GameBlazers allows the same golfer on two different cards in the same lineup. If prohibited, a per-player sum constraint (`sum(x_i for cards where player == golfer) <= 1`) must be added in Phase 2. This is easy to add but must be confirmed before the optimizer is finalized.

- **Exact contest parameters:** The example contest config values in ARCHITECTURE.md (salary ranges, roster sizes, collection limits) are illustrative. Actual current values must be confirmed against the live GameBlazers contest before deploying. This is a Phase 1 config task, not a research task.

- **Library version confirmation:** All recommended versions are from training data. Run `pip index versions fastapi pulp pandas uvicorn` on the VPS before finalizing `requirements.in`.

---

## Sources

### Primary (HIGH confidence)
- `E:/ClaudeCodeProjects/GBGolfOptimizer/PROJECT.md` — GameBlazers-specific contest rules, constraint definitions, and scope boundaries
- PuLP documentation (coin-or.github.io/pulp) — ILP formulation patterns and binary variable declaration
- FastAPI documentation (fastapi.tiangolo.com) — UploadFile handling, Jinja2 integration, endpoint structure

### Secondary (MEDIUM confidence)
- DFS optimizer community patterns (training data) — multi-lineup sequential ILP with card exclusion; this is the standard pattern used by pydfs-lineup-optimizer and similar tools
- FantasyLabs, SaberSim, FantasyCruncher, DraftKings optimizer (training data) — feature landscape for DFS lineup optimizers

### Tertiary (LOW-MEDIUM confidence)
- Exact PyPI version numbers — from training data cutoff ~mid 2025; should be confirmed before install
- Hostinger KVM 2 Ubuntu environment specifics — general Linux deployment knowledge; verify PuLP/CBC binary compatibility on actual VPS early in Phase 1

---
*Research completed: 2026-03-13*
*Ready for roadmap: yes*
