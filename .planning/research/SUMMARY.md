# Project Research Summary

**Project:** GB Golf Optimizer v1.1 — Manual Lock/Exclude Milestone
**Domain:** ILP-based DFS golf lineup optimizer (GameBlazers-specific)
**Researched:** 2026-03-14
**Confidence:** HIGH

## Executive Summary

The GB Golf Optimizer v1.0 is a stateless Flask + PuLP app that parses two CSVs (roster and projections), runs an ILP solve, and renders lineups in a single request-response cycle. The v1.1 milestone adds manual lock/exclude controls — the single most universal feature in all mainstream DFS optimizers. Research confirms the feature is well-understood in the industry, but GameBlazers' card-based system with duplicate golfer cards at different multipliers introduces two distinctions standard tools never have to address: card-level lock/exclude versus golfer-level lock/exclude. These distinctions must be built into the data model, ILP constraint layer, and UI from day one — they cannot be bolted on after the fact.

The recommended implementation approach is a hidden-field serialization architecture: valid cards are serialized to JSON in a hidden form field on the results page, and a new `/reoptimize` POST route deserializes them, applies lock/exclude constraints, and re-runs the ILP without requiring file re-upload. This adds zero new dependencies to the existing stack (Flask, PuLP, Jinja2, Pydantic v2) and stays consistent with the app's established stateless POST/render pattern. Flask's built-in session cookie is sufficient for the lock/exclude state payload (well under the 4KB limit), but the architecture research recommends hidden fields for the card data itself to avoid the cookie size risk entirely.

The critical risk in this milestone is constraint correctness in the multi-lineup sequential loop. The optimizer already tracks used cards across lineups to prevent cross-contest card reuse. Lock constraints must interact correctly with this mechanism: a card-level lock can only apply once (the card is consumed after assignment), while a golfer-level lock means "any card for this player must appear somewhere." Getting this semantics distinction wrong produces silently wrong lineups. Pre-solve constraint validation (salary feasibility, collection limit checks, conflict detection between lock and exclude) must ship alongside the lock feature itself, not as a follow-up.

---

## Key Findings

### Recommended Stack

No new dependencies are required for this milestone. The existing Flask 3.x, PuLP 2.x, Jinja2, and Pydantic v2 stack handles all three feature areas without addition. Flask's built-in signed-cookie session stores the lock/exclude identifier sets (worst-case ~600 bytes, well within the 4KB limit). PuLP's `+=` constraint API natively supports the two lock patterns needed. HTML checkboxes plus standard form POST replaces any need for HTMX or JavaScript frameworks.

The one candidate addition — `flask-session` with filesystem backend — was researched and explicitly rejected. The locked card identifier payload fits in a cookie. Storing full `Card` dataclass objects in session is the only scenario that would require server-side session storage, and that is an anti-pattern (dataclasses are not JSON-serializable).

**Core technologies:**
- **Flask built-in session**: Store lock/exclude identifiers — fits in cookie, zero new config
- **PuLP `+=` constraint API**: Inject `x[i] == 1` (card lock) and `lpSum >= 1` (golfer lock) before `solve()`
- **Jinja2 + HTML checkboxes**: Per-card toggle controls via standard form POST — no JS needed
- **Hidden form field (JSON)**: Carry serialized `valid_cards` between requests without re-upload or server storage

See `.planning/research/STACK.md` for full rationale, rejected alternatives, and session size calculations.

### Expected Features

All research into mainstream DFS optimizers (FantasyPros, Footballguys, Daily Fantasy Fuel, SaberSim, FTN Fantasy) confirms that lock/exclude is table stakes — a feature users expect without being asked. Every major tool implements it the same way: lock forces 100% exposure in all lineups, exclude removes from the eligible pool entirely, state persists within a session and resets on new upload.

**Must have (v1.1 core, P1):**
- Exclude a golfer by name — removes all their cards from pool before ILP (pre-filter, no constraint needed)
- Exclude a specific card — removes that exact card from pool before ILP (pre-filter)
- Lock a specific card — force this card into one lineup via `x[i] == 1` equality constraint
- Lock a golfer by name — require at least one of their cards via `lpSum >= 1` constraint
- Session-scoped state — lock/exclude resets on new CSV upload, persists across re-optimize calls
- Player pool table with lock/exclude controls — cards must be visible before users can act on them
- Visual confirmation in lineup output — locked cards marked so users can confirm constraints took effect

