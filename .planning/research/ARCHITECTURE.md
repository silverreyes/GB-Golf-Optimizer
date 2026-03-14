# Architecture Research

**Domain:** Flask + PuLP fantasy golf optimizer — manual lock/exclude integration
**Researched:** 2026-03-14
**Confidence:** HIGH (based on direct codebase inspection)

---

## Context: What Was Actually Built (v1.0)

The pre-v1.0 research document described FastAPI. The actual implementation is Flask. This file supersedes that document for all milestone planning purposes.

v1.0 is a stateless request-response app. Every POST to `/` re-parses CSVs, re-filters, and re-runs the full ILP solve. There is no session persistence, no card identity across requests, no JavaScript-driven re-optimization. The single template (`index.html`) handles both the upload form state and the results display.

---

## Standard Architecture (Current v1.0)

```
+------------------------------------------------------------------+
|                      Browser (HTML/Jinja2)                        |
|  GET /   ->  upload form (index.html, details[open])             |
|  POST /  ->  same template, results injected, details[closed]    |
+------------------------------+-----------------------------------+
                               |
                               v  multipart/form-data POST
+------------------------------------------------------------------+
|              Flask Blueprint (gbgolf/web/routes.py)               |
|                                                                  |
|  index() GET  ->  render_template("index.html")                  |
|                                                                  |
|  index() POST ->                                                 |
|    1. Save uploads to NamedTemporaryFile                         |
|    2. validate_pipeline(roster, projections, config)             |
|    3. optimize(valid_cards, contests)                            |
|    4. render_template("index.html", result=result)               |
+-----+-------------------+------------------------------------------+
      |                   |
      v                   v
+------------+   +---------------------+
| data/      |   | optimizer/          |
| __init__.py|   | __init__.py         |
|            |   |                     |
| parse_     |   | optimize()          |
| roster_csv |   |   for each contest: |
| parse_     |   |     for each entry: |
| proj_csv   |   |       _solve_one_   |
| match_     |   |       lineup()      |
| projections|   |       (PuLP ILP)    |
| apply_     |   +---------------------+
| filters    |
+------------+
```

### Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `routes.py` | HTTP boundary: receive files, call pipeline, render template | `gbgolf/web/routes.py` |
| `data/__init__.py` | Orchestrate parse -> enrich -> filter pipeline | `gbgolf/data/__init__.py` |
| `filters.py` | Exclusion rules ($0, expired, no projection) | `gbgolf/data/filters.py` |
| `models.py` | Card, ExclusionRecord, ValidationResult dataclasses | `gbgolf/data/models.py` |
| `optimizer/__init__.py` | Multi-contest, multi-entry loop; disjoint card tracking | `gbgolf/optimizer/__init__.py` |
| `optimizer/engine.py` | Single ILP solve via PuLP/CBC | `gbgolf/optimizer/engine.py` |
| `index.html` | Upload form + results display in a single Jinja2 template | `gbgolf/web/templates/index.html` |

---

## Lock/Exclude Integration Architecture

### The Core Question: Where Does State Live?

The app has no persistent state. There are three options for carrying lock/exclude state:

**Option A: Flask server-side session (signed cookie)**
Store locked/excluded card identifiers in `flask.session`. The session is a signed cookie — survives across requests automatically, cleared when browser session ends or user re-uploads.

**Option B: Hidden form fields (client-side only)**
Render the current lock/exclude set as hidden `<input>` elements in the results page. Each re-optimize POST echoes them back.

**Option C: Server-side storage (file/DB)**
Store state on the server keyed by a session token. Overkill for this use case.

**Recommendation: Flask session (Option A)**

