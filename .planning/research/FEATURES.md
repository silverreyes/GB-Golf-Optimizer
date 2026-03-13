# Feature Landscape

**Domain:** DFS Golf Lineup Optimizer (GameBlazers-specific)
**Researched:** 2026-03-13
**Confidence:** MEDIUM (based on training data knowledge of DFS optimizer ecosystem; web search unavailable for verification)

## Context

This analysis covers features found in mainstream DFS lineup optimizers (FantasyLabs, DraftKings Optimizer, SaberSim, FantasyCruncher, RotoGrinders, etc.) and maps them onto the GameBlazers-specific problem space. GameBlazers differs from DraftKings/FanDuel in several important ways:

- **Card-based system** with multipliers (1.0-1.5) rather than flat player salaries
- **Collection constraints** (Weekly/Core limits) in addition to salary caps
- **Duplicate player cards** at different multipliers/salaries
- **Cross-lineup card locking** -- a card used in one lineup cannot appear in another
- **Two contest tiers** with different constraints and prize structures
- **Small user base** -- single-user app, no multi-user concerns

These differences mean some standard DFS optimizer features are irrelevant, while others become more critical.

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| CSV roster upload and parsing | Core input mechanism; no other way to get card data in | Low | Parse GameBlazers export format, handle $0 salary cards, duplicates |
| Projections upload (CSV) | Second required input; optimizer is useless without projections | Low | Simple name + projected_score format |
| Optimal lineup generation | The entire point of the app | High | ILP solver (PuLP/OR-Tools) with salary, collection, and card-lock constraints |
| Cash contest priority ordering | Cash contest has real money at stake; must get best cards first | Medium | Solve Tips lineups first, then Intermediate Tee from remaining pool |
| Salary cap enforcement | Lineups violating salary rules are invalid and cannot be entered | Low | Min and max salary bounds per contest |
| Collection constraint enforcement | Weekly/Core card limits are hard rules in GameBlazers | Medium | Track collection type per card, enforce per-lineup limits |
| Cross-lineup card locking | GameBlazers rule -- same card cannot appear in multiple entries | Medium | Remove used cards from pool after each lineup is generated |
| Effective value display | Users need to see projected_score x multiplier, not raw projection | Low | Simple calculation, but critical for understanding lineup quality |
| Lineup display with key stats | Users need to see player, salary, multiplier, projected value per lineup | Low | Clear table format showing each lineup's composition |
| Total lineup projected score | Users want to see total expected points per lineup | Low | Sum of effective values |
| Salary remaining / utilization | Shows how efficiently salary cap is used | Low | Standard optimizer output |
| Editable contest configuration | Contest rules change; users should not need code changes | Low | JSON/YAML config file for salary caps, roster sizes, collection limits |
| Error handling for bad CSV input | Users will upload wrong files or malformed CSVs | Low | Clear error messages for missing columns, bad data |
| Player field filtering | Cards for players not in this week's tournament ($0 salary or missing from projections) must be excluded | Low | Filter before optimization |

## Differentiators

Features that set product apart from manually building lineups or using basic spreadsheets.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-lineup correlation awareness | When generating 3 Tips lineups, diversify player exposure rather than 3 near-identical lineups | High | Standard in DFS optimizers; prevents overexposure to one player. Implement via constraints that limit player appearances across lineups, or by iteratively removing top-picked players |
| Card-vs-card comparison for same player | When user has multiple cards for the same player (different multipliers/salaries), show which card is the better value | Low | Unique to GameBlazers card system; simple effective_value / salary calculation |
| Lineup export / copy-paste format | Let users quickly copy lineup into GameBlazers entry form | Low | Reduces manual re-entry friction |
| Sensitivity analysis ("how close") | Show which players nearly made the lineup and by how much | Medium | Helps users make manual swaps with confidence; uses LP shadow prices or re-solve with forced swaps |
| Manual player lock/exclude | Let users force a specific card into a lineup or exclude a player entirely | Medium | Common in all DFS optimizers; users have "gut feel" overrides |
| Remaining card pool visualization | After Tips lineups are built, show what cards remain for Intermediate Tee | Low | Helps users understand what the non-cash optimizer is working with |
| Projection adjustment interface | Let users tweak individual projections in the browser before optimizing | Medium | Faster than re-uploading CSV; users often want to adjust 2-3 players based on late news |
| Historical results tracking | Upload actual tournament results to see how optimized lineups would have scored | Medium | Feedback loop for improving projection sourcing over time |
| Ownership percentage integration | Factor in projected field ownership to find contrarian plays for GPP-style strategy | High | Less relevant for GameBlazers cash games but valuable for non-cash contest |
| Lineup diversity controls | Set minimum/maximum exposure per player across all lineups | Medium | Standard DFS feature; prevents putting all eggs in one basket |

## Anti-Features

