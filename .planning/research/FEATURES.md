# Feature Landscape

**Domain:** DFS Golf Lineup Optimizer (GameBlazers-specific)
**Researched:** 2026-03-14 (lock/exclude milestone update)
**Confidence:** HIGH for lock/exclude UX patterns (verified via web search); MEDIUM for broader ecosystem features

## Context

This analysis covers features found in mainstream DFS lineup optimizers (FantasyLabs, DraftKings Optimizer, SaberSim, FantasyCruncher, RotoGrinders, FantasyPros, Footballguys, Daily Fantasy Fuel, BlueCollarDFS) and maps them onto the GameBlazers-specific problem space. GameBlazers differs from DraftKings/FanDuel in several important ways:

- **Card-based system** with multipliers (1.0-1.5) rather than flat player salaries
- **Collection constraints** (Weekly/Core limits) in addition to salary caps
- **Duplicate player cards** at different multipliers/salaries — same golfer may appear multiple times with different card attributes
- **Cross-lineup card locking** — a card used in one lineup cannot appear in another
- **Two contest tiers** with different constraints and prize structures
- **Small user base** — single-user app, no multi-user concerns

These differences mean some standard DFS optimizer features are irrelevant, while others become more critical.

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| CSV roster upload and parsing | Core input mechanism; no other way to get card data in | LOW | Parse GameBlazers export format, handle $0 salary cards, duplicates. **DONE v1.0.** |
| Projections upload (CSV) | Second required input; optimizer is useless without projections | LOW | Simple name + projected_score format. **DONE v1.0.** |
| Optimal lineup generation | The entire point of the app | HIGH | ILP solver (PuLP) with salary, collection, and card-lock constraints. **DONE v1.0.** |
| Cash contest priority ordering | Cash contest has real money at stake; must get best cards first | MEDIUM | Solve Tips lineups first, then Intermediate Tee from remaining pool. **DONE v1.0.** |
| Salary cap enforcement | Lineups violating salary rules are invalid and cannot be entered | LOW | Min and max salary bounds per contest. **DONE v1.0.** |
| Collection constraint enforcement | Weekly/Core card limits are hard rules in GameBlazers | MEDIUM | Track collection type per card, enforce per-lineup limits. **DONE v1.0.** |
| Cross-lineup card locking | GameBlazers rule — same card cannot appear in multiple entries | MEDIUM | Remove used cards from pool after each lineup is generated. **DONE v1.0.** |
| Effective value display | Users need to see projected_score x multiplier, not raw projection | LOW | Simple calculation, but critical for understanding lineup quality. **DONE v1.0.** |
| Lineup display with key stats | Users need to see player, salary, multiplier, projected value per lineup | LOW | Clear table format. **DONE v1.0.** |
| Total lineup projected score | Users want to see total expected points per lineup | LOW | Sum of effective values. **DONE v1.0.** |
| Salary remaining / utilization | Shows how efficiently salary cap is used | LOW | Standard optimizer output. **DONE v1.0.** |
| Editable contest configuration | Contest rules change; users should not need code changes | LOW | JSON config file. **DONE v1.0.** |
| Error handling for bad CSV input | Users will upload wrong files or malformed CSVs | LOW | Clear error messages. **DONE v1.0.** |
| Player field filtering | Cards for players not in this week's tournament must be excluded | LOW | $0 salary, expired cards excluded. **DONE v1.0.** |
| Unmatched player report | Users need to know when projections don't match cards | LOW | Surfaces missing projection matches. **DONE v1.0.** |
| **Manual lock/exclude (session-scoped)** | Every mainstream DFS optimizer provides this; users expect to override the optimizer's choices based on their own judgment | MEDIUM | Users must be able to force cards/golfers in or out without re-uploading CSVs. **v1.1 target.** |

---

## Lock/Exclude Feature Deep Dive

