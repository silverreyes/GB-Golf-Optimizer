# Phase 5: Serialization and Re-Optimize Route - Research

**Researched:** 2026-03-14
**Domain:** Flask route design, JSON serialization, Python dataclass round-trip, HTML form patterns
**Confidence:** HIGH — all findings derived from direct codebase inspection; no external dependencies introduced

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Re-Optimize button lives in a separate `<form>` element, independent from the upload form
- Positioned above the lineup results (first thing user sees after lineups load)
- Always visible after results load — no state check for active locks/excludes
- Does NOT live inside the `<details>` upload section
- Reuse the existing full-page "Optimizing…" overlay on Re-Optimize click
- Same overlay text ("Optimizing…") — no distinction from a fresh upload
- No new CSS or JS needed for the loading state
- On missing/unparseable hidden field: show "Session expired — please re-upload your files" error, render upload form so user can start over
- Re-optimized results visually identical to original — same tables, same layout
- No badge, label, or count indicator on re-optimized results

### Claude's Discretion

- Serialization format for hidden form field (JSON encoding of Card fields)
- Which Card fields to include in serialization (all fields needed to reconstruct the card for the optimizer)
- Route name (`/reoptimize` or handled within `/`)
- Form method and action for the Re-Optimize form

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-02 | User can re-optimize with updated lock/exclude selections without re-uploading CSVs | Covered by: hidden field card pool serialization, `/reoptimize` POST route, session-read constraint reconstruction, `optimize()` call with deserialized cards + session constraints |
</phase_requirements>

---

## Summary

Phase 5 adds a Re-Optimize button and backing route so users can iterate on lock/exclude state without re-uploading files. The card pool (`valid_cards`) produced by `validate_pipeline()` must survive the HTTP round-trip. The project's established approach (decided in Phase 4) is to serialize card objects into a hidden HTML form field as JSON, not store them in the Flask cookie session (which has a 4 KB limit).

The implementation has three tightly coupled parts: (1) the `/reoptimize` route in `routes.py`, (2) the JSON serialization/deserialization of `Card` objects, and (3) the template change that embeds the hidden field and the Re-Optimize form. All integration points are well-understood from existing code — no new libraries, no new CSS, no new JS beyond a single `addEventListener` call mirroring the existing upload form listener.

**Primary recommendation:** Implement as a new `POST /reoptimize` blueprint route in `routes.py`. Serialize `valid_cards` to JSON (list of dicts, Card fields only) in the existing upload route, inject into `index.html` as a hidden field, and deserialize back into `Card` objects in the new route before calling `optimize()`.

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Role in Phase 5 |
|---------|---------|---------|----------------|
| Flask | >=3.0 | Web framework | New route, `request.form`, `session`, `render_template` |
| Python `json` | stdlib | Serialization | `json.dumps` / `json.loads` for hidden field value |
| Python `dataclasses` | stdlib | Card reconstruction | `Card(...)` constructor from deserialized dict |
| Jinja2 | bundled with Flask | Template rendering | Hidden input, Re-Optimize form, overlay trigger |

No `pip install` needed for this phase.

---

## Architecture Patterns

### Recommended Project Structure

No new files required beyond route additions and template changes:

```
gbgolf/web/
├── routes.py          # Add: /reoptimize route + card serialization helpers
└── templates/
    └── index.html     # Add: hidden form field + Re-Optimize form block
tests/
└── test_web.py        # Add: re-optimize integration tests
```

### Pattern 1: Card Pool Serialization to Hidden Form Field

**What:** In the existing upload route's successful POST path, serialize `validation.valid_cards` to a JSON string and pass it to the template as a new `card_pool_json` variable. Jinja2 renders it into a `<input type="hidden">` inside the results block.

**When to use:** After `optimize()` returns successfully in the upload route; also echoed back by the re-optimize route itself so subsequent re-optimizations work.

