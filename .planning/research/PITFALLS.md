# Pitfalls Research

**Domain:** Adding manual lock/exclude to an existing ILP-based DFS lineup optimizer (GameBlazers-specific)
**Researched:** 2026-03-14
**Confidence:** HIGH — findings grounded in existing codebase analysis, ILP constraint theory, and DFS optimizer community patterns verified via web search

---

## Critical Pitfalls

### Pitfall 1: Locked Cards Making the ILP Infeasible with No Useful Error

**What goes wrong:**
The user locks 4 expensive cards (e.g., total locked salary = $44,000) into a 6-card Tips lineup with salary cap $64,000. The ILP must select 2 more cards with salary between $30,000 − $44,000 = −$14,000 floor (already violated) and $64,000 − $44,000 = $20,000 ceiling from remaining cards. If no 2-card combination meets both salary bounds and collection limits simultaneously, the solve returns `LpStatusInfeasible`. The current engine returns `None` and logs a generic notice like "lineup 1 of 3 could not be built (infeasible)". The user sees a blank lineup with no guidance.

**Why it happens:**
The existing `_solve_one_lineup` in `engine.py` returns `None` for any non-optimal status without distinguishing user error (over-locked) from genuine scarcity. When locks are added as equality constraints (`x[i] == 1`), the solver will find infeasibility but cannot tell the user which constraint is the culprit without additional diagnostics. Adding lock constraints is technically trivial — `prob += x[i] == 1` — but infeasibility diagnosis is skipped in the current implementation.

**How to avoid:**
- After a `None` result from `_solve_one_lineup`, run a fast pre-solve check specific to lock constraints:
  1. Compute locked card count — if it equals or exceeds `roster_size`, reject immediately with "X locked cards equals/exceeds the required Y roster slots."
  2. Compute locked salary sum — if it already exceeds `salary_max`, reject with "Locked cards total $X, which exceeds the salary cap of $Y."
  3. Compute minimum remaining salary needed — if locked salary + min possible salary for remaining slots > `salary_max`, reject with a specific message.
  4. Check collection limits — if locked cards already exceed a collection limit (e.g., 4 Weekly Collection cards locked but limit is 3), reject with "X Weekly Collection cards locked but limit is Y."
- Return these pre-solve diagnostics as structured data, not just a string, so the UI can display them per-lineup with actionable guidance.
- Run these checks in Python before calling PuLP (they are O(n) and take microseconds) so the error is immediate.

**Warning signs:**
- User locks cards and all lineups disappear simultaneously
- Infeasibility notice appears but the user cannot identify what to change
- User reports "the optimizer broke when I locked my best cards"

**Phase to address:**
Phase 1 of the lock/exclude milestone (constraint layer). The pre-solve diagnostics must be part of the same implementation as the lock constraints themselves — never shipped separately.

---

### Pitfall 2: Lock Constraint Leaking Across the Multi-Lineup Sequential Loop

**What goes wrong:**
The `optimize()` function in `__init__.py` loops over `range(config.max_entries)` and calls `_solve_one_lineup(available, config)` for each lineup. Lock constraints are meant to apply to every lineup (e.g., "always include Scottie Scheffler"). However, once lineup 1 is built and Scheffler's card is added to `used_card_ids`, the card is excluded from `available` for lineup 2. Lineup 2's lock constraint (`x[scheffler_card] == 1`) then references a card that is not in the pool — the constraint silently vanishes or, depending on implementation, causes a KeyError.

**Why it happens:**
The existing engine builds a fresh ILP per lineup with only `available` cards. If a locked card is no longer in `available`, there is no variable for it to constrain. The developer assumes "lock = force into every lineup" but the card-locking rule (each card used only once) makes this physically impossible.

