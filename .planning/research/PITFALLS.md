# Domain Pitfalls

**Domain:** DFS Fantasy Golf Lineup Optimizer (GameBlazers-specific)
**Researched:** 2026-03-13
**Overall confidence:** MEDIUM (training data only -- web search unavailable; however, ILP formulation pitfalls and DFS optimizer patterns are well-established in operations research literature)

---

## Critical Pitfalls

Mistakes that cause incorrect lineups, silent bugs, or require architectural rewrites.

---

### Pitfall 1: Duplicate Player Cards Treated as Identical Players

**What goes wrong:** The optimizer treats two cards for "Scottie Scheffler" (one at 1.0x/$12,000, another at 1.2x/$10,500) as the same decision variable. The ILP either picks both or neither, or silently drops one. Since GameBlazers allows the same player with different multipliers/salaries, each card is a distinct selectable item.

**Why it happens:** Most DFS optimizer tutorials model one decision variable per player. GameBlazers breaks this assumption because the same player name appears on multiple cards with different attributes.

**Consequences:** Optimizer may produce infeasible lineups, silently discard high-value cards, or place the same physical golfer twice in a lineup (violating contest rules if only one instance of a golfer is allowed per lineup -- verify this rule).

**Prevention:**
- Model each *card* as its own binary decision variable, not each *player*. The variable is `x_card_id`, not `x_player_name`.
- Assign each card a unique ID during CSV parsing (e.g., row index or a composite key of Player+Multiplier+Salary+Collection).
- If GameBlazers rules say the same golfer cannot appear twice in one lineup (even on different cards), add a constraint: for each player name, sum of all card variables for that player <= 1 per lineup.
- Test explicitly with a roster CSV containing duplicate player cards.

**Detection:** Lineup contains the same golfer name twice. Or: optimizer produces fewer lineups than expected because it ran out of "players" when it actually had extra cards available.

**Which phase should address it:** Phase 1 (data model and CSV parsing). The card-level unique ID must be established before any optimizer work begins.

---

### Pitfall 2: Generating Near-Identical Multi-Lineups

**What goes wrong:** When generating 3 Tips lineups, the optimizer produces Lineup 1, then (after removing used cards) Lineup 2 is almost identical to Lineup 1 because the remaining card pool still favors the same top players. All 3 lineups converge on the same core of 4-5 golfers, reducing diversification value.

**Why it happens:** Greedy sequential optimization (solve lineup 1, remove cards, solve lineup 2) naturally converges. The card-locking constraint helps somewhat but does not guarantee meaningful diversity -- if a player has 3 cards at different multipliers, they could appear in all 3 lineups.

**Consequences:** For cash contests, some correlation is acceptable. But if 3 lineups all bust on the same golfer having a bad week, the user gets zero return from all 3 entries. The user expects the optimizer to spread risk.

**Prevention:**
- **Primary approach (card locking is already required):** Since each card can only appear in one lineup, this provides natural diversity. But verify: can the same golfer (different card) appear in multiple lineups? If yes, add an optional "golfer diversity" constraint limiting a golfer to at most N lineups out of 3.
- **Exposure limits:** Allow the user (or config) to set a max exposure percentage per golfer across lineups (e.g., "Scottie Scheffler in at most 2 of 3 lineups").
- **Iterative exclusion:** After solving lineup K, add a constraint that lineup K+1 must differ by at least M players from lineup K. This is modeled as: sum of shared players between lineup K and K+1 <= roster_size - M.
- **Solve all lineups simultaneously** in one ILP with cross-lineup constraints, rather than sequentially. This is more complex but produces globally optimal diverse sets.

**Detection:** Inspect generated lineups side by side. If 4+ of 6 golfer names are identical across lineups, diversity is insufficient.

**Which phase should address it:** Phase 2 (optimizer core). The sequential vs. simultaneous decision is architectural and hard to change later.

---

### Pitfall 3: Player Name Matching Failures Between Roster and Projections CSVs

