# Phase 3: Web Application and Deployment - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a browser UI for file uploads (roster CSV + projections CSV), trigger lineup generation, and display results — then deploy the app to the Hostinger KVM 2 VPS. Optimization logic (Phase 2) and data parsing (Phase 1) are complete; this phase wraps them in a web layer and ships to production.

</domain>

<decisions>
## Implementation Decisions

### Page structure & upload flow
- Single-page app — upload form at top, results render below it on the same page
- After generating lineups, the upload form collapses with a small "Change files" toggle to reveal it again
- While optimization runs, a full-page loading overlay is shown
- Files persist in the form so user can change one file and re-run without re-uploading both

### Lineup results display
- Contests displayed as sequential sections: The Tips first, then The Intermediate Tee below
- Each lineup rendered as a table — one row per player, columns: Player | Collection | Salary | Multiplier | Proj Score
- Lineup totals appear both as a summary header above each lineup table AND as a footer row within the table
- If a lineup could not be built (infeasibility notice), show a clear message in its place

### Unmatched player report
- Report appears between the upload form and the lineup results
- Only shown when there are exclusions — hidden entirely on a clean run
- Format: simple list, one row per excluded card with the reason inline (e.g., "Ludvig Åberg — no projection found")
- Covers all three exclusion reasons: no projection found, $0 salary (not in field), expired card

### Deployment
- URL: `gameblazers.silverreyes.net/golf` — subdomain dedicated to GameBlazers-related optimizers; `/golf` path distinguishes this from a future NFL optimizer at `/nfl`
- Server setup: systemd service + Nginx reverse proxy
- The VPS already runs Open Claw — Nginx config must coexist with it (separate server block for the subdomain, no port conflicts)
- No existing website published at silverreyes.net to protect

### Claude's Discretion
- Flask vs FastAPI choice (both listed in project constraints; either works)
- HTML/CSS framework (vanilla or lightweight library — no heavy frontend framework needed)
- Gunicorn worker count and bind port
- Exact Nginx server block configuration
- Styling details (colors, fonts, spacing)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gbgolf.data.validate_pipeline(roster_path, projections_path, contests)` → `ValidationResult` — the web layer calls this with uploaded file paths
- `gbgolf.optimizer.optimize(valid_cards, contests)` → `OptimizationResult` — called after validation; returns lineups grouped by contest
- `OptimizationResult`: `.lineups` (dict by contest name), `.unused_cards`, `.infeasibility_notices`
- `Lineup`: `.contest`, `.cards`, `.total_salary`, `.total_projected_score`, `.total_effective_value`
- `Card`: `.player`, `.salary`, `.multiplier`, `.collection`, `.projected_score`, `.effective_value`
- `ValidationResult`: `.valid_cards`, `.excluded` (list of `ExclusionRecord`), `.projection_warnings`
- `ExclusionRecord`: `.player`, `.reason` (one of "$0 salary", "no projection found", "expired card")
- `contest_config.json` — already exists at project root with contest parameters

### Established Patterns
- Dataclasses for all data structures (not Pydantic at the core layer)
- Functions return data, no print/I/O in core logic — clean to wrap in HTTP handlers
- Fail fast with clear ValueError messages — web layer should catch these and surface as user-facing errors

### Integration Points
- Web app imports `gbgolf.data.validate_pipeline` and `gbgolf.optimizer.optimize`
- Uploaded CSVs need to be written to temp files (or streamed) before passing to `validate_pipeline`
- `contest_config.json` loaded at startup and passed to both `validate_pipeline` and `optimize`
- The web app is a new module: `gbgolf/web/` or similar

</code_context>

<specifics>
## Specific Ideas

- `gameblazers.silverreyes.net` subdomain is intentionally scoped to GameBlazers tools — a future NFL optimizer will live at `/nfl` on the same subdomain
- Open Claw is already running on the VPS — Nginx must not conflict with it

</specifics>

<deferred>
## Deferred Ideas

- NFL optimizer — future project on the same subdomain at `/nfl`

</deferred>

---

*Phase: 03-web-application-and-deployment*
*Context gathered: 2026-03-13*
