# Stack Research

**Domain:** Manual lock/exclude additions to Flask + PuLP ILP optimizer (v1.1)
**Researched:** 2026-03-14
**Confidence:** HIGH

## Scope

This is a SUBSEQUENT MILESTONE research file. It covers ONLY what is needed to add manual lock/exclude to the existing validated stack (Flask, PuLP/CBC, Pydantic v2, Jinja2/HTML/CSS, session-based CSV upload flow). The question is: what changes or additions does the stack need?

**Answer: None. No new dependencies.**

All three feature areas resolve entirely within the existing stack.

---

## Recommended Stack

### Core Technologies (existing — no changes)

| Technology | Version | Purpose for v1.1 | Why No Change Needed |
|------------|---------|-----------------|----------------------|
| Flask built-in `session` | Flask 3.x (existing) | Store locked/excluded identifiers between requests | Two short lists of strings. Even 150 entries = ~600 bytes raw JSON — well under Flask's 4KB cookie limit. Zero new config. |
| PuLP `+=` constraint API | PuLP 2.x (existing) | Inject lock/exclude as ILP constraints before `solve()` | `prob += x[i] == 1` (lock card), pre-filter list (exclude card/golfer), `prob += lpSum(...) >= 1` (lock golfer). All native PuLP — no new API surface. |
| Jinja2 + HTML checkboxes | (existing) | Per-card toggle controls rendered after CSV upload | Standard `<input type="checkbox">` fields posted to a Flask route. `request.form.getlist()` collects them. No JS framework needed. |

### Supporting Libraries

No new libraries required.

| Library | Version | Purpose | Decision |
|---------|---------|---------|----------|
| Flask-Session | 0.8.0 | Server-side session storage | DO NOT ADD. Lock/exclude state (two lists of player-name strings + card identifiers) is well under the 4KB cookie limit. Adding Flask-Session for this would introduce an unnecessary dependency and filesystem/Redis configuration with zero benefit. |

---

## Session State Design

### What to store

Four session keys, all JSON-serializable:

```
session["locked_cards"]     = []   # list of [player, salary, multiplier] triples
session["locked_golfers"]   = []   # list of player name strings
session["excluded_cards"]   = []   # list of [player, salary, multiplier] triples
session["excluded_golfers"] = []   # list of player name strings
```

**Why triples for card-specific keys:** The `Card` dataclass is not JSON-serializable. Store the minimum identifier set — (player, salary, multiplier) is sufficient to uniquely identify a card within a given week's roster. Reconstruct `Card` objects from `validation.valid_cards` at optimize time.

**Why not store full Card objects:** Flask session requires JSON-compatible types (dicts, lists, strings, numbers). Dataclasses serialize to nothing useful without a custom encoder.

### Size budget (confirmed safe for built-in session)

- Realistic worst case: user locks 5 cards + excludes 10 golfers
- 15 entries × ~30 bytes each = ~450 bytes raw JSON
- After Flask's base64 + HMAC overhead (~33% expansion): ~600 bytes
- Flask limit: ~3,500 bytes usable
- Headroom: 5x+ — no risk

The only scenario that would blow the session limit is storing `valid_cards` (all 150+ cards) in session, which is NOT needed for this milestone. Don't do it.

### Reset on new CSV upload

In the existing `routes.py` POST handler, clear lock/exclude keys when a roster file is received:

```python
# At the top of the CSV upload POST branch, before validate_pipeline
for key in ("locked_cards", "locked_golfers", "excluded_cards", "excluded_golfers"):
    session.pop(key, None)
```

This is the correct integration point. The CSV upload is the natural "start over" action.

---

## ILP Constraint Injection Design

### Integration point

`_solve_one_lineup` in `gbgolf/optimizer/engine.py` builds and solves one PuLP problem. Lock/exclude constraints must be injected after standard constraints are built, before `prob.solve()`.

### Constraint patterns (all native PuLP)

**Exclude a card** — filter before problem construction (simplest; reduces problem size):
```python
exclude_keys = set(tuple(t) for t in excluded_card_triples)
cards = [c for c in cards if (c.player, c.salary, c.multiplier) not in exclude_keys]
```

**Exclude a golfer** — filter before problem construction:
```python
cards = [c for c in cards if c.player not in excluded_golfer_names]
```

**Lock a specific card** — force binary variable to 1:
```python
for i, card in enumerate(cards):
    if (card.player, card.salary, card.multiplier) in locked_card_keys:
        prob += x[i] == 1
```

**Lock a golfer by name** — at least one of their cards must be selected:
```python
for player in locked_golfer_names:
    indices = [i for i, c in enumerate(cards) if c.player == player]
    if indices:
        prob += pulp.lpSum(x[i] for i in indices) >= 1
```

### Infeasibility handling