**Should have (P2, add after core works):**
- "Clear all" button — clears lock/exclude state without re-uploading
- Lock/exclude state summary — shows "3 cards locked, 2 golfers excluded" above the Optimize button
- Card-vs-card comparison view — side-by-side for same golfer with different multipliers
- Lineup export — copy to clipboard or download as CSV

**Defer to v1.2+:**
- Exposure limits (ADV-01) — cap how often a single golfer appears across all lineups
- Diversity constraints (ADV-02) — enforce minimum player differences between lineups
- Sensitivity analysis (ADV-03) — show how lineup changes if a projection shifts
- Contest configuration editor in web UI

See `.planning/research/FEATURES.md` for the full prioritization matrix, competitor analysis, and feature dependency graph.

### Architecture Approach

The v1.0 architecture is a single-route, single-template, stateless request-response loop. v1.1 extends this with one new route (`POST /reoptimize`) and one new data structure (`LockExcludeSpec`). The card data problem — files are temp files deleted after the first request — is solved by serializing `valid_cards` to JSON in a hidden form field on the results page. The `reoptimize` route deserializes these cards, parses the lock/exclude form fields into a `LockExcludeSpec`, and calls an extended `optimize()` function. A stable card key `(player, salary, multiplier, collection)` replaces the Python `id()` approach used in v1.0 for cross-lineup tracking, which breaks across serialization boundaries.

**Major components (new or modified):**
1. **`Card.card_key` property** — stable composite identity for lock/exclude tracking and serialization; replaces `id()` across requests
2. **`LockExcludeSpec` dataclass** — carries `lock_cards`, `lock_players`, `exclude_cards`, `exclude_players` into the optimizer with a `validate()` method for conflict detection
3. **`cards_to_json()` / `cards_from_json()`** — serialization helpers for the hidden form field transport
4. **`POST /reoptimize` route** — new route in `routes.py`; deserializes cards, applies spec, re-runs optimizer, re-renders results
5. **Extended `optimize()` and `_solve_one_lineup()`** — accept `LockExcludeSpec`, apply lock constraints before `solve()`, pre-filter excludes before ILP construction
6. **Lock/exclude panel in `index.html`** — checkboxes per card row, hidden `cards_json` field, Re-Optimize button

See `.planning/research/ARCHITECTURE.md` for the full data flow diagrams, component boundary tables, and the five architectural anti-patterns to avoid.

### Critical Pitfalls

The full pitfall catalog is in `.planning/research/PITFALLS.md`. The five most dangerous:

1. **Lock constraint leaking across the multi-lineup sequential loop** — Card-level locks can only apply once (card is consumed after assignment). Golfer-level locks may become infeasible in lineup 2 if the golfer has only one card. Distinguish these semantically before writing any ILP code; surface per-lineup lock resolution in the UI. Recovery is HIGH cost if deferred.

2. **Infeasibility with no useful error message** — When locked cards push salary over cap or exceed collection limits, the solver returns non-Optimal with no guidance. Pre-solve diagnostics (salary sum check, collection limit check, roster size check) must ship with the lock feature — never separately. O(n) Python checks, microsecond cost.

3. **Conflicting lock + exclude constraints causing silent infeasibility** — User locks a card and excludes the same golfer. ILP receives `x[i] == 1` and `sum == 0` for the same variable, which is immediately infeasible. Add `validate()` to `LockExcludeSpec`; add conflict detection as a pre-flight check before any solve attempt; disable conflicting UI states in the template.

4. **Card vs. golfer exclude ambiguity causing wrong results** — "Exclude" meaning exclude-one-card versus exclude-all-cards-for-this-golfer are distinct and must be labeled explicitly in the UI. Store in two separate sets in `LockExcludeSpec`. Implementing only one level silently produces wrong lineups.

5. **Stale locks after CSV re-upload due to `id()` usage** — Storing lock state by Python `id()` silently no-ops when new card objects are created on re-upload. Always use the stable composite key `(player, salary, multiplier, collection)`. Always clear lock/exclude state when a new upload succeeds and show a visible notice to the user.

---

## Implications for Roadmap

Based on combined research, a four-phase structure is recommended. All five critical pitfalls map to Phase 1 — they are architectural decisions that cannot be deferred without rework. The phases are strictly ordered by code dependency.

### Phase 1: Card Identity and Constraint Foundation