**What goes wrong:** The roster CSV says "Byeong Hun An" but the projections CSV says "B.H. An" or "Ben An". The join fails silently, and that player gets no projection, effectively receiving a score of 0 and being excluded from lineups.

**Why it happens:** GameBlazers roster export and external projection sources (DataGolf, FantasyNational) use different name conventions. Common mismatches: initials vs. full names, suffixes (Jr., III), hyphens, accented characters (Jon Rahm vs. Jon Rahm), spaces in Asian names, nicknames.

**Consequences:** High-value players silently dropped from optimization. The user does not notice unless they manually check every player. Worst case: the best projected player is missing from all lineups.

**Prevention:**
- **Normalize both sides:** Strip whitespace, lowercase, remove periods/commas/suffixes before matching.
- **Fuzzy matching as fallback:** Use `rapidfuzz` or `thefuzz` (Python) with a threshold (e.g., 85% similarity) for names that do not exact-match after normalization.
- **Unmatched player report:** After the join, display a clear list of (a) roster players with no projection match and (b) projection players with no roster match. This is the single most important UX feature for data quality.
- **Manual alias mapping:** Maintain a small JSON/CSV alias file (e.g., "B.H. An" -> "Byeong Hun An") that grows over time as mismatches are discovered.
- **Never silently drop:** Any unmatched player should be flagged, not quietly excluded.

**Detection:** After merge, count matched vs. total. If matched < 80% of roster players who have non-zero salary, something is wrong.

**Which phase should address it:** Phase 1 (data ingestion). Name matching must be solved before the optimizer can produce trustworthy results. The unmatched report should be in the very first UI iteration.

---

### Pitfall 4: $0 Salary Cards Breaking the ILP Formulation

**What goes wrong:** Cards with $0 salary are included in the optimization. Since they cost nothing against the salary cap, the optimizer greedily selects them if they have any positive projection. But $0 salary means the player is not in the tournament field (or card is not activated) -- including them produces an invalid lineup.

**Why it happens:** The ILP treats $0 salary as "free" and will always prefer a $0 card with any positive projection over paying salary for another player. There is no constraint saying "salary must be > 0 to be eligible."

**Consequences:** Generated lineups contain players who are not playing that week. User submits lineup to GameBlazers and gets zero points for those slots.

**Prevention:**
- **Filter $0 salary cards during CSV parsing.** Remove them from the candidate pool entirely before optimization.
- **Also filter cards where the player has no projection** (not in the projections CSV at all). This catches inactive players even if their salary is non-zero.
- **Display filtered cards** in a "Not eligible this week" section so the user can verify the filtering is correct.
- **Edge case:** If a player legitimately has $0 salary but IS in the field (unlikely but verify with GameBlazers rules), the filter needs a toggle or the projections CSV acts as the source of truth for field membership.

**Detection:** Any lineup containing a $0 salary player. Any lineup where total salary is suspiciously far below the salary floor.

**Which phase should address it:** Phase 1 (data ingestion/filtering). This is a pre-processing step that must happen before cards reach the optimizer.

---

### Pitfall 5: Salary Cap Modeled as Upper Bound Only (Missing Floor)

**What goes wrong:** The ILP only constrains `sum(salary) <= max_salary` but GameBlazers also has a salary floor (e.g., $30,000 minimum for Tips). The optimizer finds a lineup of all cheap high-projection players that totals $22,000, which is invalid.

**Why it happens:** Most DFS optimizer tutorials (DraftKings, FanDuel) only have a salary cap (upper bound). GameBlazers has both a floor and a ceiling. Developers copy standard ILP formulations and forget the lower bound.

**Consequences:** Generated lineups are infeasible on GameBlazers. User cannot submit them.

**Prevention:**
- Model salary as a range constraint: `min_salary <= sum(salary_i * x_i) <= max_salary`
- In PuLP this is two separate constraints:
  ```python
  prob += lpSum(salary[i] * x[i] for i in cards) >= min_salary
  prob += lpSum(salary[i] * x[i] for i in cards) <= max_salary
  ```