This section details the expected behavior of lock/exclude based on verified research into DraftKings, FantasyPros, Footballguys, SaberSim, FTN Fantasy, and Daily Fantasy Fuel optimizer tools.

### Standard Industry Behavior (HIGH confidence)

All mainstream DFS optimizers share this core model:

- **Lock**: Forces the player/card into every generated lineup. Applies globally (all lineups), not per-lineup. Results in 100% exposure for that player.
- **Exclude**: Removes the player/card from the eligible pool entirely. No lineup will include them. Applies globally.
- **Re-optimize after lock/exclude**: Users set lock/exclude state, then click "Optimize" again. The optimizer respects constraints and regenerates lineups. Lock/exclude settings persist across re-optimize calls until explicitly cleared.
- **Clear/reset**: States are per-session. Starting a new upload (new roster/projections) resets all lock/exclude state. Some tools also offer a "Clear all" button.
- **Toggle pattern**: Lock/exclude state is typically a three-state toggle on each player row: Neutral (optimizer decides) → Locked → Excluded → Neutral.

### GameBlazers-Specific Distinction: Card Lock vs. Golfer Lock

Standard DFS tools lock "a player" because there is only one version of each player in the pool. GameBlazers has duplicate cards for the same golfer with different multipliers/salaries. This creates two distinct lock types that the GB optimizer must support, and that no standard DFS tool documents:

| Lock Type | What It Means | ILP Implementation |
|-----------|---------------|-------------------|
| **Lock a specific card** | Force this exact card (by unique card ID/row) into the optimizer. The optimizer must assign it to exactly one lineup. | Add constraint: `sum of assignment vars for this card across all lineups >= 1`. Card's other attributes (multiplier, salary, collection type) remain in play. |
| **Lock a golfer by name** | Require that at least one of this golfer's cards appears somewhere across the generated lineups (or in a specific lineup). The optimizer picks which card. | Add constraint: `sum of assignment vars for all cards belonging to this golfer >= 1`. Lets optimizer pick best card. |
| **Exclude a specific card** | Remove this exact card from the eligible pool for all lineups. | Set the card's binary variable to 0, or remove it from the model entirely before solving. |
| **Exclude a golfer by name** | Remove all of this golfer's cards from consideration. No lineup may include them. | Set all binary variables for all cards belonging to this golfer to 0. |

The lock-golfer behavior is a natural fit for the user's workflow: "I want Scottie Scheffler in a lineup, but I don't care which of my Scheffler cards the optimizer picks — just use the best one."

### Scope: Session-Scoped State

Lock/exclude settings persist only within the current upload session:

- State initializes to all-neutral on CSV upload.
- User adjusts locks/excludes in the UI.
- Clicking "Optimize" runs the solver with current lock/exclude constraints.
- User can adjust and re-optimize multiple times without re-uploading.
- New CSV upload (roster or projections) resets all lock/exclude state.

This is the standard behavior across all major DFS optimizers (HIGH confidence).

### UX Pattern: Where Lock/Exclude Lives

Based on FantasyPros, Footballguys, and Daily Fantasy Fuel patterns:

- Lock/exclude controls appear in the **player pool table** (the list of available cards/players), not in the output lineup display.
- Each row in the player pool has a lock icon and an exclude icon (or a single three-state toggle).
- The controls are accessible **before** and **after** optimization. Users can see which cards were used in lineups and then lock/exclude based on that output.
- After adjusting, users click the same "Optimize" button to regenerate.

### What Standard DFS Tools Don't Have That GB Optimizer Needs

| Gap | Why It Matters | How to Handle |
|-----|---------------|---------------|
| Lock a specific card (not just a player name) | GB has multiple cards per golfer | Support both card-level and golfer-level locking |
| Visual distinction of "already-used" cards | After optimization, user wants to see which cards were assigned | Show card assignment in the player pool table, not just in the lineup output |
| Card pool scoping across contests | Tips uses cards first; lock/exclude must be aware of cross-contest card allocation | Lock constraints interact with the cross-contest card-locking already in the ILP |