**How to avoid:**
- Distinguish two semantically different lock types before writing a line of ILP code:
  - **Card lock**: Force *this specific card* into the lineup. Applies to exactly one lineup (the card is then consumed). Mutually exclusive with appearing in lineup 2.
  - **Golfer lock**: Force *this golfer* (by name) into the lineup — any card for that golfer will do. Can apply to multiple lineups because different cards for the same golfer are separate objects.
- For card locks: apply only to lineup 1 (or whichever lineup the card is available for). Show the user which lineup the card will appear in.
- For golfer locks: translate to "at least one card for player X must be selected" — `prob += lpSum(x[i] for i in indices_for_player) >= 1`. This survives card exhaustion only if the golfer has multiple cards; if only one card remains and it is consumed in lineup 1, lineup 2 will be infeasible unless the user understands this.
- Surface this distinction prominently in the UI label ("Lock this card" vs. "Lock this golfer").

**Warning signs:**
- Lock on a golfer causes lineup 1 to work but lineup 2 becomes infeasible when golfer has only one card
- Card lock silently disappears in lineup 2 because card is already used
- User thinks golfer appears in all lineups but only sees them in one

**Phase to address:**
Phase 1 of the lock/exclude milestone (before any UI work). The card vs. golfer distinction is architectural for the constraint layer.

---

### Pitfall 3: Session State Carrying Stale Locks After CSV Re-Upload

**What goes wrong:**
The user uploads CSVs, locks Scottie Scheffler, sees the lineup, then uploads new CSVs with a different roster. The lock state (`locked_card_ids = {id(scheffler_card)}`) still references the Python `id()` of the old card object. New CSV parsing creates entirely new `Card` objects with different `id()` values. The lock appears to apply (the set is non-empty) but never matches any card in the new pool — silently no-ops. Alternatively: the lock list is stored as player names in a server-side dict that persists across requests. New session, old locks remain. The user optimizes thinking Scheffler is locked but he is not.

**Why it happens:**
The current `optimize()` uses `id(c)` for card deduplication across lineups — a Python object identity approach that is session-local and non-persistent. This is correct for the current use case. But if lock state is stored the same way (by object identity), it breaks when objects are recreated. Meanwhile, Flask's default session is cookie-based and persists across requests in the same browser session. If lock state is stored in Flask session, uploading new CSVs does not automatically clear it unless explicitly coded.

**How to avoid:**
- Never store lock state by Python `id()`. Store locks by a stable card key: composite of `(player_name, salary, multiplier, collection)` — this matches the same logical card across upload cycles.
- Implement an explicit "reset locks on new upload" rule: whenever `validate_pipeline` succeeds for a new CSV pair, clear all lock/exclude state. This is the safest and simplest guarantee.
- If using Flask session for lock state, add a "session fingerprint" — a hash of the uploaded CSV filenames + upload timestamp. If the fingerprint changes, clear locks. If the fingerprint matches, restore locks.
- Document the reset rule in the UI: a visible "Locks reset when new CSVs are uploaded" notice near the upload button.

**Warning signs:**
- User reports "I locked a player but they didn't appear in the lineup after I re-uploaded"
- Lock indicator shows a player as locked who no longer exists in the current roster
- POST to `/optimize` with locks produces results that ignore the locks with no error

**Phase to address:**
Phase 1 of the lock/exclude milestone (state management design). The stable key scheme must be decided before any implementation — changing it later requires migrating all stored state.

---

### Pitfall 4: Exclude on a Card vs. Exclude on a Golfer — Ambiguous Semantics Causing Wrong Results

**What goes wrong:**
The user has two Scottie Scheffler cards (1.0x at $12,000 and 1.5x at $10,500). They click "exclude" on the $12,000 card intending to force the optimizer to use the cheaper 1.5x card instead. But the UI labels both a card-level action ("exclude this card") and a player-level action ("exclude Scottie Scheffler") identically. Implementation excludes the golfer entirely — neither card appears. User loses their best card from consideration.

The reverse also occurs: user intends to exclude Scheffler entirely (he is injured) but the UI only excludes the specific card they clicked. The other card is still selected by the optimizer.