**Rationale:** The stable card key is a prerequisite for everything else. ILP constraint logic must be validated before UI is built around it — infeasibility behavior must be understood to design error messages. All five critical pitfalls require decisions made here (card vs. golfer semantics, conflict detection, pre-solve diagnostics, stable key scheme, session state reset on upload). Deferring any of these creates rework across all later phases.

**Delivers:** A working optimizer that correctly applies lock and exclude constraints, handles infeasibility with useful per-constraint diagnostics, and resets state on new upload. Testable via unit tests without any UI.

**Addresses features:** All four lock/exclude types (lock card, lock golfer, exclude card, exclude golfer); session-scoped state reset on upload; constraint validation pre-flight check.

**Avoids:**
- Pitfall 1 (lock leaking across sequential loop): Design card-lock vs. golfer-lock semantics before writing ILP code
- Pitfall 2 (infeasibility with no useful error): Include salary/collection pre-solve diagnostics alongside constraint injection
- Pitfall 3 (stale locks after re-upload): Use stable composite key from day one; clear state on new upload
- Pitfall 4 (card vs. golfer exclude ambiguity): Separate `excluded_card_keys` and `excluded_players` into distinct sets
- Pitfall 5 (conflicting lock + exclude): Add `validate()` to `LockExcludeSpec`; conflict detection as pre-flight check

**Implementation order within phase:**
1. Add `card_key` property to `Card` dataclass; update `optimize()` to use it instead of `id()`
2. Add `LockExcludeSpec` dataclass with `validate()` method
3. Extend `_solve_one_lineup()` with `locked_indices` parameter and pre-solve diagnostics
4. Extend `optimize()` with `spec: LockExcludeSpec | None = None`
5. Add session reset on new CSV upload in `routes.py`

### Phase 2: Serialization and Re-Optimize Route

**Rationale:** Once the optimizer correctly handles lock/exclude specs, the transport layer (serialization + new route) is straightforward. Serialization is a prerequisite for the route; the route is a prerequisite for the UI.

**Delivers:** A working `POST /reoptimize` endpoint that accepts hidden card JSON plus form-posted lock/exclude fields, runs the optimizer, and returns results. End-to-end flow testable without a polished UI.

**Uses:** Flask hidden form field pattern (no new dependencies); `cards_to_json()` / `cards_from_json()` helpers; existing `render_template` pattern from `routes.py`.

**Implements:** `POST /reoptimize` route in `routes.py`; serialization helpers in `models.py`.

**Avoids:** Storing full `Card` objects in session (anti-pattern per ARCHITECTURE.md); using Python `id()` in serialized data (breaks across requests).

### Phase 3: Template UI and Lock/Exclude Panel

**Rationale:** Pure presentation layer. All logic is validated; UI is wiring. Last in the core build because template work is fastest to iterate when the backend contract is stable.

**Delivers:** Player pool table with per-card lock/exclude checkboxes, hidden `cards_json` field, Re-Optimize button, visual markers on locked cards in lineup output, and lock/exclude state that re-renders correctly after re-optimize.

**Implements:** Architecture component "Lock/exclude panel in `index.html`"; hidden field; Re-Optimize form; loading overlay applied to `/reoptimize` form submit.

**Avoids:** Full-page scroll loss (accepted as MVP behavior per research; HTMX upgrade deferred).

### Phase 4: P2 Polish Features

**Rationale:** "Clear all" button, lock/exclude state summary, card-vs-card comparison, and lineup export are all low-complexity additions that require the Phase 3 UI to exist first but add no architectural risk. These can be done in any order.

**Delivers:** Improved UX for weekly use; surfaces card comparison data that is unique to GameBlazers' multi-card system; reduces re-entry friction via export.

**Addresses features:** "Clear all" button; lock/exclude state summary; card-vs-card comparison (USBL-02); lineup export (USBL-04).

### Phase Ordering Rationale

- Phases 1 through 3 are strictly ordered by code dependency: stable key → constraint logic → serialization → route → UI. No phase can be reordered without breaking the next.
- All five critical pitfalls require Phase 1 decisions. Deferring any of them creates rework in the ILP layer, the UI layer, and the state management layer simultaneously.
- Phase 4 polish features are independent of each other and can be done in any order or in parallel once Phase 3 is complete.
- ADV-01 (exposure limits) and ADV-02 (diversity constraints) are explicitly deferred to v1.2+ — they add significant ILP formulation complexity and are not required for the lock/exclude use case validated in v1.1.