---

## Differentiators

Features that set product apart from manually building lineups or using basic spreadsheets.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Card-vs-card comparison for same player | When user has multiple cards for the same player, show which card is the better value | LOW | Unique to GameBlazers card system; simple effective_value/salary calc. **v1.1 target.** |
| Lineup export / copy-paste format | Quickly copy lineup into GameBlazers entry form | LOW | Reduces manual re-entry friction. **v1.1 target.** |
| Contest configuration editor in web UI | No need to edit a JSON file manually | MEDIUM | Remove file-editing step entirely. **v1.1 target.** |
| Sensitivity analysis ("how close") | Show which players nearly made the lineup and by how much | MEDIUM | Uses LP shadow prices or re-solve with forced swaps. Helps manual overrides. |
| Remaining card pool visualization | After Tips lineups are built, show what cards remain for Intermediate Tee | LOW | Helps users understand what the non-cash optimizer is working with. |
| Projection adjustment interface | Let users tweak individual projections in the browser before optimizing | MEDIUM | Faster than re-uploading CSV for 2-3 player adjustments. |
| Historical results tracking | Upload actual tournament results to see how optimized lineups would have scored | MEDIUM | Feedback loop for improving projection sourcing. |
| Ownership percentage integration | Factor in projected field ownership to find contrarian plays | HIGH | Less relevant for GameBlazers cash games. Future only. |
| Lineup diversity / exposure limits | Cap how often a single golfer appears across all lineups | MEDIUM | Standard DFS feature. **v1.1 target (ADV-01).** |
| Diversity constraints | Enforce minimum player differences between lineups | MEDIUM | Prevents 3 near-identical Tips lineups. **v1.1 target (ADV-02).** |

---

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Per-lineup lock/exclude | Standard DFS tools don't offer this; it's complex to implement and rarely needed. The optimizer will naturally use different cards across lineups due to cross-lineup card locking. | Global lock/exclude is sufficient. If user needs lineup-specific control, they can re-optimize with different lock states. |
| Automatic projection scraping | Projections come from multiple sites; scraping is fragile, legally questionable, and the user already averages them manually | CSV upload; user maintains control over projection methodology |
| GameBlazers scraping for contest data | Contest parameters change infrequently; scraping adds complexity for minimal value | Editable config file; update manually when contests change |
| User accounts and authentication | Single-user app; no need for login, profiles, or multi-tenancy | Serve openly or with a simple shared secret |
| RUC optimization | Different optimization problem with different objectives; out of scope | Could be a v2 feature |
| Real-time odds / live scoring integration | Optimizer runs pre-tournament; live scoring adds no optimization value | Users check live scores on GameBlazers directly |
| Stacking / correlation-based construction | Golf is an individual sport; stacking is a team-sport DFS concept | Ignore entirely |
| Persisted lock/exclude state across sessions | State is meaningless next week (different field, different cards) | Session-scope only; resets on new upload |
| Monte Carlo simulation | Adds significant complexity; projection quality is the user's responsibility | Deterministic optimization using uploaded projections |
| GPP vs Cash mode toggle | GameBlazers has specific contest types with fixed rules; generic DFS modes don't map cleanly | Contest-specific optimization driven by config file |

---

## Feature Dependencies