If a lock constraint makes a lineup infeasible (e.g., locked card pushes salary over cap), `prob.solve()` returns non-Optimal status, `_solve_one_lineup` returns `None`, and the existing UI renders "No lineup could be built for this contest." No new error handling is required.

---

## UI Controls Design

### Form pattern

Lock/exclude controls live on the results page (after CSV upload). A new section renders the eligible card list with checkboxes. The form POSTs to a dedicated route (e.g., `POST /locks`) which writes to session and re-optimizes.

```html
<!-- Per-card row — player|salary|multiplier as compound value -->
<input type="checkbox" name="locked_cards"
       value="{{ card.player }}|{{ card.salary }}|{{ card.multiplier }}">

<!-- Per-golfer row — name only -->
<input type="checkbox" name="excluded_golfers" value="{{ card.player }}">
```

`request.form.getlist("locked_cards")` returns all checked values as a list of strings.

### No JavaScript required

The existing app uses form-submit-then-render. Lock/exclude toggles follow the same pattern. The loading overlay already exists. No HTMX, no Alpine.js, no fetch() calls needed.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Flask-Session | Adds dependency + server-side storage for a payload that fits in a cookie | Flask built-in `session` — already configured, zero extra work |
| Storing `Card` dataclass objects in session | Not JSON-serializable; Flask session will raise | Store (player, salary, multiplier) triples; reconstruct Cards at optimize time |
| HTMX / Alpine.js / any JS framework | Toggle controls work via standard form POST | Plain HTML checkboxes + form submit |
| AJAX re-optimize | Unnecessary complexity; re-optimize on form submit is the app's established pattern | Standard POST/redirect/render cycle |
| Redis | No cross-process session sharing needed; single Gunicorn worker is fine for single-user app | n/a |
| Separate lock/exclude database table | No persistence beyond the browser session is needed | Flask session cookie |

---

## Alternatives Considered

| Recommended | Alternative | When Alternative Makes Sense |
|-------------|-------------|-------------------------------|
| Flask built-in `session` | Flask-Session with filesystem backend | Only if payload exceeds ~3.5KB — which requires storing full Card objects in session, not just identifiers |
| Filter cards before ILP construction (exclude) | `prob += x[i] == 0` constraint | Equivalent result. Filtering is simpler and reduces the variable count, but either works. |
| Dedicated `/locks` POST route | Extending the existing CSV upload route | Either works. Separate route is cleaner because lock/exclude operates on already-uploaded data without re-uploading files. |
| Checkboxes + form POST | Inline AJAX toggle buttons | AJAX would avoid full page reload on each toggle — worthwhile only if re-optimize is slow (it isn't: <1 sec). |

---

## Version Compatibility

| Package | Constraint | Notes |
|---------|------------|-------|
| Flask | >= 2.0 (existing 3.x) | `session` dict API unchanged since Flask 0.x |
| PuLP | >= 2.0 (existing 2.x) | `prob +=` constraint API, `LpStatus`, `PULP_CBC_CMD(msg=0)` all unchanged |
| Pydantic | v2 (existing) | Not involved in lock/exclude path — no changes |

---

## Sources

- [Flask Sessions — TestDriven.io](https://testdriven.io/blog/flask-sessions/) — confirmed 4KB cookie limit, JSON serialization requirement (MEDIUM confidence, authoritative community source matching Flask docs)
- [Flask-Session 0.8.0 documentation](https://flask-session.readthedocs.io/en/latest/config.html) — confirmed 0.8.0 is current version; filesystem interface deprecated in 0.7.0 in favor of CacheLib (MEDIUM confidence, official docs via WebSearch)
- [Flask server-side sessions — TestDriven.io](https://testdriven.io/blog/flask-server-side-sessions/) — confirmed server-side session use cases and when they're needed (MEDIUM confidence)
- [PuLP 3.3.0 technical docs](https://coin-or.github.io/pulp/technical/pulp.html) — confirmed `+=` constraint API and binary variable patterns (HIGH confidence, official COIN-OR docs)
- [GitHub coin-or/pulp](https://github.com/coin-or/pulp) — confirmed current PuLP development status (MEDIUM confidence)
- Existing codebase `gbgolf/optimizer/engine.py` — constraint injection design derived directly from existing `_solve_one_lineup` structure (HIGH confidence, first-party source)
- Existing codebase `gbgolf/web/routes.py` — session reset integration point derived from existing POST handler (HIGH confidence, first-party source)
- Existing codebase `gbgolf/data/models.py` — confirmed `Card` dataclass is not JSON-serializable; triple identifier strategy derived from Card field structure (HIGH confidence, first-party source)

---

*Stack research for: GB Golf Optimizer v1.1 Manual Lock/Exclude*
*Researched: 2026-03-14*