**Card fields to serialize:** All fields needed to reconstruct a `Card` for the optimizer:
- `player` (str) — used for player-level lock/exclude matching and composite key
- `salary` (int) — part of composite key; used in feasibility checks
- `multiplier` (float) — part of composite key; used in effective_value
- `collection` (str) — part of composite key; used in collection constraint checks
- `expires` (str, ISO 8601 or null) — Card constructor expects `Optional[date]`; serialize as `card.expires.isoformat() if card.expires else None`
- `projected_score` (float or null) — used in lineup score calculation
- `effective_value` (float or null) — pre-computed; include to avoid recomputing
- `franchise` (str) — Card field, default ""
- `rookie` (str) — Card field, default ""

**Serialization (in route):**
```python
import json
from datetime import date

def _serialize_cards(cards: list) -> str:
    """Serialize a list of Card objects to a JSON string for the hidden form field."""
    return json.dumps([
        {
            "player": c.player,
            "salary": c.salary,
            "multiplier": c.multiplier,
            "collection": c.collection,
            "expires": c.expires.isoformat() if c.expires else None,
            "projected_score": c.projected_score,
            "effective_value": c.effective_value,
            "franchise": c.franchise,
            "rookie": c.rookie,
        }
        for c in cards
    ])
```

**Deserialization (in re-optimize route):**
```python
from datetime import date
from gbgolf.data.models import Card

def _deserialize_cards(json_str: str) -> list:
    """Reconstruct Card objects from a JSON string. Returns list[Card]."""
    raw = json.loads(json_str)
    cards = []
    for d in raw:
        expires = None
        if d.get("expires"):
            expires = date.fromisoformat(d["expires"])
        cards.append(Card(
            player=d["player"],
            salary=int(d["salary"]),
            multiplier=float(d["multiplier"]),
            collection=d["collection"],
            expires=expires,
            projected_score=d.get("projected_score"),
            effective_value=d.get("effective_value"),
            franchise=d.get("franchise", ""),
            rookie=d.get("rookie", ""),
        ))
    return cards
```

**Confidence:** HIGH — derived from reading `gbgolf/data/models.py` directly.

### Pattern 2: Re-Optimize Route

**What:** A new `POST /reoptimize` route that reads the hidden field, deserializes cards, reads session for constraints, calls `optimize()`, returns the same template vars as the upload route.

**Key difference from upload route:** No file I/O, no `validate_pipeline()`, no session clearing, no `lock_reset` banner.

```python
@bp.route("/reoptimize", methods=["POST"])
def reoptimize():
    """Re-run optimizer using the serialized card pool from the hidden form field."""
    card_pool_json = request.form.get("card_pool")
    if not card_pool_json:
        return render_template(
            "index.html",
            error="Session expired — please re-upload your files",
        )

    try:
        valid_cards = _deserialize_cards(card_pool_json)
    except (ValueError, KeyError, TypeError):
        return render_template(
            "index.html",
            error="Session expired — please re-upload your files",
        )

    constraints = ConstraintSet(
        locked_cards=[tuple(k) for k in session.get("locked_cards", [])],
        locked_golfers=session.get("locked_golfers", []),
        excluded_cards=[tuple(k) for k in session.get("excluded_cards", [])],
        excluded_players=session.get("excluded_players", []),
    )

    result = optimize(valid_cards, current_app.config["CONTESTS"], constraints=constraints)

    return render_template(
        "index.html",
        result=result,
        show_results=True,
        lock_reset=False,
        card_pool_json=card_pool_json,  # Echo back for subsequent re-optimizations
    )
```

**Confidence:** HIGH — mirrors existing upload route structure exactly.

### Pattern 3: Template Changes

**What:** Two additions to `index.html`:

1. Hidden input inside the results block — carries card pool across Re-Optimize submissions:
```html
{% if show_results and card_pool_json %}
<input type="hidden" id="card-pool-data" name="card_pool" value="{{ card_pool_json | e }}" />
{% endif %}
```