- Load both floor and ceiling from the contest config file.
- Add a validation step post-solve that checks the lineup's total salary is within range.

**Detection:** Post-solve validation: check `min_salary <= lineup_salary <= max_salary`. If either fails, the constraint was misconfigured.

**Which phase should address it:** Phase 2 (optimizer core). Part of initial ILP formulation.

---

### Pitfall 6: Collection Constraints Modeled Incorrectly

**What goes wrong:** GameBlazers has "max 3 Weekly Collection cards" and "max 6 Core cards" per Tips lineup. The developer models this as `weekly_count + core_count = 6` (roster size), forgetting that these are upper bounds not exact counts, or misunderstanding that these are separate constraints on each collection type.

**Why it happens:** The constraint semantics are subtle. "Max 3 Weekly" means 0-3 Weekly cards are allowed. "Max 6 Core" in a 6-golfer lineup means all 6 could be Core. These are independent upper bounds, not a partition.

**Consequences:** Over-constrained model produces infeasible results or sub-optimal lineups. Under-constrained model produces lineups that violate GameBlazers rules.

**Prevention:**
- Model each collection type as an independent upper-bound constraint:
  ```python
  prob += lpSum(x[i] for i in cards if collection[i] == "Weekly") <= max_weekly
  prob += lpSum(x[i] for i in cards if collection[i] == "Core") <= max_core
  ```
- Parse the "Collection" column from the roster CSV. Verify the possible values (likely "Weekly" and "Core" but could include others like "Franchise" or "Rookie" -- check the CSV columns).
- The roster CSV has columns: Collection, Franchise, Rookie. Clarify whether "Franchise" and "Rookie" are separate collection types or boolean flags. This affects constraint modeling.
- Write unit tests with known card sets where the collection constraint is the binding constraint.

**Detection:** Generate a lineup and manually count Weekly vs. Core cards. If counts exceed configured limits, the constraint is wrong. If the optimizer reports "infeasible" when feasible lineups clearly exist, the constraint is likely over-specified.

**Which phase should address it:** Phase 1 (understand data model) and Phase 2 (optimizer constraints). The CSV column interpretation must be nailed down before constraints are coded.

---

### Pitfall 7: Card Locking Across Contests Not Enforced Globally

**What goes wrong:** The optimizer generates 3 Tips lineups correctly (no card reuse). Then it generates 2 Intermediate Tee lineups but does not exclude cards already used in Tips lineups. A card appears in both a Tips lineup and an Intermediate Tee lineup.

**Why it happens:** If Tips and Intermediate Tee optimizations are run as separate, independent ILP solves, the second solve does not know about the first solve's results unless explicitly told.

**Consequences:** User submits lineups that reuse the same card across contests. GameBlazers may reject the entry or the user unknowingly submits an invalid configuration.

**Prevention:**
- **Sequential with exclusion:** After solving Tips lineups, collect all used card IDs. Remove them from the candidate pool before solving Intermediate Tee lineups.
- **Single unified ILP:** Model all 5 lineups (3 Tips + 2 Intermediate Tee) in one optimization problem with cross-lineup constraints. More complex but guarantees global optimality and card exclusivity.
- **Post-solve validation:** After all lineups are generated, verify that every card ID appears at most once across all lineups.
- The PROJECT.md specifies "Cash contest optimized first" which implies sequential. This is the simpler approach and correct for prioritization (maximize cash lineup quality, then use leftovers).

**Detection:** Post-solve check: collect all card IDs from all lineups into a set. If `len(all_card_ids) != sum(lineup_sizes)`, there is a duplicate.

**Which phase should address it:** Phase 2 (optimizer core). The sequential approach is simpler and aligns with the "cash first" strategy. But the card exclusion between stages must be explicitly implemented, not assumed.

---

## Moderate Pitfalls

---

### Pitfall 8: Objective Function Uses Projection Instead of Effective Value

**What goes wrong:** The optimizer maximizes `sum(projection_i * x_i)` instead of `sum(projection_i * multiplier_i * x_i)`. A 1.0x card and a 1.5x card for the same player are valued identically.

