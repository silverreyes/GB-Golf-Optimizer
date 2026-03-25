# Feature Research: v1.2 DataGolf API Integration

**Domain:** DFS Golf Lineup Optimizer -- DataGolf Scratch Plus API integration and projection source selector
**Researched:** 2026-03-25
**Confidence:** HIGH for API structure and integration patterns; MEDIUM for exact fantasy-projection-defaults response fields (documented via historical endpoint sample + official docs; projection endpoint field names extrapolated but need first-call verification)

## Research Focus

This document covers feature requirements for v1.2: automated projection fetching from DataGolf's `fantasy-projection-defaults` endpoint, PostgreSQL storage, cron scheduling, and a projection source selector in the optimizer UI.

---

## DataGolf API: Verified Facts

### Endpoint

```
GET https://feeds.datagolf.com/preds/fantasy-projection-defaults
```

**Parameters:**

| Parameter | Required | Default | Options | Notes |
|-----------|----------|---------|---------|-------|
| `key` | YES | -- | API token string | Passed as query parameter |
| `tour` | NO | `pga` | `pga`, `euro`, `opp`, `alt` | `opp` = opposite-field PGA TOUR event |
| `site` | NO | `draftkings` | `draftkings`, `fanduel`, `yahoo` | FanDuel/Yahoo: main slate only |
| `slate` | NO | `main` | `main`, `showdown`, `showdown_late`, `weekend`, `captain` | Non-main slates DraftKings only |
| `file_format` | NO | `json` | `json`, `csv` | JSON recommended for programmatic use |

**For this project, always use:** `tour=pga&site=draftkings&slate=main&file_format=json`

