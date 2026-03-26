# Phase 7: Polish - Research

**Researched:** 2026-03-14
**Domain:** Vanilla JS DOM manipulation, Jinja2 template extension, Python/pytest HTML assertion
**Confidence:** HIGH

## Summary

Phase 7 is the final v1.1 phase. It adds two UI features (active constraint count display, sortable table columns) and server-side HTML-presence tests for the Clear All button that was already delivered in Phase 6. Everything is client-side JS + Jinja2 only — no Python backend changes, no new dependencies, no new routes.

The constraint count display (UI-06) is a new DOM element rendered by Jinja2 above the Re-Optimize button. Its numeric value is maintained entirely by JS listeners attached to existing checkbox classes. The sortable columns feature is a pure-JS table sort with click handlers on `<th>` headers. Both features follow the established pattern of vanilla JS + `document.querySelectorAll` — no libraries needed.

The existing test infrastructure (pytest, Flask test client, HTML string assertions in `test_web.py`) handles the server-side HTML-presence tests cleanly. JS behavior (sort order, count updates) is not tested by Python tests — this is an explicit project decision recorded in CONTEXT.md.

**Primary recommendation:** Implement as two focused plans — (1) count display + Clear All tests, (2) sortable columns. Each plan is self-contained and can be verified independently.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Active constraint count display (UI-06)
- Live JS counter — updates instantly as checkboxes are toggled, no server round-trip
- Placement: above the Re-Optimize button, outside the collapsible player pool section
- Format: `Locks: 2 | Excludes: 1`
- Lock Golfer checkboxes count as locks (not tracked separately)
- Hidden completely when count is 0 — no "No active constraints" message, just invisible
- Count also resets to 0 visually when Clear All is clicked (JS updates it immediately)

#### Clear-all button (UI-05)
- Button already exists in template from Phase 6 work
- Tests needed: HTML presence tests only (server-side) — verify button renders when results are shown
- Behavior (unchecking, count reset) is pure JS — not tested via Python tests

#### Sortable player pool columns
- All columns are sortable: Lock, Lock Golfer, Exclude, Player, Collection, Salary, Multiplier, Proj Score
- Default sort on page load: Player name A-Z (matches current server-side order)
- Click once: descending; click again: ascending; toggle on each click
- Sort indicator: ▲ for ascending, ▼ for descending in the column header next to the label
- Checkbox column sort order: checked rows first when descending, unchecked first when ascending
- Sort state resets to default (Player A-Z) on Re-Optimize re-render — not persisted through form submission
- Pure JS implementation — no libraries, consistent with existing vanilla JS in the template

#### Test scope for count display (UI-06)
- Server-side tests verify the count element is present in the HTML response when results are shown
- Count value is computed by JS — not asserted in Python tests

### Claude's Discretion
- CSS styling for the count display (color, font weight, spacing above Re-Optimize)
- Exact HTML element for count display (span, div, p)
- CSS class name for the count element
- JS implementation approach for sort (e.g., data attributes vs. cell text parsing)
- Arrow styling (Unicode ▲▼ vs CSS pseudo-elements)