**Why it happens:** Developer uses raw projection score as the objective coefficient, forgetting that GameBlazers applies the card multiplier to the player's actual score.

**Consequences:** Optimizer ignores multiplier advantage. A 1.5x card for a player projected at 40 points (effective: 60) is treated the same as a 1.0x card (effective: 40). Lineups leave significant value on the table.

**Prevention:**
- Compute `effective_value = projection * multiplier` during data preparation.
- Use `effective_value` as the objective coefficient: `prob += lpSum(effective_value[i] * x[i] for i in cards)`
- Display both raw projection and effective value in the UI so the user can verify.

**Detection:** Compare a 1.5x card and 1.0x card for the same player. If the optimizer treats them equally, the multiplier is not being applied.

**Which phase should address it:** Phase 1 (data preparation) and Phase 2 (objective function).

---

### Pitfall 9: ILP Solver Returns Non-Integer Solution Due to Relaxation

**What goes wrong:** PuLP or OR-Tools returns fractional values (e.g., x_i = 0.7) instead of binary (0 or 1). The code then rounds or truncates, producing invalid lineups.

**Why it happens:** Variables declared as `LpContinuous` instead of `LpBinary` (PuLP) or the solver relaxes the integer constraint due to configuration. Some developers use LP relaxation for speed and then try to round, which does not respect constraints.

**Consequences:** Lineups may have fractional players (rounding to wrong count), violate salary/collection constraints after rounding, or miss the optimal solution entirely.

**Prevention:**
- In PuLP: `x[i] = LpVariable(name, cat='Binary')` -- always use `Binary` category.
- Never round LP relaxation results. Use proper ILP solving.
- After solving, assert all variables are 0 or 1: `assert all(v.varValue in (0, 1) for v in prob.variables())`
- For the problem sizes in this app (hundreds of cards, 5 lineups), ILP solves in milliseconds. There is zero reason to use LP relaxation.

**Detection:** Any variable value that is not exactly 0 or 1 after solving.

**Which phase should address it:** Phase 2 (optimizer core). Basic ILP setup.

---

### Pitfall 10: Infeasible Model with No Diagnostic Information

**What goes wrong:** The ILP returns status "Infeasible" and the user sees "No lineup could be generated" with no explanation of why.

**Why it happens:** After filtering $0 salary cards, removing used cards from prior lineups, and applying salary floor/ceiling + collection constraints, it is possible that no valid lineup exists. Without diagnostics, the user has no idea what to fix.

**Consequences:** User is stuck. They cannot tell if the issue is too few eligible cards, salary constraints too tight, collection constraints too restrictive, or a bug in the optimizer.

**Prevention:**
- When infeasible, run diagnostic checks:
  1. How many eligible cards remain? (Need at least roster_size cards)
  2. Can the salary floor be met with the cheapest eligible cards?
  3. Can the salary ceiling be met with the most expensive eligible cards?
  4. Do collection constraints allow enough cards of each type?
- Display a specific error: "Only 4 eligible cards remain but 6 are needed for Tips lineup" or "All remaining Weekly cards have been used -- cannot satisfy max 3 Weekly constraint with 0 Weekly cards available" (this latter case is not actually a problem since 0 <= 3, but the example illustrates the pattern).
- Better example: "Minimum salary is $30,000 but the 6 cheapest available cards only total $18,000."

**Detection:** Solver returns `LpStatusInfeasible` (PuLP) or equivalent.

**Which phase should address it:** Phase 2 (optimizer) for detection, Phase 3 (UI) for displaying diagnostics.

---

### Pitfall 11: CSV Parsing Brittleness

**What goes wrong:** The roster CSV from GameBlazers has a slightly different column order, extra whitespace in headers, BOM characters, or encoding issues. The parser crashes or silently maps wrong columns.

**Why it happens:** Hard-coded column indices (column 0 = Player, column 8 = Salary) instead of header-name-based parsing. Or the CSV has a UTF-8 BOM that makes the first header `\ufeffPlayer` instead of `Player`.