```
CSV Roster Parsing
    └──requires──> Player Field Filtering
                       └──requires──> Optimal Lineup Generation (ILP)
                                          └──enhances──> Lock a Specific Card
                                          └──enhances──> Lock a Golfer by Name
                                          └──enhances──> Exclude a Card
                                          └──enhances──> Exclude a Golfer

Projections Upload --> Effective Value Calculation --> Optimal Lineup Generation

Contest Configuration --> Salary Cap Enforcement --> Optimal Lineup Generation
Contest Configuration --> Collection Constraint Enforcement --> Optimal Lineup Generation

Optimal Lineup Generation (Tips)
    └──requires──> Cross-Lineup Card Locking --> Optimal Lineup Generation (Intermediate Tee)

Manual Lock/Exclude State (session)
    └──modifies──> Optimal Lineup Generation (ILP constraints)
    └──requires──> Player Pool Display (UI surface for controls)

Player Pool Display
    └──enhances──> Card-vs-Card Comparison
    └──enhances──> Remaining Card Pool Visualization

Lineup Display --> Lineup Export
Exposure Limits --> Optimal Lineup Generation (adds per-player cap constraints)
Diversity Constraints --> Optimal Lineup Generation (adds minimum-difference constraints)
```

### Dependency Notes

- **Lock/exclude requires the player pool display**: Users need a visible table of cards to click on. The lock/exclude controls live in the player pool table, not the lineup output.
- **Lock a specific card interacts with cross-lineup card locking**: If a user locks card X into the optimizer, the ILP must still ensure card X is not double-assigned. The lock constraint adds a lower bound of 1 on that card's total assignments; the existing uniqueness constraint caps it at 1. Together they force exactly one assignment.
- **Lock a golfer by name does not pin a specific card**: The ILP must sum all assignment variables for that golfer and require the sum >= 1, while still allowing the optimizer to choose the best card. This is a sum-over-group constraint, not a pin on a single variable.
- **Exclude a golfer removes all that golfer's cards**: The ILP sets all binary variables for cards belonging to that golfer to 0 before solving (or equivalent). This is simpler than a constraint — just remove those cards from the eligible pool.
- **Session-scope dependency**: All lock/exclude state depends on the current session's uploaded roster. Clearing the roster resets lock/exclude. This is intentional — lock state from last week's cards is meaningless.

---

## MVP Definition for v1.1 (Manual Lock/Exclude Milestone)

### Launch With (v1.1 Core)

Minimum viable behavior for the lock/exclude milestone. Everything needed to validate the concept.

- [ ] **Exclude a golfer by name** — simplest case; removes all their cards from pool before ILP runs. No solver change needed, just pre-filter.
- [ ] **Lock a specific card** — force a specific card into the optimizer; ILP lower-bound constraint on that card's assignment variable. Requires card identity in the UI.
- [ ] **Lock a golfer by name** — require at least one of this golfer's cards appears in a lineup; ILP sum-over-group constraint.
- [ ] **Exclude a specific card** — remove this exact card from the eligible pool; pre-filter before ILP.
- [ ] **Session-scoped state** — lock/exclude resets on new CSV upload; persists across re-optimize calls within a session.
- [ ] **Lock/exclude controls in player pool table** — lock icon and exclude icon (or toggle) on each card row in the pre-optimize view.
- [ ] **Re-optimize with current lock/exclude state** — clicking "Optimize" always uses current lock/exclude constraints.
- [ ] **Visual feedback in lineup output** — locked cards are visually marked in the output so users can confirm their constraints took effect.

### Add After Validation (v1.1+)

- [ ] **"Clear all" button** — clears all lock/exclude state without re-uploading.
- [ ] **Lock/exclude state summary** — small section above the optimizer button showing "3 cards locked, 2 golfers excluded" to confirm what's active.
- [ ] **Card-vs-card comparison view** — side-by-side display of multiple cards for same player (USBL-02).
- [ ] **Lineup export** — copy to clipboard or download as CSV (USBL-04).

### Future Consideration (v1.2+)