### Deferred Ideas (OUT OF SCOPE)
- Site-wide visual design (color scheme, typography, layout aesthetics) — future milestone (v1.2 or dedicated design phase)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-05 | User can clear all locks and excludes with a single button | Button already exists in template (`id="clear-all-btn"`, line 61). Tests needed: server-side HTML presence assertion that the button renders when `show_results` is true. |
| UI-06 | App shows count of active locks and excludes above the Optimize button | New Jinja2 element rendered above Re-Optimize button (line 121). Count maintained by JS event listeners on `.lock-cb`, `.lock-golfer-cb`, `.exclude-cb`. Server-side test confirms element is present in HTML. |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla JS | ES5+ | DOM manipulation, event listeners, table sort | Already in use; project decision is no JS frameworks |
| Jinja2 | (Flask-bundled) | Server-side HTML rendering for count element | All templates already use Jinja2 |
| pytest | >=8.0 | Server-side HTML-presence assertions | Existing test infrastructure |
| Flask test client | (Flask-bundled) | HTTP-level integration tests | Already used in `test_web.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None | — | — | All phase work fits existing stack |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vanilla JS sort | `tablesort` or `sorttable.js` | Project decision: no JS libraries |
| Unicode ▲▼ indicators | CSS `:after` pseudo-elements | Both valid; Unicode is simpler, project has discretion |
| `data-*` attributes for sort keys | Parsing cell text directly | `data-*` is more robust for salary ($) and multiplier formatting; recommended |

**Installation:** No new packages needed.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed. All changes land in:

```
gbgolf/web/templates/index.html   # Jinja2 count element + th sort headers
tests/test_web.py                 # New server-side HTML presence tests
```

### Pattern 1: Constraint Count Display (UI-06)

**What:** A single hidden DOM element above the Re-Optimize button that JS shows/hides based on active checkbox counts.

**When to use:** Any time checkbox state must be reflected in UI without a server round-trip.

**Implementation approach:**

```html
<!-- Rendered by Jinja2 — JS controls visibility and text -->
<div id="constraint-count" style="display:none;"></div>
<button type="submit">Re-Optimize</button>
```

```javascript
function updateConstraintCount() {
  var locks = document.querySelectorAll(".lock-cb:checked, .lock-golfer-cb:checked").length;
  var excludes = document.querySelectorAll(".exclude-cb:checked").length;
  var el = document.getElementById("constraint-count");
  if (!el) return;
  if (locks === 0 && excludes === 0) {
    el.style.display = "none";
  } else {
    el.textContent = "Locks: " + locks + " | Excludes: " + excludes;
    el.style.display = "";
  }
}
```

Call `updateConstraintCount()` from:
- Each `.lock-cb` / `.lock-golfer-cb` / `.exclude-cb` `change` listener (extend existing blocks, lines 211-224)
- `clearAllCheckboxes()` (extend existing function, lines 225-230)
- On page load (after pre-checked initialization block, lines 232-241) to initialize count from server-rendered checked state

**Note on Lock Golfer counting:** `.lock-golfer-cb:checked` counts toward locks. The selector `".lock-cb:checked, .lock-golfer-cb:checked"` handles both in one `querySelectorAll` call.

### Pattern 2: Sortable Table Columns

**What:** Click handlers on `<th>` elements reorder `<tbody>` rows in-place. Rows are sorted by reading a `data-*` attribute on each `<td>`.

**When to use:** Client-side table sort with no backend calls needed.

**Recommended approach — data attributes on `<td>` cells:**

Add `data-sort` attributes to each `<td>` in the player pool tbody rows so JS does not need to parse display text (which has `$` prefix for salary, `%` for multiplier, etc.):

```html
<!-- Example row in Jinja2 template -->
<tr>
  <td data-sort="{{ 1 if ... else 0 }}">...</td>   <!-- Lock checkbox -->
  <td data-sort="{{ 1 if ... else 0 }}">...</td>   <!-- Lock Golfer checkbox -->
  <td data-sort="{{ 1 if ... else 0 }}">...</td>   <!-- Exclude checkbox -->
  <td data-sort="{{ card.player }}">{{ card.player }}</td>
  <td data-sort="{{ card.collection }}">{{ card.collection }}</td>
  <td data-sort="{{ card.salary }}">{{ card.salary }}</td>
  <td data-sort="{{ card.multiplier }}">{{ card.multiplier }}</td>
  <td data-sort="{{ card.projected_score or 0 }}">...</td>
</tr>
```

**Sort function skeleton:**

```javascript
var sortState = { col: 3, asc: true };  // default: Player A-Z (col index 3)