**Consequences:** All data is wrong. Salaries might be read from the Multiplier column. Silent corruption is worse than a crash.

**Prevention:**
- Parse by column name, not index: `df['Salary']` not `df.iloc[:, 8]`.
- Strip whitespace from all column headers: `df.columns = df.columns.str.strip()`.
- Handle BOM: Use `encoding='utf-8-sig'` in pandas `read_csv()`.
- Validate expected columns exist after parsing. If a required column is missing, fail with a clear error listing expected vs. found columns.
- Validate data types: Salary should be numeric, Multiplier should be between 1.0 and 1.5, etc.

**Detection:** Unit test with a sample CSV that has BOM, extra whitespace, and varied column order.

**Which phase should address it:** Phase 1 (data ingestion). First thing built, first thing tested.

---

### Pitfall 12: Sequential Optimization Produces Globally Sub-Optimal Results

**What goes wrong:** Lineup 1 uses the absolute best cards. Lineup 2 gets the scraps. Lineup 3 is terrible. The total expected value across all 3 lineups is lower than if cards were distributed more evenly.

**Why it happens:** Greedy sequential optimization maximizes each lineup individually without considering the impact on subsequent lineups. This is locally optimal but globally sub-optimal.

**Consequences:** Total expected points across all lineups is lower than the mathematical optimum. For cash contests where all 3 lineups need to perform, this matters.

**Prevention:**
- **For V1, sequential is acceptable** -- it is simpler and the cash-first strategy naturally prioritizes the most important contest. Document this as a known limitation.
- **For future improvement:** Solve all 3 Tips lineups simultaneously in one ILP. The objective becomes `max(sum of effective_values across all 3 lineups)` with cross-lineup card exclusivity constraints. This guarantees global optimality.
- **Middle ground:** Solve lineup 1 optimally, then solve lineups 2 and 3 simultaneously (2-lineup joint optimization is simpler than 3).

**Detection:** Compare sequential total value vs. simultaneous total value on test data. If simultaneous is >5% better, it is worth the complexity.

**Which phase should address it:** Phase 2 (optimizer core) as a known limitation. Phase 4 or later as an enhancement.

---

## Minor Pitfalls

---

### Pitfall 13: Solver Dependency Installation on VPS

**What goes wrong:** PuLP works locally (it bundles CBC solver) but on the Hostinger VPS, the bundled CBC binary is not compatible with the Linux architecture, or OR-Tools requires specific system libraries that are not installed.

**Prevention:**
- PuLP bundles CBC for most platforms and is the safer choice for deployment simplicity.
- Test `pulp.PULP_CBC_CMD()` on the VPS early in development, not at deployment time.
- If using OR-Tools: it requires a `pip install ortools` that downloads platform-specific binaries. Verify it works on the VPS Linux distribution.
- Pin exact versions in `requirements.txt`.
- Consider using a Docker container on the VPS to isolate dependencies.

**Detection:** Import and run a trivial ILP solve on the VPS. If it fails, solver is not installed correctly.

**Which phase should address it:** Phase 1 (environment setup). Verify solver works on VPS before writing optimizer code.

---

### Pitfall 14: No Rate Limiting or File Size Validation on Uploads

**What goes wrong:** The app is publicly accessible (no auth). Someone uploads a 500MB file or sends thousands of requests, exhausting VPS memory/disk.

**Prevention:**
- Limit upload file size (e.g., 5MB max -- roster CSVs are tiny).
- Validate file extension (.csv only).
- Rate limit the optimization endpoint (e.g., 10 requests per minute).
- Process uploads in memory (do not save to disk unnecessarily), or clean up temp files immediately.
- Consider basic IP-based rate limiting via Flask-Limiter or nginx.

**Detection:** Monitor VPS disk and memory usage. Set up basic alerting.

**Which phase should address it:** Phase 3 (deployment hardening).

---

### Pitfall 15: Contest Configuration Drift

**What goes wrong:** GameBlazers changes contest parameters (salary cap, collection limits, roster size) and the config file is not updated. The optimizer generates lineups with outdated constraints that GameBlazers rejects.