Source: [DataGolf API Access](https://datagolf.com/api-access) -- HIGH confidence

### Authentication

- **Method:** API key as query parameter (`?key=API_TOKEN`)
- **Access requirement:** Scratch Plus membership (paid subscription)
- **No OAuth, no headers, no bearer tokens** -- simple query parameter auth

Source: [DataGolf API Access](https://datagolf.com/api-access) -- HIGH confidence

### Rate Limits

- **Limit:** 45 requests per minute across all endpoints
- **Penalty:** 5-minute suspension/timeout when exceeded
- **No tier differences** -- same limit for all Scratch Plus members
- **Context:** Implemented because their servers were "massacred one too many times" -- lenient but firm

Source: [DataGolf Forum - PSA: API Rate Limits](https://forum.datagolf.com/t/psa-api-rate-limits/2511) -- HIGH confidence

**Implication for v1.2:** With cron running 2x/week fetching a single endpoint, rate limits are a non-issue. Even manual re-fetches from a UI button would be fine. No retry/backoff logic needed beyond basic HTTP error handling.

### Response Structure (Verified via Historical Endpoint Sample)

The DataGolf historical DFS data endpoint (`/historical-dfs-data/sample`) returns this verified structure for DraftKings:

```json
{
  "dg_id": 1547,
  "player_name": "Mickelson, Phil",
  "salary": 6700,
  "ownership": 0.0136,
  "fin_text": "1",
  "streak_pts": 0,
  "bogey_free_pts": 0,
  "hole_in_one_pts": 0,
  "sub_70_pts": 0,
  "hole_score_pts": 75.5,
  "finish_pts": 30,
  "total_pts": 105.5
}
```

CSV headers for historical data:
```
tour,year,season,event_name,event_id,site,ownerships_from,player_name,dg_id,salary,ownership,fin_text,streak_pts,bogey_free_pts,hole_in_one_pts,sub_70_pts,hole_score_pts,finish_pts,total_pts
```

Source: [DataGolf Historical DFS Sample](https://feeds.datagolf.com/historical-dfs-data/sample?site=draftkings&file_format=json) -- HIGH confidence (actual API response)

### Fantasy Projection Defaults Response (Extrapolated -- MEDIUM Confidence)

The `fantasy-projection-defaults` endpoint returns **projections** (forward-looking), not actuals. Based on:
1. The historical endpoint field naming conventions (verified above)
2. The DataGolf fantasy projections web page showing columns for projected points, salary, ownership
3. The API documentation stating it "corresponds to the Fantasy Projections page with default settings"

The projection response per player likely contains:

| Field | Type | Description | Confidence |
|-------|------|-------------|------------|
| `dg_id` | int | DataGolf unique player ID | HIGH -- consistent across all endpoints |
| `player_name` | string | Player name in **"Last, First"** format | HIGH -- verified in historical sample |
| `salary` | int | DraftKings salary in hundreds (e.g., 6700 = $6,700) | HIGH -- verified in historical sample |
| `proj_ownership` | float | Projected ownership percentage (0.0-1.0) | MEDIUM -- historical uses `ownership`; projection may prefix with `proj_` |
| Projected points field | float | Projected DraftKings fantasy points | MEDIUM -- likely named something like `proj_points`, `total_pts`, or `projected_pts` |
| Event metadata | varies | Tournament name, event_id | MEDIUM -- historical data includes these; projections likely do too |

**CRITICAL ACTION ITEM:** On first API call, log the full raw response and document exact field names. The projection endpoint may use different field names than the historical endpoint (e.g., `proj_ownership` vs `ownership`, projected vs actual point breakdowns). Build the Pydantic model with `model_config = ConfigDict(extra="allow")` initially to capture unknown fields.

### Player Name Format: "Last, First"

**DataGolf:** `"Mickelson, Phil"`, `"Koepka, Brooks"`, `"Oosthuizen, Louis"`
**GameBlazers:** `"Scottie Scheffler"`, `"Rory McIlroy"`, `"Ludvig Aberg"` (First Last)

DataGolf's own documentation warns: *"player_name will not necessarily be the same for all data points for a given player. Use dg_id instead of player_name when performing operations by player."*

Source: [DataGolf Raw Data Notes](https://datagolf.com/raw-data-notes) -- HIGH confidence

### Tournament / Week Concept

DataGolf does **not** use a "calendar week" concept for the API. Key facts:

- **No explicit week parameter** on `fantasy-projection-defaults` -- the endpoint automatically returns projections for the **current/upcoming tournament**
- **`event_id`** identifies tournaments -- constant across years for PGA/KFT tours, changes annually for other tours
- **`event_name`** may change year-to-year for the same event_id
- Projections appear when field data is available -- typically Monday (free content) to Tuesday (paid content) before a Thursday-start event
- Finish probabilities recalculate when field changes or tee times are released (typically Tuesday for Thursday events)

Source: [DataGolf FAQ](https://datagolf.com/frequently-asked-questions), [DataGolf Raw Data Notes](https://datagolf.com/raw-data-notes) -- HIGH confidence

**Implication:** The API call is stateless regarding time -- you always get the current week's projections. Store `event_name`, `event_id`, and fetch timestamp to know what week the data is for.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features the v1.2 milestone must deliver. Without these, the milestone is incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| DataGolf API fetcher | Core purpose of v1.2; manually averaging projections from multiple sites is tedious | MEDIUM | HTTP GET with API key query param; parse JSON response; handle errors. Use `requests` or `httpx`. |
| PostgreSQL projection storage | Projections must persist between sessions; file-based storage is fragile for scheduled fetches | MEDIUM | Schema: projections table with `dg_id`, `player_name`, `salary`, projected points, `event_name`, `event_id`, `fetch_timestamp`. Design for v1.3 user accounts. |
| Cron-based auto-fetch | User should not have to manually trigger fetches; projections should be ready when they open the app | LOW | systemd timer or cron on Ubuntu 24.04; runs Tue + Wed mornings; calls the fetcher script/module. |
| Projection source selector | User must choose DataGolf projections (from DB) or upload a CSV manually; cannot force one or the other | MEDIUM | Radio button or dropdown on the upload form. When "DataGolf" selected, hide projections file input. When "CSV" selected, show file upload as before. |
| Stale data indicator | When DataGolf projections are from a previous week (no current-week fetch yet), user must know the data is old | LOW | Compare `event_name` or `fetch_timestamp` against current date. Show label: "DataGolf projections from [Event Name] (fetched [N days ago])" |
| Player name normalization (DataGolf to GameBlazers) | DataGolf uses "Last, First"; GameBlazers uses "First Last"; matching must work automatically | MEDIUM | Extend `normalize_name()` or add a `parse_datagolf_name()` that converts "Last, First" to "first last" before normalization. Handle edge cases (suffixes, accents). |

### Differentiators (Competitive Advantage)

Features that make v1.2 significantly better than just "fetch and display."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Automatic "best available" projection selection | When current-week DataGolf projections exist, auto-select them; otherwise fall back to last-fetched with staleness warning | LOW | Reduces friction -- user opens app and projections are ready. No manual source selection needed for the common case. |
| Projection comparison view | Show DataGolf projected points alongside user's CSV projections for same player, highlighting discrepancies | MEDIUM | Helps user decide whether to trust DataGolf or their own numbers. Defer to v1.3+ unless trivial to add. |
| Manual fetch button in UI | Let user trigger a DataGolf fetch from the web UI (in addition to cron) | LOW | "Refresh Projections" button; calls same fetcher logic; useful when cron hasn't run yet or user wants latest data. |
| Fetch status dashboard | Show last fetch time, event name, player count, and any fetch errors in the UI | LOW | Simple info panel. Builds confidence that automation is working. |

### Anti-Features (Do NOT Build in v1.2)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Multi-source projection averaging | "Average DataGolf + FantasyNational + own projections for better accuracy" | Massively increases scope -- need multiple API integrations, weighting logic, normalization. PROJECT.md explicitly scopes this to v2.0. | Single source (DataGolf or CSV). User can manually average externally and upload CSV. |
| DataGolf custom settings (weights, course fit, etc.) | DataGolf web UI lets users adjust Long-Term/Short-Term form weights, course fit, etc. | API `fantasy-projection-defaults` endpoint only returns **default** settings. Custom settings require the full projection endpoint (different tier?). Adds complexity with minimal value. | Use defaults. DataGolf's default model is already good. |
| Historical projection tracking | "Show how DataGolf's projections changed through the week" | Requires storing multiple snapshots per event. Complicates schema and UI. Minimal value for lineup optimization. | Store only the latest fetch per event. Cron runs Tue + Wed to capture any mid-week updates. |
| DraftKings salary integration from DataGolf | "Use DataGolf's DK salary data instead of GameBlazers salary" | GameBlazers has its own salary system independent of DraftKings. DataGolf DK salaries are irrelevant to GameBlazers lineup building. | Ignore the `salary` field from DataGolf response. Only use projected fantasy points. |
| DataGolf strokes-gained or skill decomposition data | "Use sg_putt, sg_app etc. for custom modeling" | Out of scope per PROJECT.md. v1.2 uses `fantasy-projection-defaults` only. Custom modeling is a v2.0+ feature. | Stick to projected fantasy points from the defaults endpoint. |
| Automatic player name matching via dg_id cross-reference | "Fetch DataGolf's player list, build a dg_id-to-GameBlazers-name mapping table" | Over-engineering for v1.2. The normalize_name approach works for 95%+ of players. Building and maintaining a mapping table adds a database table, admin UI, and ongoing maintenance. | Use name normalization (Last,First -> first last). Surface unmatched players in the UI (existing pattern). Let user manually fix their CSV if needed. |

---

## Feature Dependencies

```
DataGolf API Fetcher (PROJ-01)
    |
    +-- requires --> API Key Configuration (env var / config)
    |
    +-- requires --> Player Name Parser ("Last, First" -> normalized)
    |
    +-- produces --> Raw projection data
            |
            +-- stored in --> PostgreSQL Projection Table (PROJ-03)
                                |
                                +-- consumed by --> Projection Source Selector (PROJ-04)
                                |                       |
                                |                       +-- feeds --> Optimizer (existing)
                                |
                                +-- consumed by --> Stale Data Display (PROJ-05)

Cron Scheduler (PROJ-02)
    |
    +-- triggers --> DataGolf API Fetcher (PROJ-01)

CSV Upload (existing v1.0)
    |
    +-- alternative to --> PostgreSQL Projection Table (PROJ-03)
    |
    +-- selected via --> Projection Source Selector (PROJ-04)
```

### Dependency Notes

- **PROJ-01 (Fetcher) requires API key config:** Must decide where to store the API key. Environment variable (`DATAGOLF_API_KEY`) is simplest and most secure. Do NOT hardcode or commit to repo.
- **PROJ-03 (DB) requires PROJ-01 (Fetcher):** The DB schema design depends on knowing the exact API response fields. Build PROJ-01 first, log raw response, then finalize schema.
- **PROJ-04 (Selector) requires PROJ-03 (DB):** The selector needs to query the DB to show available DataGolf projections and their metadata (event name, date).
- **PROJ-05 (Stale display) requires PROJ-03 (DB):** Staleness is determined by comparing DB `fetch_timestamp` and `event_name` against the current date.
- **PROJ-02 (Cron) is independent:** Can be set up any time after PROJ-01 works. Systemd timer on the VPS.

---

## Edge Cases and Risks

### Edge Case 1: No Current-Week Projections Available

**Scenario:** User opens the app on Monday morning. DataGolf hasn't published projections for the upcoming tournament yet (content typically drops Monday afternoon for free, Tuesday for paid).

**Handling:**
- If no projections exist in DB at all: show "No DataGolf projections available yet. Upload a CSV instead."
- If projections exist but for a previous event: show "DataGolf projections from [Previous Event Name] (fetched [date]). These may not reflect the current field." with a warning icon.
- Auto-select CSV upload as default source if DataGolf data is stale.

### Edge Case 2: Player Name Mismatches

**Scenario:** DataGolf returns `"Scheffler, Scottie"` but GameBlazers roster has `"Scottie Scheffler"`. After normalization, both become `"scottie scheffler"` -- match. But edge cases exist:

| DataGolf Name | GameBlazers Name | Issue | Solution |
|---------------|------------------|-------|----------|
| `"Aberg, Ludvig"` | `"Ludvig Aberg"` | No accent in GameBlazers | Already handled by `normalize_name()` NFKD decomposition |
| `"Kim, Si Woo"` | `"Si Woo Kim"` | Multi-word first name | "Last, First" split on first comma handles this correctly |
| `"Hojgaard, Nicolai"` | `"Nicolai Hojgaard"` | Accent in original (Hojgaard) | NFKD handles this |
| `"Smith Jr., Cameron"` | `"Cameron Smith"` | Suffix in DataGolf, none in GameBlazers | Strip common suffixes (Jr., Sr., III, IV) during normalization |
| `"Van Rooyen, Erik"` | `"Erik Van Rooyen"` | Multi-word last name | "Last, First" split on first comma: last="Van Rooyen", first="Erik" -- works correctly |
| `"Fleetwood, Tommy"` | `"Tommy Fleetwood"` | Straightforward | Works after comma-split and reorder |
| Unknown DG player | Not in GameBlazers roster | Player not owned | Not an error -- just no card to match. DataGolf has ~150 players; user may own 20-40 cards. |

**Recommended `parse_datagolf_name()` logic:**
```
Input: "Scheffler, Scottie"
1. Split on first comma: last="Scheffler", first="Scottie"
2. Strip suffixes from last: Jr., Sr., III, IV, II
3. Reconstruct as "first last" -> "Scottie Scheffler"
4. Pass through existing normalize_name() -> "scottie scheffler"
```

### Edge Case 3: API Returns Error or Empty Data

**Scenarios:**
- 401/403: Invalid or expired API key
- 429: Rate limited (5-minute timeout)
- 500/502/503: DataGolf server issues
- 200 with empty array: Tournament not started / no data yet
- Network timeout: VPS can't reach DataGolf

**Handling:**
- Log all errors with timestamp and HTTP status
- On cron failures: do NOT delete existing DB data. Last good fetch remains valid.
- On 401/403: alert user (log or email) that API key needs attention
- On empty response: log but do not treat as error -- may be between tournaments
- Implement basic retry: 1 retry after 30-second delay for 5xx errors only

### Edge Case 4: Mid-Week Field Changes

**Scenario:** Player withdraws (WD) after Tuesday fetch. Wednesday fetch has updated field.

**Handling:** Each fetch replaces the previous data for that event_id. The Wednesday fetch will not include the WD player, so their projection disappears. This is correct behavior -- the optimizer should not use projections for players not in the field.

### Edge Case 5: Opposite-Field Events / Multiple Tournaments

**Scenario:** Some weeks have two PGA TOUR events (main + opposite field).

**Handling:** The `tour` parameter distinguishes these (`pga` vs `opp`). For v1.2, only fetch `tour=pga` (the main event). The user plays GameBlazers which uses the main PGA TOUR event. If GameBlazers ever uses opposite-field events, add a second fetch with `tour=opp`.

### Edge Case 6: DraftKings Scoring vs GameBlazers Scoring

**Important:** DataGolf projects DraftKings fantasy points, but GameBlazers has its own scoring system (eagles +8, birdies +4, pars -0.5, etc. -- see PROJECT.md Context section). DraftKings scoring is different from GameBlazers scoring.

**However:** The projected DraftKings points serve as a reasonable proxy for relative player strength. A player projected to score highly on DraftKings will generally also score highly on GameBlazers -- the relative rankings are what matter for optimization, not the absolute point values. The optimizer uses `projected_score * multiplier` to rank cards, so even if the absolute numbers differ, the relative ordering drives correct optimization.

**Risk:** If DraftKings scoring heavily weights something GameBlazers does not (or vice versa), the ranking proxy breaks down. In practice, both scoring systems reward low scores and penalize high scores, so the correlation is strong.

**For v1.2:** Use DraftKings projected points directly as `projected_score`. Document this assumption. If the user notices ranking discrepancies, they can upload a manually-adjusted CSV instead.

---

## v1.2 MVP Definition

### Must Have (v1.2 Launch)

- [x] **PROJ-01: DataGolf API fetcher** -- HTTP client calling `fantasy-projection-defaults`, parsing response, handling errors
- [x] **PROJ-02: Cron scheduler** -- systemd timer running Tue + Wed mornings on Ubuntu 24.04 VPS
- [x] **PROJ-03: PostgreSQL storage** -- projections table storing player_name, dg_id, projected points, event metadata, fetch timestamp
- [x] **PROJ-04: Projection source selector** -- UI control to pick "DataGolf (from DB)" or "Upload CSV"
- [x] **PROJ-05: Stale data display** -- show event name, fetch date, and staleness warning when data is old
- [x] **Name normalization** -- convert DataGolf "Last, First" to match GameBlazers "First Last" via existing normalize_name pipeline

### Add After Validation (v1.2.x)

- [ ] **Manual fetch button** -- "Refresh Projections" in the UI; calls fetcher on demand
- [ ] **Fetch status dashboard** -- show last fetch time, player count, any errors
- [ ] **Unmatched player report for DataGolf source** -- surface which DataGolf players could not be matched to GameBlazers cards (reuse existing unmatched report pattern)

### Defer to v1.3+

- [ ] **Projection comparison view** -- side-by-side DataGolf vs CSV projections
- [ ] **Multi-source averaging** -- combine DataGolf + other sources (explicitly v2.0 per PROJECT.md)
- [ ] **DataGolf player list cross-reference** -- build dg_id-to-name mapping table

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Notes |
|---------|------------|---------------------|----------|-------|
| DataGolf API fetcher (PROJ-01) | HIGH | MEDIUM | P1 | Core feature; everything else depends on it |
| PostgreSQL storage (PROJ-03) | HIGH | MEDIUM | P1 | Required for persistence; design schema for v1.3 |
| Name normalization (DG format) | HIGH | LOW | P1 | Without this, DataGolf data is useless |
| Projection source selector (PROJ-04) | HIGH | MEDIUM | P1 | User-facing feature; the visible deliverable |
| Stale data display (PROJ-05) | MEDIUM | LOW | P1 | Prevents user confusion with old data |
| Cron scheduler (PROJ-02) | MEDIUM | LOW | P1 | Automation; but manual fetch works without it |
| Manual fetch button | MEDIUM | LOW | P2 | Convenience; cron covers the main case |
| Fetch status dashboard | LOW | LOW | P2 | Nice to have; builds trust in automation |
| Unmatched player report (DG) | MEDIUM | LOW | P2 | Reuses existing pattern from v1.0 |
| Projection comparison view | LOW | MEDIUM | P3 | Defer; not needed for core workflow |

---

## Competitor Feature Analysis (DFS Optimizers with DataGolf)

| Feature | FantasyCruncher | SaberSim | Daily Fantasy Fuel | Our Approach (v1.2) |
|---------|----------------|----------|--------------------|--------------------|
| DataGolf integration | Uses DataGolf as one of many projection sources | Uses their own projections | Uses DataGolf and others | Single DataGolf source via API |
| Projection source selection | Multiple sources with weighting sliders | Pre-built model, no user selection | Source toggles | Binary: DataGolf or CSV upload |
| Auto-fetch projections | Yes, background updates | Yes | Yes | Cron-based Tue/Wed fetch |
| Player name matching | Built-in cross-reference databases | Internal player IDs | Internal IDs | Name normalization (normalize_name) |
| Stale data handling | Auto-updates; always current | Always current | Manual refresh | Staleness label with event name + age |

**Key insight:** Major DFS optimizers use internal player ID databases to avoid name matching entirely. For a single-user app like GBGolfOptimizer, name normalization is sufficient and far simpler.

---

## API Integration Checklist (Implementation Guide)

### Before First API Call
1. Obtain Scratch Plus API key from [datagolf.com/subscribe](https://datagolf.com/subscribe)
2. Store API key as environment variable `DATAGOLF_API_KEY`
3. Add `DATAGOLF_API_KEY` to `.env.example` (without the actual value) and `.gitignore`

### First API Call (Discovery)
1. Call `fantasy-projection-defaults` with `tour=pga&site=draftkings&slate=main&file_format=json`
2. **Log the FULL raw response** -- exact field names matter for schema design
3. Document actual field names vs the extrapolated names in this document
4. Update the Pydantic model and DB schema based on actual response

### Expected API URL
```
https://feeds.datagolf.com/preds/fantasy-projection-defaults?tour=pga&site=draftkings&slate=main&file_format=json&key={DATAGOLF_API_KEY}
```

### What We Need from the Response (Minimum)
- `player_name` (string) -- to match against GameBlazers roster
- `dg_id` (int) -- for future cross-referencing
- Projected fantasy points field (float) -- the actual projection value
- Any event/tournament identifier -- to detect staleness

### What We Ignore from the Response
- `salary` -- GameBlazers has its own salary system
- `ownership` -- irrelevant for GameBlazers (no shared player pool)
- Point breakdowns (streak_pts, bogey_free_pts, etc.) -- only need the total projection

---

## Sources

- [DataGolf API Access Documentation](https://datagolf.com/api-access) -- endpoint parameters, authentication
- [DataGolf Raw Data Notes](https://datagolf.com/raw-data-notes) -- field naming conventions, player_name warning, event_id behavior
- [DataGolf FAQ](https://datagolf.com/frequently-asked-questions) -- projection timing, content release schedule
- [DataGolf Forum - PSA: API Rate Limits](https://forum.datagolf.com/t/psa-api-rate-limits/2511) -- 45 req/min, 5-min timeout
- [DataGolf Site Updates](https://datagolf.com/site-updates) -- fantasy-projection-defaults endpoint launch (May 2022)
- [DataGolf Historical DFS Sample (JSON)](https://feeds.datagolf.com/historical-dfs-data/sample?site=draftkings&file_format=json) -- verified response structure with actual field names
- [DataGolf Historical DFS Sample (CSV)](https://feeds.datagolf.com/historical-dfs-data/sample?site=draftkings&file_format=csv) -- verified CSV column headers
- [Unofficial Python Library (coreyjs/data-golf-api)](https://github.com/coreyjs/data-golf-api) -- endpoint path confirmation, parameter options
- [DataGolf Fantasy Projections Page](https://datagolf.com/fantasy-projections) -- column pattern verification, wave split info

---
*Feature research for: v1.2 DataGolf API Integration*
*Researched: 2026-03-25*
