# Phase 1: Data Foundation - Research

**Researched:** 2026-03-13
**Domain:** Python CSV parsing, data validation, CLI tooling, package structure
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Player name matching**: Normalize before comparing — lowercase + trim whitespace (no punctuation stripping). If normalized names still don't match, card is excluded and reported. Unmatched report shows the exact roster name that couldn't be matched.
- **Unmatched card handling**: Cards with no projection match are excluded from the optimizer pool entirely (not included with score=0). Exclusion report is a flat list, one card per row, with reason noted inline. Three exclusion reasons: no projection found, $0 salary, expired card.
- **Validation error behavior**:
  - Roster CSV format error (wrong/missing columns, can't be parsed): fail immediately with a clear error message, no partial processing
  - Projections CSV bad row (missing or non-numeric score): skip that row with a warning, continue loading the rest
  - Too few valid cards after filtering: fail with a clear message before passing to the optimizer
- **Phase 1 interface**: Delivers a Python module (imported by Phase 2 optimizer) AND a standalone CLI validation command
  - CLI command: `python -m gbgolf.data validate roster.csv projections.csv`
  - Default output: summary (valid card count, total parsed, exclusion count) + exclusion report
  - Verbose output (`--verbose` flag): also lists every valid card with its effective value
  - CLI also validates the contest config JSON

### Claude's Discretion
- Exact Python module structure and file layout
- Contest config JSON schema design (fields, nesting)
- How expired date parsing handles edge cases (invalid date formats)
- Specific error message wording

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UPLD-01 | User can upload a GameBlazers roster CSV export (columns: Player, Positions, Team, Multiplier, Overall, Franchise, Rookie, Tradeable, Salary, Collection, Status, Expires) | CSV parsing with column validation, dataclass card model |
| UPLD-02 | User can upload a weekly projections CSV containing player name and projected fantasy score | Flexible CSV parsing, name normalization for matching |
| OPT-05 | Effective card value is calculated as projected_score × multiplier | Simple arithmetic on parsed float fields |
| OPT-07 | Contest parameters (salary cap, salary floor, roster size, max entries, collection limits) are stored in an editable JSON config file | JSON config loading with Pydantic validation at boundary |
| DATA-01 | Cards with $0 salary are automatically excluded from optimization | Filter during card loading; include in exclusion report |
| DATA-02 | App surfaces a report of roster players with no matching projection | Name normalization + match loop; collect unmatched cards |
| DATA-03 | Cards past their Expires date are automatically excluded from optimization | Date parsing with datetime.strptime + datetime.date.today() comparison |
</phase_requirements>

---

## Summary

Phase 1 is a pure Python data pipeline: read two CSVs, validate structure, normalize and match player names, apply three exclusion filters ($0 salary, expired date, no projection match), calculate effective values, load a JSON config, and expose results as a Python module plus a CLI validation command. There is no web layer in this phase; the outputs are in-memory Python objects (dataclasses) and printed/returned reports.

The scope is well-suited to Python's standard library plus two lightweight dependencies: `python-dateutil` for flexible date parsing of the "Expires" column and `pydantic` (v2) at the config-loading boundary. The CSV parsing itself should use Python's built-in `csv.DictReader` — the roster is small (hundreds of cards at most), and pandas introduces unnecessary weight for a project that only ever reads two small files.

The locked decision to use lowercase + trim (no punctuation stripping) for name matching is sensible for golf names. One important caveat: golfer names with Unicode accents (Ludvig Åberg, Nicolai Højgaard, etc.) will not normalize correctly with lowercase + strip alone. The planner should decide whether to add `unicodedata.normalize('NFKD', ...)` + ASCII encoding as part of the normalization step — this is not explicitly locked and falls under Claude's Discretion for edge cases.

**Primary recommendation:** Use `csv.DictReader` for parsing, plain `@dataclass` objects for internal card representation, `pydantic` v2 for JSON config validation only, `datetime.strptime` with `dateutil` fallback for date parsing, and `argparse` (stdlib) for the CLI — minimizing external dependencies while keeping the interface clean and testable.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `csv` (stdlib) | Python 3.10+ | Parse roster and projections CSVs | No deps; DictReader maps headers to fields automatically |
| `dataclasses` (stdlib) | Python 3.10+ | Card and report data containers | Zero-cost; fast instantiation; serializable via `dataclasses.asdict()` |
| `datetime` (stdlib) | Python 3.10+ | Expiration date comparison | `datetime.strptime` + `datetime.date.today()` covers all needs |
| `json` (stdlib) | Python 3.10+ | Load contest config file | stdlib; pairs naturally with Pydantic for validation |
| `pydantic` | v2.x | Validate contest config JSON at load boundary | Runtime validation with clear error messages; used only at the config boundary |
| `python-dateutil` | 2.9.x | Fallback date parsing for ambiguous Expires values | Handles formats strptime misses; graceful parse errors |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unicodedata` (stdlib) | Python 3.10+ | NFKD normalization for accented golfer names | Use if name matching misses accented names; zero cost |
| `argparse` (stdlib) | Python 3.10+ | CLI argument parsing for `python -m gbgolf.data validate` | No extra deps; sufficient for one subcommand + one flag |
| `pytest` | 8.x | Unit and integration testing | Standard Python test framework |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `csv.DictReader` | `pandas.read_csv` | Pandas is 50–100MB dep, adds PyArrow complexity; unnecessary for files with < 1,000 rows |
| `argparse` | `click` or `typer` | Click/Typer are better for complex multi-command CLIs; one subcommand with one flag doesn't justify the dependency |
| `pydantic` v2 | `jsonschema` | Pydantic gives richer Python error objects and generates schema; jsonschema is more config, less Pythonic |
| `python-dateutil` | multiple `strptime` formats | dateutil handles ambiguous formats automatically; strptime alone requires enumerating every possible format GameBlazers uses |

**Installation:**
```bash
pip install pydantic python-dateutil pytest
```

---

## Architecture Patterns

### Recommended Project Structure
```
gbgolf/
├── __init__.py
├── data/
│   ├── __init__.py          # Public API: load_cards(), load_config(), validate_pipeline()
│   ├── __main__.py          # Entry point for: python -m gbgolf.data validate ...
│   ├── models.py            # Card, ContestConfig, ExclusionRecord dataclasses
│   ├── roster.py            # parse_roster_csv() — reads roster CSV, returns List[Card]
│   ├── projections.py       # parse_projections_csv() — reads projections CSV, returns Dict[str, float]
│   ├── matching.py          # normalize_name(), match_projections() — enriches cards
│   ├── filters.py           # apply_filters() — $0 salary, expired, no match
│   ├── config.py            # load_contest_config() — JSON load + Pydantic validation
│   └── report.py            # build_exclusion_report(), format_summary(), format_verbose()
tests/
├── conftest.py              # Shared fixtures: sample CSV strings, tmp file helpers
├── test_roster.py           # parse_roster_csv() — valid/invalid columns, bad rows
├── test_projections.py      # parse_projections_csv() — bad rows skipped, warnings
├── test_matching.py         # normalize_name(), match_projections() — accents, case, whitespace
├── test_filters.py          # $0 salary, expired, no-match exclusion logic
├── test_config.py           # ContestConfig — missing fields, bad values
└── test_pipeline.py         # Integration: end-to-end validate_pipeline()
pyproject.toml
```

### Pattern 1: Fail-Fast CSV Loading with DictReader
**What:** Validate required headers immediately on open; raise `ValueError` with specific message before reading any rows.
**When to use:** Roster CSV (hard fail). Not projections CSV (soft fail — skip bad rows).
**Example:**
```python
# Source: Python stdlib csv docs + pattern from Python Application Layouts guide
import csv

REQUIRED_ROSTER_COLUMNS = {
    "Player", "Multiplier", "Salary", "Collection", "Expires"
}

def parse_roster_csv(path: str) -> list[Card]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Roster CSV is empty or unreadable: {path}")
        missing = REQUIRED_ROSTER_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"Roster CSV missing required columns: {sorted(missing)}"
            )
        cards = []
        for row in reader:
            cards.append(_row_to_card(row))
    return cards