Features to explicitly NOT build in v1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Automatic projection scraping | Projections come from multiple sites (DataGolf, FantasyNational, etc.); scraping is fragile, legally questionable, and the user already averages them manually | CSV upload is the right approach; user maintains control over projection methodology |
| GameBlazers scraping for contest data | Contest parameters change infrequently; scraping adds complexity and brittleness for minimal value | Editable config file; update manually when contests change |
| User accounts and authentication | Single-user app; no need for login, profiles, or multi-tenancy | Serve the app openly or with a simple shared secret if needed |
| RUC (Recycling Useless Cards) optimization | Different optimization problem with different objectives; out of scope per project definition | Could be a v2 feature if the core optimizer proves useful |
| Mobile-native app | Web app works on mobile browsers; native app adds huge complexity for a single-user tool | Responsive CSS ensures mobile browser usability |
| Real-time odds / live scoring integration | Optimizer runs pre-tournament; live scoring adds complexity with no optimization value | Users can check live scores on GameBlazers directly |
| Stacking / correlation-based lineup construction | Golf is an individual sport; stacking (grouping correlated players) is a team-sport DFS concept that does not apply | Ignore entirely; golf DFS correlation is minimal |
| Social features (sharing lineups, leaderboards) | Single-user tool; no audience for social features | Not applicable |
| Bankroll management / bet sizing | Out of scope for a lineup optimizer; this is a contest entry tool, not a bankroll tracker | Users manage their own contest entries |
| Monte Carlo simulation for projections | Adds significant complexity; projection quality is the user's responsibility via their manual averaging process | Simple deterministic optimization using uploaded projections |
| GPP (tournament) vs Cash game mode toggle | GameBlazers has specific contest types (Tips = cash, Intermediate Tee = non-cash) with fixed rules; generic DFS modes don't map cleanly | Contest-specific optimization driven by config file |

## Feature Dependencies

```
CSV Roster Parsing --> Player Field Filtering --> Optimal Lineup Generation
Projections Upload --> Effective Value Calculation --> Optimal Lineup Generation
Contest Configuration --> Salary Cap Enforcement --> Optimal Lineup Generation
Contest Configuration --> Collection Constraint Enforcement --> Optimal Lineup Generation
Optimal Lineup Generation (Tips) --> Cross-Lineup Card Locking --> Optimal Lineup Generation (Intermediate Tee)
Optimal Lineup Generation --> Lineup Display with Stats
Optimal Lineup Generation --> Remaining Card Pool Visualization
Lineup Display --> Lineup Export / Copy-Paste
Manual Player Lock/Exclude --> Optimal Lineup Generation (modifies constraints)
Projection Adjustment Interface --> Effective Value Calculation (modifies inputs)
Multi-Lineup Correlation Awareness --> Optimal Lineup Generation (adds diversity constraints)
```

Key ordering insight: The dependency chain is strictly linear for the core flow. CSV parsing and projections must work before optimization. Tips must solve before Intermediate Tee. Display comes after generation. All differentiator features either modify inputs to or add constraints on the core optimization -- they can be layered on incrementally.

## MVP Recommendation

**Prioritize (Phase 1 -- Core Optimizer):**
1. CSV roster upload and parsing (table stakes, Low complexity)
2. Projections upload (table stakes, Low complexity)
3. Contest configuration file (table stakes, Low complexity)
4. Player field filtering (table stakes, Low complexity)
5. Optimal lineup generation with all constraints (table stakes, High complexity -- this is the core)
6. Cash-first priority ordering (table stakes, Medium complexity)
7. Cross-lineup card locking (table stakes, Medium complexity)
8. Lineup display with effective values and stats (table stakes, Low complexity)

**Prioritize (Phase 2 -- Usability):**
1. Card-vs-card comparison for same player (differentiator, Low complexity, high unique value)
2. Manual player lock/exclude (differentiator, Medium complexity, high user demand)
3. Remaining card pool visualization (differentiator, Low complexity)
4. Lineup export / copy-paste (differentiator, Low complexity)
5. Projection adjustment interface (differentiator, Medium complexity)

**Prioritize (Phase 3 -- Advanced Optimization):**
1. Multi-lineup correlation / diversity controls (differentiator, High complexity, big impact on lineup quality)
2. Sensitivity analysis (differentiator, Medium complexity)

**Defer indefinitely:**
- Historical results tracking (nice to have but not core to optimization)
- Ownership percentage integration (minimal value for GameBlazers ecosystem)

## Complexity Notes

- **High complexity items** are the ILP solver setup (core optimizer) and multi-lineup diversity. The solver is the heart of the product and will take the most development time, but it is well-supported by PuLP/OR-Tools. Diversity constraints add mathematical complexity to an already-constrained optimization problem.
- **Medium complexity items** involve UI interactivity (lock/exclude, projection tweaks) or constraint tracking (collection limits, card locking across lineups).
- **Low complexity items** are primarily data parsing, display, and simple calculations.

The highest-risk feature is the core optimizer itself -- getting the ILP formulation correct with salary caps, collection constraints, card locking, and multiplier-weighted values. Everything else layers on top of a working optimizer.

## Sources

- Training data knowledge of DFS optimizer tools (FantasyLabs, SaberSim, FantasyCruncher, DraftKings built-in optimizer, RotoGrinders). Confidence: MEDIUM -- these tools are well-established and their feature sets are stable, but I could not verify current feature states via web search.
- GameBlazers-specific constraints sourced from PROJECT.md. Confidence: HIGH -- directly from project documentation.
- Note: Web search was unavailable during this research. Feature landscape is based on training data knowledge of the DFS optimizer ecosystem as of early-mid 2025. Core DFS optimizer features are stable and unlikely to have changed significantly.