2. Re-Optimize form — separate `<form>` above lineup tables:
```html
{% if show_results %}
<form method="post" action="{{ url_for('main.reoptimize') }}" id="reoptimize-form">
  <input type="hidden" name="card_pool" value="{{ card_pool_json | e }}" />
  <button type="submit">Re-Optimize</button>
</form>
{% endif %}
```

3. JS listener addition (mirrors existing upload-form listener):
```javascript
document.getElementById("reoptimize-form").addEventListener("submit", function () {
  document.getElementById("loading-overlay").style.display = "flex";
});
```

**Important:** `| e` (Jinja2 auto-escape) is always active in `.html` templates. The hidden field value will be HTML-entity-escaped on render and decoded by the browser before form submission — no double-encoding issue. The JSON string itself does not contain single quotes, so `value="{{ card_pool_json }}"` with double-quote delimiters is safe, but `| e` is correct defensive practice.

**Confidence:** HIGH — derived from reading existing `index.html` directly.

### Pattern 4: Error Recovery

When `card_pool` field is missing or malformed, render `index.html` with only `error=` set (no `show_results`, no `result`). This matches how the upload route handles `ValueError` — same template, same error display, upload form shown in open state.

```python
return render_template(
    "index.html",
    error="Session expired — please re-upload your files",
)
```

The `<details id="upload-section">` opens automatically when `show_results` is falsy (Jinja2: `{% if not show_results %}open{% endif %}`). No extra logic needed.

**Confidence:** HIGH — derived from existing template logic.

### Anti-Patterns to Avoid

- **Storing `valid_cards` in Flask session:** The cookie session has a ~4 KB limit after HMAC + base64 overhead. Even a modest card pool of 30+ cards with all fields would exceed this. Project decision: hidden form field only.
- **Pydantic at deserialize boundary:** The project rule is "Pydantic at boundary only." Internal card reconstruction should use the `Card` dataclass constructor directly, not a Pydantic model.
- **Re-running `validate_pipeline()` on re-optimize:** This would require re-uploaded files. The whole point of the hidden field is to skip file I/O entirely.
- **Using Python's `id()` as card identifier in JSON:** `id()` is a memory address; it changes across requests. The composite key `(player, salary, multiplier, collection)` is the stable identity (established in Phase 4).
- **`| safe` on card_pool_json:** Using `| safe` would disable escaping of HTML special chars in the JSON blob. Use `| e` (explicit escape) or rely on auto-escape, but do NOT use `| safe` for user-derived data injected into attribute values.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Custom CSV/delimited encoding | Python stdlib `json` | Already used in project; handles all Card field types; round-trips cleanly |
| Date serialization | Custom date format | `date.isoformat()` / `date.fromisoformat()` | Standard ISO 8601; stdlib; no ambiguity |
| HTML escaping of JSON in attribute | Manual string replace | Jinja2 auto-escape (`| e`) | Handles `"`, `<`, `>`, `&` correctly; Jinja2 is already the template engine |
| Constraint reconstruction | New session schema | Existing `ConstraintSet(...)` pattern from routes.py | Already tested; identical construction in upload route |

---

## Common Pitfalls

### Pitfall 1: Double HTML-encoding of JSON in hidden field value

**What goes wrong:** `json.dumps` produces a string with `"` characters. If passed through `| tojson` in Jinja2, it gets double-encoded. If no escaping is applied, raw `"` characters break the HTML attribute.

**Why it happens:** JSON uses double quotes; HTML attributes also use double quotes. Naive injection produces malformed HTML.

**How to avoid:** Pass `card_pool_json` as a plain Python string to `render_template`. In the template, use `value="{{ card_pool_json | e }}"`. Jinja2 auto-escape converts `"` to `&quot;` in attribute context; browsers decode `&quot;` back to `"` before form submission. The value received by Flask's `request.form.get("card_pool")` is the original JSON string — no double-decoding needed.