### Research Flags

Phases with well-documented patterns (skip additional research):
- **Phase 2 (Serialization/Route):** Standard Flask route + JSON serialization; no unknowns beyond what is in ARCHITECTURE.md.
- **Phase 3 (Template UI):** Standard Jinja2/HTML form patterns; existing `index.html` is the guide.
- **Phase 4 (Polish):** All P2 features are low-complexity additions with established patterns.

Phases that should use the PITFALLS.md checklist as a test plan (no external research needed):
- **Phase 1 (ILP Constraint Foundation):** The multi-lineup sequential loop interaction with lock constraints is the highest-risk area. The "Looks Done But Isn't" checklist in PITFALLS.md should be used as the acceptance test plan for this phase before proceeding to Phase 2. All answers are in the existing codebase and PITFALLS.md — no external research needed.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Based on direct codebase inspection plus verified Flask/PuLP documentation. No new dependencies means no unknown API surfaces. |
| Features | HIGH | Lock/exclude behavior verified across FantasyPros, Footballguys, Daily Fantasy Fuel, SaberSim, FTN Fantasy. GameBlazers-specific card distinctions derived from PROJECT.md (first-party). |
| Architecture | HIGH | Based on direct codebase inspection of `engine.py`, `__init__.py`, `routes.py`, `models.py`, `index.html`. Hidden-field serialization is a standard, well-understood web pattern. |
| Pitfalls | HIGH | All five critical pitfalls are grounded in existing codebase analysis, ILP constraint theory, and verified DFS optimizer community patterns. Recovery costs are explicitly rated. |

**Overall confidence:** HIGH

The unusually high confidence across all areas reflects that this is a subsequent milestone on an existing, inspected codebase rather than greenfield research. The domain (ILP lock/exclude for DFS) is well-documented. The only genuine unknowns are UX edge cases (scroll position loss on full-page reload; per-lineup lock resolution display format), both of which are explicitly deferred or accepted as MVP behavior.

### Gaps to Address

- **Per-lineup lock resolution display format**: The architecture describes showing "Card locked in lineup 1; not available for lineup 2" but does not specify the exact UI treatment (inline notice vs. tooltip vs. separate section). Decide during Phase 3 template work.
- **Card-vs-card comparison layout**: The P2 feature is identified as valuable but the display format (side-by-side table, inline in card pool, or separate section) is not specified. Design during Phase 4.
- **"Clear all" scope**: Should "Clear all" clear only locks, only excludes, or both? Industry standard is both. Confirm during Phase 4 planning.

---

## Sources

### Primary (HIGH confidence)

- Existing codebase: `gbgolf/optimizer/engine.py`, `gbgolf/optimizer/__init__.py`, `gbgolf/web/routes.py`, `gbgolf/data/models.py`, `gbgolf/data/filters.py`, `gbgolf/web/templates/index.html` — constraint integration design, session state reset point, Card field structure, `id()` usage patterns
- PuLP technical documentation (coin-or.github.io/pulp) — `+=` constraint API, binary variable patterns, `LpStatus` values
- FantasyPros DFS Optimizer support documentation — lock/exclude UX behavior (verified via web search 2026-03-14)
- Footballguys DFS Multi Lineup Optimizer Quick Start Guide — lock/exclude behavior, exposure percentage (verified via web search 2026-03-14)

### Secondary (MEDIUM confidence)

- Flask Sessions — TestDriven.io — 4KB cookie limit, JSON serialization requirement, server-side session use cases
- Flask-Session 0.8.0 documentation — version confirmed, filesystem interface deprecated in 0.7.0
- Daily Fantasy Fuel PGA optimizer — lock/exclude feature patterns (web search 2026-03-14)
- SaberSim golf optimizer — lock/exclude feature patterns (web search 2026-03-14)
- FTN Fantasy PGA optimizer — lock/exclude feature patterns (web search 2026-03-14)
- RotoWire NFL DFS Optimizer FAQ, Fantasy Footballers — over-locked infeasibility patterns
- GitHub coin-or/pulp — current PuLP development status and CBC constraint handling

### Tertiary (LOW confidence)

- DFS community documentation on over-lock infeasibility — multiple sources agree, elevating to MEDIUM in aggregate; listed here for transparency about source type

---

*Research completed: 2026-03-14*
*Ready for roadmap: yes*
