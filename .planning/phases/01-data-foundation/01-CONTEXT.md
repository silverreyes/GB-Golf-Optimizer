# Phase 1: Data Foundation - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Parse the user's GameBlazers roster CSV and weekly projections CSV into validated, projection-enriched card objects ready for the optimizer. Applies filtering rules ($0 salary, expired dates, no projection match), calculates effective values, loads contest config, and produces a standalone CLI validation command. Optimization logic is Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Player name matching
- Normalize before comparing: lowercase + trim whitespace (no punctuation stripping)
- If normalized names still don't match, card is excluded and reported
- Unmatched report shows the exact roster name that couldn't be matched (e.g., "No projection found for: Ludvig Åberg") so the user can fix their projections CSV

### Unmatched card handling
- Cards with no projection match are **excluded** from the optimizer pool entirely (not included with score=0)
- Exclusion report is a flat list, one card per row, with reason noted inline
- Three exclusion reasons surfaced: no projection found, $0 salary (not in tournament field), expired card

### Validation error behavior
- **Roster CSV format error** (wrong/missing columns, can't be parsed): fail immediately with a clear error message, no partial processing
- **Projections CSV bad row** (missing or non-numeric score): skip that row with a warning, continue loading the rest
- **Too few valid cards after filtering** (pool too small to build even one lineup): fail with a clear message before passing to the optimizer (e.g., "Only 4 valid cards found — Tips contest requires at least 6. Check your exclusion report.")

### Phase 1 interface
- Delivers a **Python module** (imported by Phase 2 optimizer) AND a **standalone CLI validation command**
- CLI command: `python -m gbgolf.data validate roster.csv projections.csv`
- Default output: summary (valid card count, total parsed, exclusion count) + exclusion report
- Verbose output (`--verbose` flag): also lists every valid card with its effective value (projected_score × multiplier)
- CLI also validates the contest config JSON — checks required fields are present and values are sensible

### Claude's Discretion
- Exact Python module structure and file layout
- Contest config JSON schema design (fields, nesting)
- How expired date parsing handles edge cases (invalid date formats)
- Specific error message wording

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — Phase 1 establishes the conventions

### Integration Points
- Phase 2 (Optimization Engine) imports the card objects and contest config produced by this phase
- Phase 3 (Web App) will expose the exclusion report and valid card data through the UI — the data structures defined here must be serializable

</code_context>

<specifics>
## Specific Ideas

- No specific references or UI references discussed — open to standard approaches for module layout and CLI output formatting

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-data-foundation*
*Context gathered: 2026-03-13*