**Why it happens:**
Card-level and player-level lock/exclude feel identical to the user — one click, one intent. But the ILP constraint difference is significant:
- Card exclude: remove card from `valid_cards` list before calling `_solve_one_lineup`
- Player exclude: add constraint `sum(x[i] for i in player_indices) == 0` (or equivalently, filter all cards for that player)

Developers typically implement only one level and assume it covers both use cases, or implement both but make the distinction unclear in the UI.

**How to avoid:**
- Design the UI with two explicitly labeled actions per card row:
  - "Exclude card" — removes only this card (the 1.5x card remains eligible)
  - "Exclude golfer" — removes all cards for this player name
- If space is limited, default to card-level exclude and provide a secondary "exclude all [player] cards" affordance
- In the data model, store exclusions in two separate sets: `excluded_card_keys: set[tuple]` and `excluded_players: set[str]`
- At optimization time, filter `valid_cards` by both sets before passing to the optimizer — do not inject player-level exclusions as ILP constraints, just pre-filter the card list. This is simpler and avoids any risk of the constraint interacting poorly with lock constraints.

**Warning signs:**
- User excludes a card but the golfer still appears (player-level was intended)
- User excludes a card and an unexpected card for the same player is also removed
- UI shows "excluded" state but optimizer still selects the player

**Phase to address:**
Phase 1 of the lock/exclude milestone (UI design and data model). This distinction must be in the design spec before any frontend code is written.

---

### Pitfall 5: Locking Both a Card and Excluding Its Player — Conflicting Constraints

**What goes wrong:**
The user locks a Scheffler card (card-level lock) and also excludes Scheffler as a player (player-level exclude) — or the UI allows this state through inconsistent interaction design. The ILP receives `x[scheffler_card] == 1` (lock) and `sum(x[scheffler_cards]) == 0` (exclude), which is immediately infeasible (`1 == 0` for the same variable). CBC returns infeasible with no useful message. The user cannot explain why their lineup failed.

**Why it happens:**
Lock and exclude are typically separate UI interactions. Without mutual exclusion logic in the frontend and validation in the backend, contradictory state is possible. This is especially likely if the lock and exclude states are stored separately and validated independently rather than as a unified constraint set.

**How to avoid:**
- When a card is locked, disable the "exclude golfer" button for that player name
- When a golfer is excluded, disable the lock button for all their cards
- In the backend validation layer (before calling the optimizer), check: does any locked card belong to an excluded player? If so, return a validation error: "Cannot lock [card] and exclude [player] simultaneously" before the solve is even attempted
- Store all constraint state in a single `ConstraintSet` dataclass with a `validate()` method that checks for internal contradictions

**Warning signs:**
- ILP returns infeasible immediately (before solver even runs meaningfully)
- User has both a lock indicator and an exclude indicator visible for the same player row
- Validation errors only appear after a multi-second solver timeout