```

### Pattern 2: Name Normalization Function
**What:** A pure function that normalizes a player name for comparison. Applied to both roster names and projection names before matching.
**When to use:** Always — called during `match_projections()`.
**Example:**
```python
import unicodedata

def normalize_name(name: str) -> str:
    """Lowercase + strip whitespace + NFKD accent decomposition."""
    name = name.strip().lower()
    # Decompose accented chars (e.g. Å -> A + combining ring) then drop combining marks
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    return name
```
Note: The locked decision says "lowercase + trim whitespace (no punctuation stripping)." NFKD accent stripping is an edge-case extension not in conflict with the locked decision — it handles golfer names like Ludvig Åberg or Nicolai Højgaard that would otherwise never match. This falls under Claude's Discretion for edge cases.

### Pattern 3: Dataclass Card Model
**What:** A plain `@dataclass` representing one card. Instantiated after parsing and enrichment. Passed to Phase 2 optimizer.
**When to use:** Core internal data structure throughout phases 1 and 2.
**Example:**
```python
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

@dataclass
class Card:
    player: str
    salary: int
    multiplier: float
    collection: str          # e.g. "Weekly Collection", "Core"
    expires: Optional[date]
    projected_score: Optional[float] = None
    effective_value: Optional[float] = None   # projected_score * multiplier