**Warning signs:** `json.loads()` raises `JSONDecodeError` in the reoptimize route despite valid upstream serialization.

### Pitfall 2: Missing `card_pool_json` on GET or error renders

**What goes wrong:** Template block `{% if show_results and card_pool_json %}` guards the hidden field. But if `card_pool_json` is not explicitly passed as `None` or omitted in `render_template(...)` calls that don't set `show_results=True`, Jinja2 raises `UndefinedError`.

**How to avoid:** Either always pass `card_pool_json=None` as a default keyword arg in all `render_template` calls in `routes.py`, or use `{{ card_pool_json | default('') }}` in the template. The latter is cleaner — one change in the template covers all callers.

**Warning signs:** `jinja2.exceptions.UndefinedError: 'card_pool_json' is undefined` in test output or browser 500 error.

### Pitfall 3: `salary` type round-trip (int vs float in JSON)

**What goes wrong:** `json.dumps` preserves Python `int` as JSON integer. `json.loads` returns Python `int`. But if a Card was constructed with a float salary upstream (unlikely given the `int` type annotation but possible), it would serialize as a float and `int(d["salary"])` in deserialization handles it correctly. Not a real risk given existing `int` type annotation, but worth explicit casting.

**How to avoid:** Always cast `salary=int(d["salary"])` and `multiplier=float(d["multiplier"])` in `_deserialize_cards`. This is already shown in the code example above.

### Pitfall 4: Re-optimize form rendered but `card_pool_json` is empty string

**What goes wrong:** If `card_pool_json` is an empty string `""` (falsy), the hidden input renders with an empty value. The re-optimize route then falls into the "session expired" error path, confusing the user when results are visible.

**How to avoid:** Only render the Re-Optimize form when `card_pool_json` is a non-empty truthy value. Jinja2 `{% if show_results and card_pool_json %}` handles this correctly.

### Pitfall 5: Re-Optimize form JS listener added before element exists

**What goes wrong:** If the `<script>` block runs before the re-optimize form is rendered (e.g., form is inside a Jinja conditional that evaluates false), `document.getElementById("reoptimize-form")` returns `null` and `.addEventListener` throws a TypeError.

**How to avoid:** Guard the listener: `const rf = document.getElementById("reoptimize-form"); if (rf) { rf.addEventListener(...); }`. This is consistent with how the existing upload-form listener is structured (it assumes the form always exists on the page — safe since the upload form is always present, but the re-optimize form is conditional).

---

## Code Examples

### Upload route modification (add card_pool_json to successful render)

```python
# In the existing upload route's successful return:
card_pool_json = _serialize_cards(validation.valid_cards)

return render_template(
    "index.html",
    validation=validation,
    result=result,
    show_results=True,
    lock_reset=lock_reset,
    card_pool_json=card_pool_json,  # NEW
)
```

### Deserialization with error handling

```python
try:
    valid_cards = _deserialize_cards(card_pool_json)
except (ValueError, KeyError, TypeError, json.JSONDecodeError):
    return render_template(
        "index.html",
        error="Session expired — please re-upload your files",
    )
```

### Template: Re-Optimize form placement