Rationale:
- Server-side session stores the card CSV data from the upload in the session, enabling re-optimize without re-upload. However, cards are too large to store in a cookie (Flask's default signed-cookie session has a 4KB limit).
- Therefore: store only the lock/exclude identifiers in the session. The actual card data must be re-submitted (or cached in server storage).

**Revised recommendation: Hidden form fields + Flask session hybrid**

The real constraint is that card data cannot fit in a cookie. The upload files are gone after the first request (temp files deleted). Therefore:

- **Hidden fields carry the parsed card data between requests** — not the raw files, but a serialized representation (or just the lock/exclude identifiers plus a mechanism to re-parse from re-submitted data).
- **Alternative: store the validated card list in Flask session using server-side session storage** (e.g. `flask-session` with filesystem backend).

After weighing implementation cost against the single-user, low-traffic context, the cleanest approach for this milestone is:

**Recommended: Re-submit data approach with hidden lock/exclude fields**

1. After initial upload, render a page that includes:
   - A hidden form with the raw CSV content (base64-encoded or as file re-upload) — this is brittle.

Actually, the cleanest approach for this app is:

**Final Recommendation: Two-route architecture with Flask filesystem session**

```
POST /upload  — parse CSVs, store ValidationResult in server-side session, redirect to /optimize
GET  /        — show upload form
POST /optimize — read valid_cards from session, apply lock/exclude from form POST, run ILP, return results
```

This avoids re-uploading files on every lock/exclude adjustment. The `flask-session` library with a filesystem backend is a single dependency that avoids the cookie size limit.

However, given the existing single-route architecture, a simpler alternative is available:

**Simpler Alternative: Serialize valid_cards to hidden fields**

The valid cards are a small set (typically 20-60 cards). Serialize them as JSON in a hidden `<textarea>` or `<input>` on the results page. On re-optimize POST, deserialize from that hidden field instead of from uploaded files. No new dependencies.

**Decision: Hidden field serialization is recommended for v1.1.**

Rationale: single dependency added (none), no server-side storage, consistent with the existing stateless model, low card counts make serialization trivially small (<10KB), simpler to test.

---

## System Overview: v1.1 Lock/Exclude Architecture

```
+------------------------------------------------------------------+
|                      Browser (HTML/Jinja2)                        |
|                                                                  |
|  State A: Upload form (GET /)                                    |
|    - roster + projections file inputs                            |
|    - submit -> POST / with files                                 |
|                                                                  |
|  State B: Results page (POST /)                                  |
|    - Lineups displayed                                           |
|    - Lock/Exclude panel: checkboxes per card/player              |
|    - Hidden field: serialized valid_cards JSON                   |
|    - "Re-Optimize" button -> POST /reoptimize                    |
|    - "Change files" -> GET / (clears all state)                  |
+----------+--------------------------+-----------------------------+
           |                          |
  POST /   |                          | POST /reoptimize
 (upload)  |                          | (hidden JSON + lock/exclude form)
           v                          v
+------------------------------------------------------------------+
|              Flask Blueprint (gbgolf/web/routes.py)               |
|                                                                  |
|  index() POST                  reoptimize() POST                 |
|    parse CSVs                    deserialize valid_cards          |
|    validate_pipeline()           parse lock_cards, exclude_cards  |
|    -> ValidationResult           -> LockExcludeSpec              |
|    serialize valid_cards         optimize(cards, contests, spec)  |
|    render results + hidden       render results + hidden          |
+------------------------------------------------------------------+
           |                          |
           v                          v
+---------------------------+  +---------------------------+
| data/ (unchanged)         |  | optimizer/ (extended)     |
|   validate_pipeline()     |  |   optimize(cards,         |
|   returns valid_cards     |  |           contests,       |
|                           |  |           locks=None,     |
|                           |  |           excludes=None)  |
|                           |  |   _solve_one_lineup()     |
|                           |  |     + lock constraints    |
|                           |  |     + exclude filtering   |
+---------------------------+  +---------------------------+
```

---

## Component Boundaries: New vs Modified

### New Components

| Component | What It Is | File |
|-----------|-----------|------|
| `LockExcludeSpec` dataclass | Carries lock_cards, lock_players, exclude_cards, exclude_players into optimizer | `gbgolf/data/models.py` (extend) |
| `reoptimize()` route | Accepts hidden card JSON + lock/exclude form fields, runs optimizer, returns results | `gbgolf/web/routes.py` (new route) |
| Lock/Exclude panel (HTML) | Checkboxes/toggles on results page for each card and each player | `gbgolf/web/templates/index.html` (extend) |
| Card serialization helpers | `cards_to_json()` / `cards_from_json()` round-trip for hidden field | `gbgolf/data/models.py` or new `gbgolf/data/serialize.py` |

### Modified Components

| Component | What Changes | Scope |
|-----------|-------------|-------|
| `optimize()` in `optimizer/__init__.py` | Accept optional `LockExcludeSpec`; pre-filter excludes; pass locks to engine | Additive — new parameter with default `None` |
| `_solve_one_lineup()` in `optimizer/engine.py` | Accept locked card indices; add `x[i] == 1` constraints for locked cards | Additive — new parameter |
| `index.html` | Add hidden field for serialized cards, add lock/exclude panel, add re-optimize form | Extend existing template |
| `routes.py` | Keep `index()` unchanged; add `reoptimize()` route | Additive |

### Unchanged Components

- `gbgolf/data/filters.py` — exclusion rules for invalid cards (manual excludes are separate, applied after pipeline)
- `gbgolf/data/roster.py`, `projections.py`, `matching.py` — parsing unchanged
- `gbgolf/data/config.py` — contest config unchanged
- `gbgolf/web/__init__.py` — app factory unchanged

---

## ILP Constraint Injection

### How Locked Cards Are Expressed in PuLP

A card lock forces `x[i] = 1` for the locked card's index. This is a simple equality constraint:

```python
# In _solve_one_lineup(), after building x[]:
for i in locked_indices:
    prob += x[i] == 1
```

This is equivalent to fixing the variable. PuLP handles this correctly — the solver will respect it as a hard constraint. If a lock makes the problem infeasible (e.g., locking two cards from the same player, or locking 7 cards into a 6-card roster), the solver returns non-Optimal and `_solve_one_lineup` returns `None`, which surfaces as an infeasibility notice.

### How Excluded Cards Are Expressed

Excluded cards are simply removed from the card pool before the ILP is built. No PuLP constraint needed — filtering at the Python level is cleaner and avoids unnecessary variables in the model.

```python
# In optimize(), before calling _solve_one_lineup():
available = [c for c in available if c not in excluded_set]
```

Card identity comparison must use a stable identifier, not Python `id()` (which is position-based and lost across serialization). A card needs a stable key: `(player, multiplier, salary, collection)` is unique enough in practice, or an explicit `card_id` field added to `Card`.

### Lock Semantics: Card vs. Player

Two distinct lock types:

- **Lock card**: force one specific card (player + multiplier + salary) into a lineup. The card must appear in exactly one lineup; the optimizer picks which lineup to assign it to.
- **Lock player**: force some card for this player to appear. Useful when user doesn't care which card is used.

For v1.1, locking a card means the optimizer must include that card in one lineup (but it doesn't specify which lineup). The current architecture already tracks `used_card_ids` across lineups in the `optimize()` loop. Locked cards need to be assigned to a lineup; the simplest approach is to inject the lock constraint in the first lineup where the card hasn't yet been used.

**Card lock implementation in optimizer loop:**

```python
for entry_num in range(config.max_entries):
    available = [c for c in valid_cards if id(c) not in used_card_ids]

    # Determine which locked cards are still unassigned and available in this pool
    pending_locks = [c for c in spec.lock_cards if id(c) not in used_card_ids and c in available]
    locked_indices = [available.index(c) for c in pending_locks]

    result = _solve_one_lineup(available, config, locked_indices=locked_indices)
```

### Player lock implementation:

A player lock adds a constraint that the sum of x[i] for all cards belonging to that player is >= 1:

```python
for player in spec.lock_players:
    player_indices = [i for i, c in enumerate(cards) if c.player == player]
    if player_indices:
        prob += pulp.lpSum(x[i] for i in player_indices) >= 1
```

The existing same-player constraint already ensures at most one card per player, so `>= 1` combined with `<= 1` forces exactly one of their cards in.

---

## Data Flow

### Initial Upload Flow (POST /)

```
Browser: POST / with roster.csv + projections.csv
    |
    v
routes.index() POST
    -> save to temp files
    -> validate_pipeline(roster_tmp, proj_tmp, config_path)
       -> parse_roster_csv()
       -> parse_projections_csv()
       -> match_projections()
       -> apply_filters()
       -> returns ValidationResult{valid_cards, excluded, warnings}
    -> optimize(valid_cards, contests)
       -> returns OptimizationResult{lineups, unused_cards, notices}
    -> serialize valid_cards to JSON string
    -> render_template("index.html",
         validation=validation,
         result=result,
         cards_json=cards_json,  # NEW: hidden field data
         show_results=True)
    |
    v
Browser: results page with lock/exclude panel + hidden cards_json field
```

### Re-Optimize Flow (POST /reoptimize)

```
Browser: POST /reoptimize with
  - cards_json (hidden field)
  - locked_cards[] (list of card keys)
  - locked_players[] (list of player names)
  - excluded_cards[] (list of card keys)
  - excluded_players[] (list of player names)
    |
    v
routes.reoptimize() POST
    -> deserialize valid_cards from cards_json
    -> parse lock/exclude form fields into LockExcludeSpec
    -> apply player-level excludes (filter from valid_cards)
    -> apply card-level excludes (filter from valid_cards)
    -> optimize(remaining_cards, contests, spec=lock_exclude_spec)
       -> for each lineup: apply lock constraints to ILP
    -> serialize valid_cards to JSON (same cards, unchanged)
    -> render_template("index.html",
         result=result,
         cards_json=cards_json,
         lock_spec=lock_spec,  # NEW: re-render UI with current lock state
         show_results=True)
```

### Card Identifier Strategy

Python object `id()` is used in v1.0 for cross-lineup tracking. This breaks across serialization. A card's stable identity for lock/exclude purposes is:

```
card_key = (player, salary, multiplier, collection)
```

This is unique for all realistic cases (two cards for the same player with identical salary/multiplier/collection would be indistinguishable but this does not occur in practice given GameBlazers card structure). The key can be serialized as a URL-safe string for form fields.

---

## UI Flow Changes

### State Machine

```
GET /
  Upload form (State 1)
  |
  | POST / (upload files)
  v
State 2: Results + Lock/Exclude Panel
  - Lineups displayed
  - Per-card row: [Lock] [Exclude] checkboxes
  - Per-player section: [Lock Player] [Exclude Player]
  - [Re-Optimize] button -> POST /reoptimize
  - [Change Files] link -> GET / (resets everything)
  |
  | POST /reoptimize
  v
State 2 (updated results, lock/exclude preserved)
```

### Lock/Exclude Panel Design

The panel should be rendered alongside or below the results. Two sub-sections:

1. **Card locks/excludes**: show all valid_cards with checkboxes. Each row: player name, multiplier, salary, collection. Checkboxes: Lock | Exclude (mutually exclusive per card).

2. **Player locks/excludes** (optional for v1.1 scope): aggregate by player name. Single lock/exclude applies to any card for that player.

The panel state must be reflected in the re-rendered template after re-optimize — the current lock/exclude selections should persist visually.

### No JavaScript Required (Base Implementation)

The re-optimize form submits via standard POST. No JavaScript needed for the base feature. The loading overlay from v1.0 applies equally to `/reoptimize` POSTs.

---

## Build Order

Build order is driven by two constraints: (1) ILP constraint injection must be verified before UI work, because infeasibility behavior must be understood; (2) card identity/serialization is a foundational dependency for everything else.

### Phase 1: Card Identity (Foundation)

**Why first:** Everything else depends on a stable card key. The current `id()` approach breaks across requests.

- Add `card_key` property or field to `Card` dataclass
- Verify round-trip: `card_key -> serialize -> deserialize -> lookup`
- Update `optimize()` to use `card_key` instead of `id()` for `used_card_ids` tracking
- Tests: card key uniqueness across a realistic roster

### Phase 2: ILP Constraint Injection (Core Logic)

**Why second:** Validates the PuLP approach before building UI around it. Infeasibility cases must be understood.

- Add `LockExcludeSpec` dataclass to `models.py`
- Extend `_solve_one_lineup()` with `locked_indices` parameter
- Extend `optimize()` with `spec: LockExcludeSpec | None = None`
- Test cases:
  - Lock one card -> appears in a lineup
  - Lock two cards -> each appears in a different lineup (if two lineups exist)
  - Lock a card that conflicts (same player twice) -> infeasibility notice surfaced
  - Exclude a card -> never appears in any lineup
  - Exclude all cards for a player -> player absent from all lineups
  - Lock player -> at least one of their cards appears in some lineup

### Phase 3: Serialization (Data Transport)

**Why third:** Needed for the re-optimize route but not for unit tests of the optimizer.

- Implement `cards_to_json()` / `cards_from_json()` in `gbgolf/data/models.py`
- Round-trip test: serialize ValidationResult.valid_cards -> deserialize -> same cards
- Verify size: realistic roster (60 cards) serializes to < 50KB

### Phase 4: Re-Optimize Route

**Why fourth:** Once optimizer accepts spec and cards can be serialized, the route is straightforward.

- Add `POST /reoptimize` route to `routes.py`
- Parse lock/exclude form fields into `LockExcludeSpec`
- Deserialize cards from hidden field
- Call `optimize()` with spec
- Re-serialize and render

### Phase 5: Template UI

**Why last:** Pure presentation. All logic is in place; UI is wiring.

- Add lock/exclude panel to `index.html`
- Add hidden `cards_json` field to results form
- Wire checkboxes to form fields using `card_key` as values
- Ensure current lock state re-renders correctly after re-optimize
- Verify loading overlay applies to `/reoptimize` form submit

---

## Anti-Patterns

### Anti-Pattern 1: Using Python `id()` for Card Identity Across Requests

**What people do:** Keep the v1.0 `id(c)` approach and try to serialize object memory addresses.
**Why it's wrong:** `id()` is a CPython memory address. It changes every request. Serializing it means nothing on deserialization.
**Do this instead:** Derive a stable key from card data fields: `(player, salary, multiplier, collection)`.

### Anti-Pattern 2: Storing Lock/Exclude in Flask Server-Side Session Without Dependency

**What people do:** Install `flask-session`, configure filesystem storage, add session cleanup logic.
**Why it's wrong:** Adds a new dependency and operational concern (session file cleanup) for a problem solvable with hidden form fields in this use case.
**Do this instead:** Serialize card data to a hidden form field. Valid card lists are small (< 50KB for any realistic roster). Standard HTTP POST handles it.

### Anti-Pattern 3: Injecting Lock Constraints as Post-Processing

**What people do:** Run the optimizer without locks, then swap in locked cards by hand, adjusting salaries.
**Why it's wrong:** The resulting lineup may violate salary constraints, collection limits, or same-player rules. The ILP solver must enforce all constraints simultaneously.
**Do this instead:** Inject lock constraints directly into the PuLP problem before solving. The solver handles all constraint interactions.

### Anti-Pattern 4: Locking a Specific Card to a Specific Lineup Slot

**What people do:** Add UI to let users specify "lock this card to Lineup 2 of The Tips."
**Why it's wrong:** Over-constrains the problem. Users care that a card appears somewhere across their lineups, not which numbered slot. Cross-lineup assignment is the optimizer's job.
**Do this instead:** Lock means "this card must appear in some lineup." The optimizer loop naturally assigns it to the first feasible lineup. If the user wants a card in a specific lineup, that's a v2 feature with significant added complexity.

### Anti-Pattern 5: Applying Excludes as ILP Constraints

**What people do:** Add `x[i] == 0` constraints for excluded cards.
**Why it's wrong:** The excluded card still takes up a variable slot in the ILP model, slightly inflating problem size with no benefit.
**Do this instead:** Filter excluded cards from the `available` list before building the PuLP problem. Fewer variables, cleaner model.

---

## Integration Points Summary

| Integration Point | New or Modified | Notes |
|-------------------|----------------|-------|
| `Card.card_key` property | Modified (Card dataclass) | Stable identity for lock/exclude tracking and serialization |
| `LockExcludeSpec` dataclass | New | Carries lock_cards, lock_players, exclude_cards, exclude_players |
| `_solve_one_lineup(locked_indices)` | Modified (additive) | New parameter, default empty list |
| `optimize(spec=None)` | Modified (additive) | New parameter, backward-compatible |
| `cards_to_json()` / `cards_from_json()` | New | Serialization for hidden form field |
| `POST /reoptimize` route | New | Separate from upload route |
| `index.html` lock/exclude panel | New UI section | Checkboxes, hidden field, re-optimize form |
| `index.html` hidden cards_json field | New hidden input | Carries card data between requests |

---

## Scaling Considerations

This app is single-user, single-server. No scaling work is needed. The optimizer runs in < 500ms for realistic card pools (20-80 cards, 5 lineups). Lock/exclude adds negligible constraint count. These are not concerns for v1.1.

---

## Sources

- Direct codebase inspection: `gbgolf/optimizer/engine.py`, `gbgolf/optimizer/__init__.py`, `gbgolf/web/routes.py`, `gbgolf/data/models.py`, `gbgolf/data/filters.py`, `gbgolf/web/templates/index.html` — HIGH confidence
- PuLP documentation: equality constraints on binary variables (`x[i] == 1`) are valid and correctly handled by CBC — HIGH confidence (standard ILP technique)
- Flask hidden form fields for stateless re-submission: standard web pattern — HIGH confidence

---

*Architecture research for: GB Golf Optimizer v1.1 lock/exclude integration*
*Researched: 2026-03-14*