@dataclass
class ExclusionRecord:
    player: str
    reason: str   # "no projection found" | "$0 salary" | "expired card"

@dataclass
class ValidationResult:
    valid_cards: list[Card]
    excluded: list[ExclusionRecord]
    projection_warnings: list[str]   # bad projection rows skipped
```

### Pattern 4: Pydantic ContestConfig at Config Boundary
**What:** Pydantic model used only to validate the JSON config file. Convert to a simple dataclass after validation.
**When to use:** `load_contest_config()` — once at startup.
**Example:**
```python
from pydantic import BaseModel, field_validator

class ContestConfigModel(BaseModel):
    name: str
    salary_min: int
    salary_max: int
    roster_size: int
    max_entries: int
    max_weekly_collection: int
    max_core: int

    @field_validator("salary_max")
    @classmethod
    def salary_range_valid(cls, v, info):
        if "salary_min" in info.data and v <= info.data["salary_min"]:
            raise ValueError("salary_max must be greater than salary_min")
        return v
```

### Anti-Patterns to Avoid
- **Loading projections as a list, then doing O(n²) matching:** Build a dict keyed by normalized name up front; matching is O(1) per card.
- **Catching all exceptions silently:** Only projections CSV bad rows are soft-skipped; everything else should bubble up with context.
- **Using float for salary:** GameBlazers salaries are whole-dollar integers; parse as `int` and keep them that way to avoid floating-point equality issues.
- **Storing the raw CSV string in the Card:** Cards must be serializable for Phase 3; keep only the fields Phase 2 needs.
- **Putting CLI logic in module functions:** `__main__.py` handles argument parsing and output formatting; `data/__init__.py` exposes pure functions that return data objects.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date parsing for ambiguous formats | Custom strptime loop with multiple format strings | `python-dateutil` parser | dateutil handles M/D/YYYY, YYYY-MM-DD, D-Mon-YYYY and a dozen others; custom loops miss formats GameBlazers may use |
| Config schema validation | Manual if-key-exists checks | `pydantic` v2 BaseModel | Pydantic gives field-level error messages, type coercion, and constraint validators for free |
| Accent normalization | Roll-your-own character replacement table | `unicodedata.normalize('NFKD', ...)` + combining char filter | stdlib; handles all Unicode combining marks correctly including precomposed vs. decomposed forms |

**Key insight:** The hard part of this phase is not parsing — it's producing a useful, actionable exclusion report. Invest in clear data models (`ExclusionRecord`) and clean separation between parsing, matching, filtering, and reporting.

---

## Common Pitfalls

### Pitfall 1: Missing Columns Cause Confusing KeyErrors
**What goes wrong:** `csv.DictReader` silently sets missing fields to `None`; `row["Salary"]` raises `KeyError` deep in parsing with no context about the file.
**Why it happens:** DictReader does not validate headers — it just maps whatever columns exist.
**How to avoid:** Validate `reader.fieldnames` against `REQUIRED_ROSTER_COLUMNS` immediately after opening the file; raise `ValueError` with the column names listed.
**Warning signs:** `KeyError: 'Salary'` or `TypeError` in `_row_to_card`.

### Pitfall 2: Salary Parsed as Float, Causing $0.0 vs $0 Mismatch
**What goes wrong:** `float("0")` is truthy in some comparisons; comparison logic written as `if card.salary == 0` works but `if not card.salary` would also catch negative salaries unexpectedly.
**Why it happens:** CSV values are strings; naive `float()` conversion is common.
**How to avoid:** Parse salary as `int(float(row["Salary"]))` to handle values like "0.00"; filter with `card.salary == 0`.
**Warning signs:** Cards with salary "0.00" not being excluded.

### Pitfall 3: Expired Date Comparison Off by One (Today vs. Strictly Past)
**What goes wrong:** A card expiring today is included or excluded depending on whether the comparison is `<` or `<=`.
**Why it happens:** "Expired" is ambiguous — does expiry on today's date mean usable today or not?
**How to avoid:** Decide and document the rule explicitly: cards are excluded if `expires < datetime.date.today()` (expired cards are those where the expiry date is strictly in the past; a card expiring today is still valid). Encode this in a comment next to the filter.
**Warning signs:** User reports a card expiring "today" is incorrectly excluded.

### Pitfall 4: Accented Names Never Match
**What goes wrong:** "Ludvig Åberg" in the roster CSV and "Ludvig Aberg" in the projections CSV (a common data entry variation) never match with lowercase + strip alone.
**Why it happens:** `å` and `a` are different code points; lowercase does not strip diacritics.
**How to avoid:** Add NFKD normalization to `normalize_name()`. This is within Claude's Discretion for edge-case date handling.
**Warning signs:** Well-known golfers consistently appearing in the exclusion report with "no projection found" reason.

### Pitfall 5: Projections Dict Built After Normalization but Roster Not Normalized
**What goes wrong:** Projection names normalized but roster names matched raw (or vice versa), so even identical names don't match.
**Why it happens:** Normalization applied inconsistently across the two datasets.
**How to avoid:** Centralize normalization in a single `normalize_name()` function; apply it identically to both sides when building the projections dict and when looking up each card's player name.
**Warning signs:** 100% of cards show "no projection found" in a test with known-good data.

### Pitfall 6: "Too Few Cards" Check Happens Too Late
**What goes wrong:** The optimizer in Phase 2 receives an empty or near-empty card pool and produces a cryptic solver error.
**Why it happens:** Minimum card count validation is skipped or placed in Phase 2.
**How to avoid:** After applying all filters, count `len(valid_cards)`. Determine minimum per contest type from the loaded config (`roster_size`). Raise `ValueError` with message like: "Only 4 valid cards found — Tips contest requires at least 6. Check your exclusion report."
**Warning signs:** Phase 2 optimizer raises solver-level errors with empty pools.

---

## Code Examples

Verified patterns from official sources:

### Date Parsing with strptime + dateutil Fallback
```python
# Source: python-dateutil official docs (dateutil.readthedocs.io)
# and Python stdlib datetime docs
from datetime import date
from dateutil import parser as dateutil_parser