**Phase to address:**
Phase 1 of the lock/exclude milestone (constraint validation). Conflict detection is a pre-flight check, not a solver concern.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store lock state by Python `id()` instead of stable composite key | Zero extra code for key generation | All locks silently break on re-upload | Never — use composite key from day one |
| Implement only player-level lock/exclude (skip card-level) | Simpler UI and state model | Users with duplicate cards cannot optimize card selection | Acceptable for MVP if explicitly documented as limitation |
| No pre-solve diagnostics — just return generic infeasibility notice | Saves ~30 lines of diagnostic code | Users cannot recover from self-inflicted infeasibility | Never — diagnostics must ship with lock feature |
| Pass lock list as global state / app config rather than per-request | Avoids Flask session complexity | State shared across users (public app) or persists after session ends | Never — this is a single-user scenario but still wrong |
| Re-run full optimize() on every lock toggle (no incremental solve) | Simple implementation, always correct | Slightly slower UX (300–500ms per toggle) | Acceptable — problem size makes full re-solve trivially fast |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| PuLP lock constraint | Add `prob += x[i] == 1` without checking if `i` is in current `available` | Pre-filter: only add lock constraints for cards present in `available`; warn for missing locked cards |
| PuLP exclude via filter | Remove cards from `valid_cards` globally (affecting all lineups) vs. per-lineup | Apply exclusion at the `available` list level inside the loop, not by mutating `valid_cards` |
| Flask session storage | Store card objects or `id()` references in session (not serializable) | Store only the stable composite key tuple `(player, salary, multiplier, collection)` as a plain list in session |
| Jinja2 template lock state | Re-render full page on lock/exclude, losing scroll position | Use HTMX or a small JS snippet to update only the card table, or accept full-page reload as MVP behavior |
| Cross-contest lock propagation | Lock applies to Tips only but user expects it to apply to all contests | Make the scope of the lock explicit in the UI ("all lineups" vs. per-contest) |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Re-solving ILP from scratch on every lock toggle with full diagnostics | Each toggle triggers 3–5 sequential PuLP solves (one per lineup) | At current scale (18–35 cards, 5 lineups), total solve time is <200ms — full re-solve is fine | Would only matter at 1,000+ cards; irrelevant for this app |
| Running diagnostic pre-checks in Python after solver returns infeasible | Negligible — pure Python arithmetic | Keep diagnostics as pre-filters, not post-solve analysis | No threshold — always fast |
| Storing lock state in Flask cookie session | Cookie size limit ~4KB — not a risk at current scale | Session stores at most a handful of card keys per session | Would require server-side sessions at 50+ locked cards per session |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Accepting lock/exclude lists from POST body without bounding their size | Malicious input with 10,000 "locked" cards causes O(n²) constraint generation | Validate: `len(locks) <= roster_size` and `len(excludes) <= total_card_count` before processing |
| Trusting composite card keys from client without verifying they match uploaded roster | User crafts fake card keys to probe optimizer behavior | Re-validate all lock/exclude keys against the current session's parsed card pool — discard any key not present in current roster |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No visual distinction between "card locked" and "golfer locked" | User locks a card thinking it locks the golfer; optimizer uses a different card for same player | Use distinct icons/labels: card icon for card-level, player icon for golfer-level |
| Lock/exclude state not cleared when new CSVs are uploaded | User uploads new week's roster but old locks apply to players no longer in field — silent no-op or wrong lineups | Reset all lock/exclude state on new upload, show a banner: "Locks and excludes cleared for new upload" |
| No feedback when a lock is unresolvable (e.g., locked card consumed in lineup 1, missing in lineup 2) | User sees lineup 2 without the "locked" player and assumes the optimizer is broken | Show per-lineup lock resolution: "Card locked in lineup 1; not available for lineup 2" |
| Optimize button triggers re-solve even when no locks changed | User expects live preview on toggle; instead must click optimize repeatedly | Show a "Re-optimize" call-to-action whenever lock/exclude state changes from the last optimization run |
| Locked/excluded cards shown mixed with eligible cards in card table | User loses track of constraint state while adjusting multiple locks | Group or visually separate locked/excluded cards from the eligible pool in the table |
| No "clear all locks" or "clear all excludes" button | User must individually toggle off each lock/exclude when starting fresh | Provide "Clear all" actions, especially important before uploading new projections |

---

## "Looks Done But Isn't" Checklist