```html
<!-- ABOVE lineup results, OUTSIDE upload <details> block -->
{% if show_results and card_pool_json %}
<form method="post" action="{{ url_for('main.reoptimize') }}" id="reoptimize-form">
  <input type="hidden" name="card_pool" value="{{ card_pool_json | e }}" />
  <button type="submit">Re-Optimize</button>
</form>
{% endif %}
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Server-side session storage for card pool | Hidden form field (client-side) | Flask cookie session 4 KB limit makes server-side infeasible without a session backend like Redis |
| Python `id()` for card identity | Composite key `(player, salary, multiplier, collection)` | Phase 4 decision; `id()` is unstable across requests |

---

## Open Questions

1. **Route name: `/reoptimize` vs sub-path**
   - What we know: CONTEXT.md leaves this to Claude's discretion. The existing routes.py has only one blueprint route (`/`). Flask convention for actions is a distinct POST-only URL.
   - Recommendation: Use `POST /reoptimize`. Clear URL, easy to test with `client.post("/reoptimize", ...)`, consistent with REST conventions for a distinct action endpoint.

2. **Should `_serialize_cards` / `_deserialize_cards` live in `routes.py` or a separate module?**
   - What we know: These are pure transformation functions with no Flask dependency. The project currently has all web logic in `routes.py`.
   - Recommendation: Place in `routes.py` as module-level functions for Phase 5 simplicity. If they need reuse in Phase 6+, extract to `gbgolf/web/serialization.py` at that time.

3. **Form method confirmation**
   - What we know: Re-Optimize sends `card_pool` (potentially large JSON payload) to the server. POST is required — GET would put the JSON in the URL query string (URL length limits apply; browsers truncate; no security).
   - Recommendation: `method="post"` confirmed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_web.py -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-02 | Re-Optimize POST returns 200 with lineup tables | integration | `pytest tests/test_web.py::test_reoptimize_returns_results -x` | Wave 0 |
| UI-02 | Re-Optimize result layout identical to upload result | integration | `pytest tests/test_web.py::test_reoptimize_layout_identical -x` | Wave 0 |
| UI-02 | Re-Optimize without card_pool field returns session-expired error | integration | `pytest tests/test_web.py::test_reoptimize_missing_card_pool -x` | Wave 0 |
| UI-02 | Re-Optimize with malformed card_pool returns session-expired error | integration | `pytest tests/test_web.py::test_reoptimize_malformed_card_pool -x` | Wave 0 |
| UI-02 | Re-Optimize reads lock/exclude state from session | integration | `pytest tests/test_web.py::test_reoptimize_uses_session_constraints -x` | Wave 0 |
| UI-02 | Re-Optimize form renders above lineup results after upload | integration | `pytest tests/test_web.py::test_reoptimize_button_rendered -x` | Wave 0 |
| UI-02 | Re-Optimize form not rendered on GET or error pages | integration | `pytest tests/test_web.py::test_reoptimize_button_absent_on_get -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_web.py -x -q`
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_web.py::test_reoptimize_*` — 7 new test functions (add to existing file, no new file needed)

*(Existing test infrastructure covers all other needs. No new config, no new fixture files — `conftest.py` and existing `client` fixture are sufficient.)*

---

## Sources

### Primary (HIGH confidence)

- Direct codebase read: `gbgolf/data/models.py` — Card dataclass field names and types
- Direct codebase read: `gbgolf/web/routes.py` — existing upload route structure, session keys, ConstraintSet construction pattern
- Direct codebase read: `gbgolf/web/templates/index.html` — existing form/overlay pattern, Jinja2 template vars, `| e` escaping behavior
- Direct codebase read: `gbgolf/optimizer/__init__.py` — `optimize()` signature
- Direct codebase read: `gbgolf/optimizer/constraints.py` — ConstraintSet fields
- Direct codebase read: `.planning/phases/05-serialization-and-re-optimize-route/05-CONTEXT.md` — all locked decisions
- Direct codebase read: `.planning/STATE.md` — established patterns (hidden form field decision, composite key, no new deps)

### Secondary (MEDIUM confidence)

- Jinja2 auto-escaping behavior in HTML attribute context: well-established Flask/Jinja2 behavior; `| e` produces `&quot;` for `"` in attribute values.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in `pyproject.toml`; no new dependencies
- Architecture: HIGH — all integration points verified by direct code reading; patterns mirror existing code exactly
- Pitfalls: HIGH — derived from direct inspection of data flow and Jinja2 rendering behavior

**Research date:** 2026-03-14
**Valid until:** 2026-06-14 (stable domain; Flask/Python stdlib serialization patterns don't change)