- [ ] **Exposure limits** — cap how often a single golfer appears across all lineups (ADV-01).
- [ ] **Diversity constraints** — enforce minimum player differences between lineups (ADV-02).
- [ ] **Sensitivity analysis** — show how lineup changes if a player's projection shifts (ADV-03).
- [ ] **Contest configuration editor in web UI** (USBL-01) — lower priority than lock/exclude usability.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Exclude a golfer by name | HIGH | LOW (pre-filter, no ILP change) | P1 |
| Exclude a specific card | HIGH | LOW (pre-filter, no ILP change) | P1 |
| Lock a specific card | HIGH | MEDIUM (ILP lower-bound constraint) | P1 |
| Lock a golfer by name | HIGH | MEDIUM (ILP sum-over-group constraint) | P1 |
| Session-scoped lock/exclude state | HIGH | LOW (Flask session or in-memory state) | P1 |
| Player pool table with lock/exclude controls | HIGH | MEDIUM (UI redesign to show card pool) | P1 |
| Visual confirmation in lineup output | MEDIUM | LOW (CSS class / icon on locked cards) | P1 |
| "Clear all" reset | MEDIUM | LOW | P2 |
| Lock/exclude summary above optimizer button | MEDIUM | LOW | P2 |
| Card-vs-card comparison | MEDIUM | LOW | P2 |
| Lineup export | MEDIUM | LOW | P2 |
| Exposure limits (ADV-01) | MEDIUM | MEDIUM | P3 |
| Diversity constraints (ADV-02) | MEDIUM | HIGH | P3 |
| Sensitivity analysis (ADV-03) | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.1 launch
- P2: Should have, add when core is working
- P3: Nice to have, future milestone

---

## Competitor Feature Analysis

| Feature | FantasyPros | Footballguys | Daily Fantasy Fuel | Our Approach |
|---------|-------------|--------------|-------------------|--------------|
| Lock player | Lock icon per row, applies to all lineups | Lock icon, 100% exposure in all lineups | Lock in core players, then optimize | Same: lock applies globally across all lineups |
| Exclude player | X icon per row, removes from pool | Exclude toggle, removes from pool | Toggle to exclude | Same: exclude removes from eligible pool entirely |
| Lock granularity | Player name (one version per player in DK/FD) | Player name | Player name | Both card-level AND golfer-level (GameBlazers-specific) |
| Re-optimize after change | Click Optimize button again | Click Optimize button again | Click Optimize button again | Same: same Optimize button, reads current lock/exclude state |
| Reset state | Page refresh or manual toggle | Clear settings | Reload / new slate | Session reset on new CSV upload; also "Clear all" button |
| State persistence | Per-page-session | Per-session | Per-slate | Session-scoped, reset on new CSV upload |
| Per-lineup lock | Not offered by any major tool | Not offered | Not offered | Not building this (anti-feature) |
| Exposure % (partial lock) | Offered as advanced feature | Offered as exposure cap | Offered | Future consideration (ADV-01), not v1.1 |

---

## Sources

- FantasyPros DFS Optimizer support documentation (verified via web search 2026-03-14). Confidence: HIGH.
  - https://support.fantasypros.com/hc/en-us/articles/115001366668
  - https://support.fantasypros.com/hc/en-us/articles/360023879153
- Footballguys DFS Multi Lineup Optimizer Quick Start Guide (verified via web search 2026-03-14). Confidence: HIGH.
  - https://www.footballguys.com/article/guide-dfs-lineup-optimizer
- Daily Fantasy Fuel PGA optimizer feature summary (web search 2026-03-14). Confidence: MEDIUM.
  - https://www.dailyfantasyfuel.com/golf/
- SaberSim golf optimizer features (web search 2026-03-14). Confidence: MEDIUM.
  - https://www.sabersim.com/golf/optimizer
- FTN Fantasy PGA optimizer (web search 2026-03-14). Confidence: MEDIUM.
  - https://ftnfantasy.com/dfs/pga/optimizer
- Exposure percentage behavior verified from multiple sources (DraftKings, FantasyPros, Footballguys). Confidence: HIGH.
- GameBlazers-specific constraints sourced from PROJECT.md. Confidence: HIGH.

---
*Feature research for: DFS Golf Lineup Optimizer (GameBlazers) — Lock/Exclude Milestone*
*Researched: 2026-03-14*