- [ ] **Card lock in multi-lineup context:** Verify that a card-level lock applies only to the lineup where the card is available, and a clear notice is shown for subsequent lineups where the card has been consumed.
- [ ] **Golfer lock with single card:** If the only card for a locked golfer is consumed in lineup 1, lineup 2 should produce an infeasibility notice that names the golfer — not a generic "could not build" message.
- [ ] **Salary infeasibility diagnosis:** When infeasible after adding locks, the error message states the locked salary sum and how much salary remains for remaining slots — not just "infeasible."
- [ ] **Collection limit infeasibility diagnosis:** When locked cards violate a collection limit, the error names the collection type and counts: "3 Weekly Collection cards locked but only 3 are allowed — no slots remain for other lineups."
- [ ] **Lock/exclude reset on new upload:** Upload a new CSV after setting locks, then optimize — verify no locks carry over and the notice is displayed.
- [ ] **Conflict detection:** Lock a card and exclude the same golfer — verify the backend rejects this with a specific error before attempting to solve.
- [ ] **Re-optimize state indicator:** Change a lock after optimizing — verify the UI shows a "stale results" warning prompting re-optimization.
- [ ] **Empty lock/exclude sets:** Optimize with zero locks and zero excludes — verify identical behavior to v1.0 (regression test).

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Lock state corrupted / stale after re-upload | LOW | Clear all session state (provide "reset" button); no data loss |
| Infeasibility from too many locks | LOW | Pre-solve diagnostics guide user to remove conflicting locks; no code change needed |
| Card vs. golfer lock confusion causing wrong lineups | MEDIUM | Add UI labels + backend constraint distinction; requires template + state model changes |
| Conflicting lock+exclude state shipped without validation | MEDIUM | Add `validate()` method to `ConstraintSet`; add conflict check to optimize route before solve |
| Lock constraint not surviving card consumption across lineups | HIGH | Requires redesign of card vs. golfer lock semantics; affects UI, state model, and ILP layer simultaneously |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Infeasibility with no useful message after locking | Phase 1: Lock constraint layer + diagnostics | Lock 4 expensive cards into 6-card lineup — error message names the salary conflict |
| Lock constraint leaking across sequential lineup loop | Phase 1: Card vs. golfer lock distinction | Lock a golfer with one card — verify card appears in lineup 1, infeasibility notice names golfer in lineup 2 |
| Stale session state after CSV re-upload | Phase 1: State management design with stable composite keys | Upload CSVs, lock a player, upload new CSVs — verify locks are cleared and notice shown |
| Card vs. golfer exclude ambiguity | Phase 1: UI design + data model (two separate stored sets) | User with duplicate cards — exclude one card, verify other card still selectable |
| Conflicting lock + exclude constraints | Phase 1: Constraint validation pre-flight check | Lock a card + exclude same golfer — verify error before solve, no ILP call made |
| No visual feedback when lock/exclude state is stale | Phase 2: UI re-optimize indicator | Set a lock, verify "Re-optimize" indicator appears; click optimize, verify indicator clears |

---

## Sources

- Existing codebase analysis: `gbgolf/optimizer/engine.py`, `gbgolf/optimizer/__init__.py`, `gbgolf/web/routes.py`, `gbgolf/data/models.py` — HIGH confidence (direct code inspection)
- ILP lock constraint mechanics (equality constraint `x[i] == 1` in PuLP): PuLP documentation and coin-or/pulp GitHub issue discussions — HIGH confidence
- DFS optimizer lock/exclude UX patterns: RotoWire NFL DFS Optimizer FAQ, FantasyPros DFS optimizer docs — MEDIUM confidence (different sport/platform, patterns transferable)
- Over-locked infeasibility patterns: DFS community documentation (SaberSim, Fantasy Footballers) — MEDIUM confidence (verified multiple sources agree)
- Flask session stale state patterns: flask-session readthedocs, TestDriven.io Flask sessions article — MEDIUM confidence
- PuLP infeasibility diagnosis with CBC (no native IIS support): blend360 OptimizationBlog, coin-or/pulp GitHub issues — MEDIUM confidence (CBC does not compute IIS natively; pre-solve diagnostics are the correct alternative)
- Constraint conflict detection as pre-flight check: ILP modeling guides (AIMMS Modeling Guide), operational research patterns — HIGH confidence

---
*Pitfalls research for: Adding manual lock/exclude to GB Golf Optimizer ILP engine*
*Researched: 2026-03-14*