function sortTable(colIndex) {
  var asc = (sortState.col === colIndex) ? !sortState.asc : false; // first click = descending
  sortState = { col: colIndex, asc: asc };
  var tbody = document.querySelector("#player-pool-section table tbody");
  var rows = Array.from(tbody.querySelectorAll("tr"));
  rows.sort(function(a, b) {
    var aVal = a.cells[colIndex].dataset.sort;
    var bVal = b.cells[colIndex].dataset.sort;
    // Numeric sort if both parse as numbers
    var aNum = parseFloat(aVal), bNum = parseFloat(bVal);
    var cmp = (!isNaN(aNum) && !isNaN(bNum))
      ? aNum - bNum
      : aVal.localeCompare(bVal);
    return asc ? cmp : -cmp;
  });
  rows.forEach(function(r) { tbody.appendChild(r); });
  updateSortIndicators(colIndex, asc);
}

function updateSortIndicators(activeCol, asc) {
  document.querySelectorAll("#player-pool-section table thead th").forEach(function(th, i) {
    // Remove old indicators, add new one on active column
    th.textContent = th.textContent.replace(/[▲▼]\s*$/, "").trimEnd();
    if (i === activeCol) {
      th.textContent += " " + (asc ? "▲" : "▼");
    }
  });
}
```

**Checkbox column sort:** `data-sort` is `"1"` for checked, `"0"` for unchecked. Numeric sort means checked-first when descending (1 > 0), unchecked-first when ascending.

**`th` click binding:**

```html
<th onclick="sortTable(0)">Lock</th>
<th onclick="sortTable(1)">Lock Golfer</th>
<th onclick="sortTable(2)">Exclude</th>
<th onclick="sortTable(3)">Player</th>
...
```

**Sort state reset on Re-Optimize:** The page re-renders from the server after form submission, so `sortState` is reset automatically — no explicit reset code needed.

**Initial default sort indicator:** Call `updateSortIndicators(3, true)` on page load (or set the Player `<th>` text to include `▲` in the template). The simplest approach is to call it from a DOMContentLoaded script block or immediately in the `<script>` tag after all function definitions.

### Anti-Patterns to Avoid

- **Storing sort data in displayed text:** `$10,000` and `10000` sort differently. Always use `data-sort` with raw numeric values.
- **Re-querying checkboxes after sort:** Row reorder does NOT change checkbox `name`/`value` attributes; form submission still works correctly. No special handling needed.
- **Updating `th.textContent` destructively:** If `onclick` is set via attribute, updating `textContent` removes the handler. Use `innerHTML` carefully, or keep the label in a `<span>` inside `<th>`. Alternatively, strip only the indicator character (as shown in `updateSortIndicators` above) rather than replacing all content.
- **Calling `updateConstraintCount()` before DOM is ready:** All JS in this project is at the bottom of `<body>`, so DOM is ready when scripts run — no `DOMContentLoaded` guard needed (consistent with existing pattern).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table sort library | Custom sort with edge cases | The vanilla sort pattern above | Checkbox columns need special sort key — handled by `data-sort="0/1"` trick |
| Live form field counting | Custom MutationObserver | `change` event on existing classes | `.lock-cb`, `.lock-golfer-cb`, `.exclude-cb` already have `change` listeners — extend them |

**Key insight:** The existing JS event listener blocks (lines 211-224) are the right extension point. Don't create parallel listener registration; extend the existing `forEach` callbacks.

---

## Common Pitfalls

### Pitfall 1: `th.textContent` Clobbers `onclick` Attribute

**What goes wrong:** Setting `th.textContent = "Lock ▲"` replaces the element's child text, but does NOT affect `onclick` attributes set in HTML. However, if the handler was attached via `addEventListener` instead of attribute, content changes don't affect it. The real risk is overwriting attribute-set `onclick` if you use `th.innerHTML`.

**Why it happens:** Confusion between `textContent`, `innerHTML`, and attribute-based event handlers.

**How to avoid:** Use `th.textContent` (not `innerHTML`) for text updates. Attribute-based `onclick="sortTable(0)"` is preserved regardless of `textContent` changes.

**Warning signs:** Sort stops working after first click on a column; click handler disappears.

### Pitfall 2: Count Element Missing from DOM When `show_results` is False

**What goes wrong:** The count `<div id="constraint-count">` is inside the `{% if show_results and card_pool_json %}` block. JS calls `document.getElementById("constraint-count")` and gets `null` on GET (no results yet). The `updateConstraintCount()` function has a null-guard (`if (!el) return`) to handle this.

**Why it happens:** Conditional Jinja2 rendering means the element doesn't exist on every page state.

**How to avoid:** Null-guard the element reference in every JS function that touches `constraint-count`. Pattern already used by the `rf` (reoptimize-form) null check at line 205.

**Warning signs:** `TypeError: Cannot read properties of null (reading 'style')` in browser console.

### Pitfall 3: Lock Golfer Checkbox Counted Twice

**What goes wrong:** A player can have both a `.lock-cb` (card lock) and `.lock-golfer-cb` (golfer lock) checked. If counted separately and summed, the display says "Locks: 2" when the user only checked one golfer-level lock.

**Why it happens:** CONTEXT.md states "Lock Golfer checkboxes count as locks (not tracked separately)" — they are merged into the lock count, not added separately.

**How to avoid:** Use combined selector: `".lock-cb:checked, .lock-golfer-cb:checked"` for the lock count. These are distinct checkboxes on distinct rows — double-counting risk is only if you query each separately and add totals.

**Warning signs:** Lock count is higher than expected when Lock Golfer is checked.

### Pitfall 4: Sort Breaks After Reoptimize Response (Row Count Changes)

**What goes wrong:** The player pool table is inside a `<form>` that POSTs to `/reoptimize`, which re-renders the page. After the server response, sort state is gone — that's expected and intentional. However, if someone calls `sortTable()` on a table that has `0` rows (e.g., before card_pool renders), the function must handle empty tbody gracefully.

**How to avoid:** The sort function should be a no-op when tbody has no rows. `Array.from(tbody.querySelectorAll("tr"))` returns `[]` and the sort/append loop does nothing — safe by default.

### Pitfall 5: Server-Side Tests Assert Dynamic Count Value

**What goes wrong:** A test tries to assert `"Locks: 2"` in the HTML response, but the count is computed by JS — the server only renders `"Locks: 0"` or an empty element.

**Why it happens:** Confusion about what server renders vs. what JS updates.

**How to avoid:** Server-side tests for UI-06 only assert element presence (e.g., `'id="constraint-count"'` in html), not count values. This is an explicit CONTEXT.md decision.

---

## Code Examples

Verified patterns from existing codebase:

### Existing clearAllCheckboxes (lines 225-230) — extend this

```javascript
// Current (index.html lines 225-230):
function clearAllCheckboxes() {
  document.querySelectorAll(".lock-cb, .lock-golfer-cb, .exclude-cb").forEach(function(cb) {
    cb.checked = false;
    cb.disabled = false;
  });
  // ADD: updateConstraintCount(); here
}
```

### Existing change listeners (lines 211-224) — extend these

```javascript
// Current lock-cb listener (index.html lines 211-217):
document.querySelectorAll(".lock-cb").forEach(function(lockCb) {
  lockCb.addEventListener("change", function() {
    var row = lockCb.closest("tr");
    var excludeCb = row.querySelector(".exclude-cb");
    if (excludeCb) excludeCb.disabled = lockCb.checked;
    // ADD: updateConstraintCount(); here
  });
});
// Same pattern for .lock-golfer-cb and .exclude-cb
```

### HTML presence test pattern (matches existing test_web.py style)

```python
def test_clear_all_button_rendered(client):
    """POST CSVs → HTML contains the Clear All button when results are shown."""
    response = _post_csvs(client, SAMPLE_ROSTER_CSV, SAMPLE_PROJECTIONS_CSV)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert 'id="clear-all-btn"' in html