**Prevention:**
- Display current contest configuration prominently in the UI so the user can visually verify it each week.
- Make the config file easy to edit (JSON or YAML, not buried in code).
- Add a "last updated" timestamp to the config display.
- Consider a simple admin UI page to edit contest parameters rather than requiring SSH/file editing.

**Detection:** User notices lineups are rejected by GameBlazers. The config display acts as a weekly visual check.

**Which phase should address it:** Phase 1 (config structure) and Phase 3 (admin UI for config editing).

---

### Pitfall 16: Projections CSV Has Players Not in Roster (and Vice Versa)

**What goes wrong:** The projections CSV includes 156 players in the field. The user's roster has 80 cards. The optimizer only considers the intersection (~60-70 matched players). But the unmatched projections are silently ignored, and the user does not realize 10 of their roster players have no projection.

**Prevention:**
- This is partially covered by Pitfall 3 (name matching), but even with perfect name matching, the asymmetry should be displayed.
- Show three lists: (a) matched players with projections, (b) roster players without projections (cards you own but no projection -- are they in the field?), (c) projection players without roster cards (players in the field you do not own).
- List (b) is the actionable one: the user may need to add missing projections or verify these players are indeed not in the tournament.

**Detection:** After merge, display match statistics prominently.

**Which phase should address it:** Phase 1 (data ingestion) and Phase 3 (UI display).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Data model & CSV parsing | Duplicate cards treated as same player (Pitfall 1) | Unique card IDs from row index, not player name |
| Data model & CSV parsing | $0 salary cards included (Pitfall 4) | Filter during ingestion, show filtered list |
| Data model & CSV parsing | Name matching failures (Pitfall 3) | Normalize + fuzzy match + unmatched report |
| Data model & CSV parsing | CSV encoding/header issues (Pitfall 11) | Parse by name, handle BOM, validate columns |
| Optimizer core | Salary floor missing (Pitfall 5) | Two-sided salary constraint from day one |
| Optimizer core | Collection constraints wrong (Pitfall 6) | Independent upper bounds per collection type |
| Optimizer core | Multiplier not in objective (Pitfall 8) | effective_value = projection * multiplier |
| Optimizer core | Variables not binary (Pitfall 9) | Use LpBinary, assert post-solve |
| Optimizer core | Cross-contest card reuse (Pitfall 7) | Remove used card IDs before next contest solve |
| Optimizer core | Near-identical lineups (Pitfall 2) | Exposure limits or minimum-difference constraints |
| Optimizer core | Infeasible with no diagnostics (Pitfall 10) | Diagnostic checks on infeasibility |
| Optimizer core | Sequential sub-optimality (Pitfall 12) | Accept for V1, document as known limitation |
| Deployment | Solver binary fails on VPS (Pitfall 13) | Test PuLP/CBC on VPS in Phase 1 |
| Deployment | No upload validation (Pitfall 14) | File size + rate limiting |
| Deployment | Config drift (Pitfall 15) | Display config in UI, easy edit mechanism |

## Sources

- ILP formulation patterns: Well-established in operations research literature (training data, MEDIUM confidence)
- PuLP variable categories and solver behavior: PuLP documentation (training data, HIGH confidence -- stable library with consistent API)
- DFS optimizer multi-lineup diversity: Common pattern in DraftKings/FanDuel optimizer community (training data, MEDIUM confidence)
- GameBlazers-specific rules (duplicate cards, $0 salary, collection constraints): Derived from PROJECT.md context (HIGH confidence for stated requirements)
- CSV parsing pitfalls (BOM, encoding): Well-known Python/pandas patterns (HIGH confidence)
- VPS deployment considerations: General Linux deployment knowledge (HIGH confidence)

**Note:** Web search was unavailable during this research session. Findings are based on training data and project context. ILP formulation patterns and DFS optimizer pitfalls are well-documented domains with stable best practices, so confidence remains MEDIUM-HIGH despite the limitation.