def parse_expires(raw: str) -> date | None:
    """Parse Expires column value. Returns None if blank or unparseable."""
    raw = raw.strip()
    if not raw:
        return None
    # Try ISO format first (fast path)
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass
    # Fallback to dateutil for other formats GameBlazers might use
    try:
        return dateutil_parser.parse(raw, dayfirst=False).date()
    except Exception:
        # Log warning; treat as no expiry (don't exclude)
        return None
```

### python -m gbgolf.data Entry Point Pattern
```python
# Source: Python Packaging User Guide - src layout + __main__.py pattern
# gbgolf/data/__main__.py
import argparse
import sys
from gbgolf.data import validate_pipeline

def main():
    parser = argparse.ArgumentParser(
        prog="python -m gbgolf.data",
        description="Validate roster and projections CSVs",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    val = sub.add_parser("validate", help="Parse and validate input files")
    val.add_argument("roster_csv")
    val.add_argument("projections_csv")
    val.add_argument("--config", default="contest_config.json")
    val.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.command == "validate":
        try:
            result = validate_pipeline(
                args.roster_csv, args.projections_csv, args.config
            )
            # print summary + exclusion report
            # if --verbose, also print all valid cards
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
```

### Contest Config JSON Schema (Recommended Design)
```json
{
  "contests": [
    {
      "name": "The Tips",
      "salary_min": 30000,
      "salary_max": 64000,
      "roster_size": 6,
      "max_entries": 3,
      "collection_limits": {
        "Weekly Collection": 3,
        "Core": 6
      }
    },
    {
      "name": "The Intermediate Tee",
      "salary_min": 20000,
      "salary_max": 52000,
      "roster_size": 5,
      "max_entries": 2,
      "collection_limits": {
        "Weekly Collection": 2,
        "Core": 5
      }
    }
  ]
}
```
Using a `contests` array supports multiple contest types natively and matches OPT-07. Phase 2 will iterate this list.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `setup.py` + `setup.cfg` | `pyproject.toml` only | PEP 621 (Python 3.11 era) | Simpler project config; `pip install -e .` works cleanly |
| `pydantic` v1 BaseModel | `pydantic` v2 BaseModel | 2023 (v2 stable) | 5-50x faster; `model_validate()` replaces `parse_obj()`; `field_validator` replaces `validator` |
| `fuzzywuzzy` | `rapidfuzz` or stdlib normalization | 2022+ | rapidfuzz is faster with same API; but for this project, NFKD + exact match is simpler and more predictable |

**Deprecated/outdated:**
- `setup.py` as primary project config: replaced by `pyproject.toml`
- `pydantic` v1 `.parse_obj()` / `@validator`: use `.model_validate()` / `@field_validator` in v2
- `fuzzywuzzy`: renamed to `thefuzz`; for this project, don't use fuzzy matching at all — exact match after normalization is more predictable and less likely to produce false positives

---

## Open Questions

1. **Franchise / Rookie column semantics**
   - What we know: REQUIREMENTS.md flags this: "unclear whether these are separate collection types requiring ILP constraints or boolean flags"
   - What's unclear: Whether the `Collection` column already encodes this, or whether `Franchise` and `Rookie` are independent boolean columns with their own lineup constraints
   - Recommendation: Phase 1 should parse and preserve `Franchise` and `Rookie` columns as-is (string or bool). The planner should add a note that Phase 2 must resolve this before building the ILP. Phase 1 is not affected — just preserve the data.

2. **Exact date format used by GameBlazers in the Expires column**
   - What we know: Column is named "Expires" per UPLD-01; format is unspecified
   - What's unclear: Whether GameBlazers uses YYYY-MM-DD, MM/DD/YYYY, or a human-readable format like "Mar 15, 2026"
   - Recommendation: Use `dateutil.parser.parse()` as the primary parser (not fallback) since it handles all common formats. Document that the parser is lenient and log the raw value whenever parsing fails.

3. **Cards with no Expires value**
   - What we know: The filter in DATA-03 excludes cards past their Expires date
   - What's unclear: Whether "no expires" means "never expires" (keep) or "data error" (exclude)
   - Recommendation: Treat blank/missing Expires as "never expires" — include the card. This is the safer default: accidentally including a never-expiring card is better than silently excluding valid cards.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` [tool.pytest.ini_options] section — Wave 0 |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UPLD-01 | Roster CSV with all required columns parses to Card list | unit | `pytest tests/test_roster.py -x` | Wave 0 |
| UPLD-01 | Roster CSV missing required column fails immediately with clear error | unit | `pytest tests/test_roster.py::test_missing_column_fails -x` | Wave 0 |
| UPLD-02 | Projections CSV bad row is skipped with warning, rest loads | unit | `pytest tests/test_projections.py::test_bad_row_skipped -x` | Wave 0 |
| UPLD-02 | Projections CSV valid rows return name->score dict | unit | `pytest tests/test_projections.py -x` | Wave 0 |
| OPT-05 | effective_value = projected_score * multiplier | unit | `pytest tests/test_matching.py::test_effective_value -x` | Wave 0 |
| OPT-07 | ContestConfig loads valid JSON correctly | unit | `pytest tests/test_config.py::test_valid_config -x` | Wave 0 |
| OPT-07 | ContestConfig raises ValidationError for missing/invalid fields | unit | `pytest tests/test_config.py::test_invalid_config -x` | Wave 0 |
| DATA-01 | Card with $0 salary is excluded and appears in report | unit | `pytest tests/test_filters.py::test_zero_salary_excluded -x` | Wave 0 |
| DATA-02 | Card with no projection match is excluded and listed in report | unit | `pytest tests/test_filters.py::test_no_projection_excluded -x` | Wave 0 |
| DATA-02 | Unmatched report shows exact roster name | unit | `pytest tests/test_filters.py::test_unmatched_name_in_report -x` | Wave 0 |
| DATA-03 | Card with past Expires date is excluded | unit | `pytest tests/test_filters.py::test_expired_excluded -x` | Wave 0 |
| DATA-03 | Card expiring today is NOT excluded | unit | `pytest tests/test_filters.py::test_expires_today_included -x` | Wave 0 |
| All | End-to-end validate_pipeline() returns correct counts | integration | `pytest tests/test_pipeline.py -x` | Wave 0 |
| All | CLI `python -m gbgolf.data validate` exits 0 on valid input | integration | `pytest tests/test_pipeline.py::test_cli_valid -x` | Wave 0 |
| UPLD-01 | CLI exits nonzero on malformed roster CSV | integration | `pytest tests/test_pipeline.py::test_cli_bad_roster -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` — shared fixtures: sample CSV content as strings, tmp CSV file factory, sample valid ContestConfig dict
- [ ] `tests/test_roster.py` — covers UPLD-01
- [ ] `tests/test_projections.py` — covers UPLD-02
- [ ] `tests/test_matching.py` — covers OPT-05, DATA-02
- [ ] `tests/test_filters.py` — covers DATA-01, DATA-02, DATA-03
- [ ] `tests/test_config.py` — covers OPT-07
- [ ] `tests/test_pipeline.py` — integration coverage
- [ ] `pyproject.toml` — project metadata + [tool.pytest.ini_options]
- [ ] Framework install: `pip install pytest pydantic python-dateutil`

---

## Sources

### Primary (HIGH confidence)
- Python stdlib `csv` docs (docs.python.org/3/library/csv.html) — DictReader, fieldnames behavior
- Python stdlib `datetime` docs (docs.python.org/3/library/datetime.html) — date.fromisoformat(), date.today()
- Python stdlib `unicodedata` docs (docs.python.org/3/library/unicodedata.html) — normalize(), combining()
- Python Packaging User Guide (packaging.python.org) — src layout, pyproject.toml, __main__.py
- pytest official docs (docs.pytest.org) — fixtures, conftest.py patterns

### Secondary (MEDIUM confidence)
- pydantic v2 official docs (docs.pydantic.dev/latest) — BaseModel, field_validator, model_validate
- dateutil official docs (dateutil.readthedocs.io/en/stable) — parser.parse(), dayfirst parameter
- Real Python: "Python Application Layouts" (realpython.com/python-application-layouts/) — src layout conventions
- SolverForge: "Dataclasses vs Pydantic in Constraint Solvers" (solverforge.org/blog/2025/12/06) — confirms dataclass for internals, Pydantic at boundary pattern

### Tertiary (LOW confidence)
- PyTutorial: "Pandas vs CSV Module" — supports choosing csv module for small files; single source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or well-documented; pydantic v2 and dateutil are stable
- Architecture: HIGH — module structure and patterns follow standard Python packaging conventions verified against official docs
- Pitfalls: MEDIUM — derived from known Python CSV/datetime behaviors plus project-specific edge cases; some depend on actual GameBlazers CSV format not yet seen
- Test map: HIGH — all behaviors are straightforwardly unit-testable

**Research date:** 2026-03-13
**Valid until:** 2026-06-13 (90 days — stable stdlib + pydantic v2 not in flux)