def test_constraint_count_element_rendered(client):
    """POST CSVs → HTML contains the constraint count element when results are shown."""
    response = _post_csvs(client, SAMPLE_ROSTER_CSV, SAMPLE_PROJECTIONS_CSV)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert 'id="constraint-count"' in html
```

### Null-guard pattern (from existing line 205)

```javascript
// Existing pattern for conditionally-rendered elements:
const rf = document.getElementById("reoptimize-form");
if (rf) {
  rf.addEventListener("submit", function () { ... });
}
// Apply same pattern for constraint-count:
function updateConstraintCount() {
  var el = document.getElementById("constraint-count");
  if (!el) return;
  // ... update logic
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Library-based table sort (e.g., DataTables) | Vanilla JS sort on `data-*` attributes | Project decision from start | No extra JS payload; consistent with existing code |
| Showing "0 constraints" when idle | Hide element entirely when count is 0 | Phase 7 CONTEXT.md decision | Cleaner UI; JS controls `display:none` toggle |

**Deprecated/outdated:**
- None applicable to this phase.

---

## Open Questions

1. **`th.textContent` vs. labeled `<span>` for sort indicators**
   - What we know: `textContent` setter replaces ALL child text nodes; `onclick` attributes are unaffected
   - What's unclear: Whether stripping indicator chars from `textContent` is robust enough if label text ever contains ▲▼ for other reasons
   - Recommendation: Use `textContent` strip approach (show in architecture pattern). The player pool headers have no ▲▼ in their labels today so stripping is safe.

2. **Initial sort indicator on page load**
   - What we know: Default sort is Player A-Z; indicator should be ▲ on Player header
   - What's unclear: Whether to render the indicator in Jinja2 (static) or set it via JS on page load
   - Recommendation: Set it via JS (call `updateSortIndicators(3, true)` at end of script block) — consistent with the dynamic pattern and avoids Jinja2 changes

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_web.py -x -q` |
| Full suite command | `pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-05 | Clear All button renders in HTML when results shown | unit (HTML assertion) | `pytest tests/test_web.py::test_clear_all_button_rendered -x` | Wave 0 — add to `test_web.py` |
| UI-05 | Clear All button absent on GET (no results) | unit (HTML assertion) | `pytest tests/test_web.py::test_clear_all_button_absent_on_get -x` | Wave 0 — add to `test_web.py` |
| UI-06 | Constraint count element renders in HTML when results shown | unit (HTML assertion) | `pytest tests/test_web.py::test_constraint_count_element_rendered -x` | Wave 0 — add to `test_web.py` |
| UI-06 | Constraint count absent on GET (no results) | unit (HTML assertion) | `pytest tests/test_web.py::test_constraint_count_absent_on_get -x` | Wave 0 — add to `test_web.py` |
| Sortable cols | Sort headers present in player pool `<thead>` | unit (HTML assertion) | `pytest tests/test_web.py::test_sort_headers_rendered -x` | Wave 0 — add to `test_web.py` |

**JS behavior (sort order, count updates, clear-all unchecking) — manual-only:** These are pure client-side behaviors with no server-observable state. Python tests cannot assert JS execution results. Verified manually in browser.

### Sampling Rate

- **Per task commit:** `pytest tests/test_web.py -x -q`
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] 5 new test functions in `tests/test_web.py` (file exists, add to it) — covers UI-05 and UI-06
- [ ] No new test files, no new fixtures, no framework changes needed

---

## Sources

### Primary (HIGH confidence)

- `gbgolf/web/templates/index.html` — full template read; all line references verified
- `tests/test_web.py` — existing test patterns, fixture structure, helper functions
- `pyproject.toml` — pytest configuration, test paths, addopts
- `.planning/phases/07-polish/07-CONTEXT.md` — all decisions verified verbatim
- `.planning/REQUIREMENTS.md` — UI-05 and UI-06 requirement definitions

### Secondary (MEDIUM confidence)

- MDN documentation on `Element.textContent`, `HTMLTableElement`, `dataset` — well-established browser APIs, no version concerns for ES5+ vanilla JS

### Tertiary (LOW confidence)

- None — all findings grounded in direct code inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; verified against existing codebase
- Architecture: HIGH — patterns derived directly from existing code in the template; no guesswork
- Pitfalls: HIGH — identified from code inspection and explicit CONTEXT.md constraints
- Test patterns: HIGH — derived from existing `test_web.py` patterns

**Research date:** 2026-03-14
**Valid until:** Stable — no external dependencies; valid until template is substantially restructured
