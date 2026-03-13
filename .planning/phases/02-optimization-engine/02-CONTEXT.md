# Phase 2: Optimization Engine - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Given validated cards and contest config (from Phase 1), produce optimal lineup sets for The Tips (3 entries) and The Intermediate Tee (2 entries). Optimization logic only — no UI, no file I/O, no CSV parsing. Returns a structured result for Phase 3 to display.

</domain>

<decisions>
## Implementation Decisions

### Card and golfer uniqueness rules
- Each physical card is a distinct, consumable asset: once assigned to any lineup, it cannot appear in any other lineup across any contest
- The same golfer MAY appear in multiple lineup entries, as long as each appearance uses a different card
- Within a single lineup entry, a golfer may only appear ONCE (regardless of how many cards owned)
- Constraint is card-level (not golfer-level) for cross-lineup locking

### Multi-lineup strategy
- Sequential solve: build lineups one at a time — Tips lineup 1, Tips lineup 2, Tips lineup 3, then Intermediate Tee lineup 1, Intermediate Tee lineup 2
- After each lineup is solved, those cards are removed from the available pool before solving the next
- Same sequential approach applies to both contests
- Intermediate Tee solves from whatever cards remain after all 3 Tips lineups are assigned

### Partial results on infeasibility
- If a lineup cannot be built (infeasible), do NOT stop entirely — return however many lineups were successfully built
- Include an infeasibility notice for each lineup that could not be constructed
- Example: Tips lineup 3 fails → return lineup 1 and lineup 2, flag lineup 3 as infeasible

### Infeasibility message detail
- General message only: "Could not build lineup N for [Contest Name]"
- No diagnostic analysis of which specific constraint blocked it
- User can review their card pool and exclusion report manually

### Optimizer output structure
- Returns a dict grouped by contest name: `{'The Tips': [...], 'The Intermediate Tee': [...]}`
- Each value is a list of Lineup objects (or None/infeasibility notice for failed lineups)
- Full OptimizationResult includes:
  - `lineups`: dict grouped by contest name
  - `unused_cards`: list of Card objects not assigned to any lineup
  - `infeasibility_notices`: list of strings describing any lineups that could not be built

### Claude's Discretion
- ILP solver library choice (PuLP or OR-Tools — both mentioned in project constraints)
- Exact Lineup dataclass fields beyond the required set
- How ties in objective value are broken within a single solve

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Card` dataclass (`gbgolf/data/models.py`): player, salary, multiplier, collection, effective_value — direct input to optimizer
- `ContestConfig` dataclass (`gbgolf/data/config.py`): salary_min, salary_max, roster_size, max_entries, collection_limits — drives constraint formulation
- `ValidationResult` (`gbgolf/data/models.py`): valid_cards list is the optimizer's input pool
- `validate_pipeline()` (`gbgolf/data/__init__.py`): public API that Phase 2 calls to get the card pool

### Established Patterns
- Dataclasses for all data structures (not Pydantic models — those are boundary-only)
- Fail fast with clear ValueError messages for unrecoverable errors
- Return data structures from functions, no print/I/O in core logic

### Integration Points
- Phase 2 imports from `gbgolf.data`: `validate_pipeline()`, `Card`, `ContestConfig`
- Phase 3 web app imports from `gbgolf.optimizer` (new module): the `optimize()` function and result types
- Result must be serializable to JSON (for Phase 3 HTTP response)

</code_context>

<specifics>
## Specific Ideas

- Sequential solve is explicitly preferred over simultaneous ILP — simpler formulation, predictable lineup ordering
- Partial results are preferred over all-or-nothing — user wants to see whatever the optimizer could build even if one lineup fails

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-optimization-engine*
*Context gathered: 2026-03-13*
