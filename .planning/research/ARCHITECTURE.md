# Architecture Patterns

**Domain:** Fantasy golf lineup optimizer (DFS / ILP-based)
**Researched:** 2026-03-13

## Recommended Architecture

A three-layer monolith deployed as a single Python process (FastAPI) serving both API endpoints and static frontend files. This is the right shape for a single-user tool with no auth, no real-time features, and a simple request-response workflow.

```
+------------------------------------------------------------------+
|                        Browser (HTML/JS/CSS)                      |
|  Upload CSVs  |  View Lineups  |  Edit Contest Config            |
+-------+------------------+------------------+--------------------+
        |                  |                  |
        v                  v                  v
+------------------------------------------------------------------+
|                     FastAPI Application                           |
|                                                                  |
|  +------------------+  +------------------+  +-----------------+ |
|  | CSV Parsing      |  | Contest Config   |  | Lineup Display  | |
|  | Module           |  | Manager          |  | (JSON response) | |
|  +--------+---------+  +--------+---------+  +-----------------+ |
|           |                     |                     ^          |
|           v                     v                     |          |
|  +------------------+  +------------------+           |          |
|  | Card Inventory   |  | Constraint       |           |          |
|  | (in-memory)      |  | Definitions      |           |          |
|  +--------+---------+  +--------+---------+           |          |
|           |                     |                     |          |
|           +----------+----------+                     |          |
|                      v                                |          |
|           +---------------------+                     |          |
|           | Optimization Engine |---------------------+          |
|           | (PuLP + CBC solver) |                                |
|           +---------------------+                                |
+------------------------------------------------------------------+
```

**No database.** All data is ephemeral per session (uploaded CSVs + config file). A JSON or YAML config file on disk is the only persistent state.

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Frontend (Static HTML/JS)** | File upload UI, lineup display, contest config editing | FastAPI via REST endpoints |
| **CSV Parser** | Validate and parse roster CSV and projections CSV into structured card objects | Card Inventory |
| **Card Inventory** | Hold parsed cards in memory, merge roster data with projections, compute effective values | Optimization Engine |
| **Contest Config Manager** | Load/save contest definitions (salary caps, roster sizes, collection limits) from JSON/YAML file on disk | Optimization Engine, Frontend |
| **Optimization Engine** | Run ILP solver per contest, enforce constraints, implement card locking across lineups | Card Inventory, Contest Config, Lineup Display |
| **Lineup Display** | Serialize optimized lineups as JSON for frontend rendering | Frontend |

## Data Flow

### End-to-End: CSV Upload to Displayed Lineups

```
1. USER uploads roster CSV
   --> POST /api/upload/roster
   --> CSV Parser validates columns, parses rows into Card objects
   --> Card Inventory stores cards in-memory (list of dicts/dataclasses)

2. USER uploads projections CSV
   --> POST /api/upload/projections
   --> CSV Parser validates, parses into {player_name: projected_score} map
   --> Card Inventory merges: each card gets effective_value = projected_score * multiplier
   --> Cards with $0 salary or no projection are flagged/filtered

3. USER triggers optimization
   --> POST /api/optimize
   --> Optimization Engine reads Card Inventory + Contest Config
   --> Sequential ILP solve (see Multi-Lineup Generation below)
   --> Returns JSON: { contests: [ { name, lineups: [ { cards: [...], total_salary, total_value } ] } ] }

4. FRONTEND renders lineups
   --> Display cards grouped by contest, sorted by lineup
   --> Show per-card: player name, salary, multiplier, projected value
   --> Show per-lineup: total salary, total projected score
```

### Card Object Shape

```python
@dataclass
class Card:
    card_id: str          # unique identifier (e.g., row index or generated UUID)
    player_name: str
    salary: int
    multiplier: float     # 1.0 - 1.5
    collection: str       # "Weekly" or "Core"
    status: str           # from CSV
    projected_score: float | None  # merged from projections CSV
    effective_value: float | None  # projected_score * multiplier
```

Key: `card_id` must be unique per card row (not per player), because the same player can have multiple cards with different multipliers/salaries.

## Multi-Lineup Generation with Card Locking

This is the core architectural challenge. The approach: **sequential ILP with cumulative exclusion constraints.**

### Algorithm

```
used_card_ids = set()

for contest in contests_by_priority:        # Tips first, then Intermediate Tee
    for lineup_number in range(contest.num_entries):
        lineup = solve_ilp(
            available_cards = [c for c in all_cards if c.card_id not in used_card_ids],
            salary_min = contest.salary_min,
            salary_max = contest.salary_max,
            roster_size = contest.roster_size,
            max_weekly = contest.max_weekly,
            max_core = contest.max_core,
        )
        used_card_ids.update(card.card_id for card in lineup)
```

### Why Sequential, Not Joint Optimization

A joint optimization (one giant ILP solving all 5 lineups simultaneously) would be theoretically superior -- it globally maximizes total value across all lineups. However:

1. **Priority ordering matters.** The user wants the best possible Tips lineups, not a globally optimal allocation. Cash contest cards should not be weakened to improve non-cash lineups.
2. **Simpler to implement and debug.** Each ILP call is a clean, independent optimization problem.
3. **Performance is not a concern.** With ~200-400 cards and 6-golfer lineups, each ILP solve completes in milliseconds. Running 5 sequential solves is effectively instant.

### ILP Formulation (Single Lineup)

```
Variables:
  x_i in {0, 1} for each available card i    # 1 = card selected

Maximize:
  sum(x_i * effective_value_i)

Subject to:
  sum(x_i) = roster_size                      # exactly N golfers
  salary_min <= sum(x_i * salary_i) <= salary_max
  sum(x_i where collection_i == "Weekly") <= max_weekly
  sum(x_i where collection_i == "Core") <= max_core
  x_i = 0 for all i in used_card_ids         # card locking (exclusion)
```

### Diversity Constraint (Optional Enhancement)

If lineups end up too similar (same 5 of 6 players), an optional diversity constraint can be added in later phases:

```
For lineup k (k > 1 in same contest):
  sum(x_i where i was in lineup k-1) <= roster_size - 1
  # Forces at least 1 different card from previous lineup
```

This is NOT needed for v1 since card locking already forces different cards (same card cannot appear twice). But if the same *player* on different cards keeps appearing, this could help.

## Patterns to Follow

### Pattern 1: Stateless Request Pipeline

**What:** Each optimization request carries all necessary state. The server does not maintain sessions or databases.
**When:** Single-user tools with simple workflows.
**Why:** Eliminates an entire class of bugs (stale state, session management, DB migrations). The uploaded CSVs and config file are the only inputs.

**Implementation:**
- Store uploaded CSV data in server memory (module-level or simple cache dict keyed by a session token / timestamp)
- On optimize, read from that in-memory store
- Data is lost on server restart (acceptable -- user just re-uploads)

### Pattern 2: Config-as-File

**What:** Contest configuration lives in a JSON file on disk, editable via the UI or directly.
**When:** Configuration changes infrequently and a database would be overkill.

```json
{
  "contests": [
    {
      "name": "The Tips",
      "type": "cash",
      "priority": 1,
      "roster_size": 6,
      "num_entries": 3,
      "salary_min": 30000,
      "salary_max": 64000,
      "max_weekly": 3,
      "max_core": 6
    },
    {
      "name": "The Intermediate Tee",
      "type": "non-cash",
      "priority": 2,
      "roster_size": 5,
      "num_entries": 2,
      "salary_min": 20000,
      "salary_max": 52000,
      "max_weekly": 2,
      "max_core": 5
    }
  ]
}
```

### Pattern 3: Separation of Parsing from Optimization

**What:** CSV parsing and validation is a distinct module from the ILP solver. The parser produces clean domain objects; the solver consumes them.
**Why:** Parsing logic is messy (encoding issues, missing columns, duplicate headers). Keeping it separate means the optimizer can be tested with synthetic data, and parsing bugs don't leak into optimization logic.

### Pattern 4: Solver Abstraction

**What:** Wrap PuLP calls in a function with a clean signature: `solve_lineup(cards, constraints) -> list[Card]`.
**Why:** If you ever swap PuLP for OR-Tools (or want to test with a greedy heuristic), the interface stays the same. Also makes unit testing trivial.

```python
def solve_lineup(
    available_cards: list[Card],
    roster_size: int,
    salary_min: int,
    salary_max: int,
    max_weekly: int,
    max_core: int,
) -> list[Card] | None:
    """Returns optimal lineup or None if infeasible."""
    ...
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Database for Ephemeral Data
**What:** Using SQLite/Postgres to store uploaded CSVs and optimization results.
**Why bad:** Adds migration complexity, ORM overhead, and state management for data that lives for one session. The user uploads fresh CSVs each week.
**Instead:** In-memory storage with a simple dict. If persistence across restarts is ever needed, pickle or JSON dump to disk.

### Anti-Pattern 2: Real-Time / WebSocket Optimization
**What:** Streaming partial optimization results to the frontend as the solver works.
**Why bad:** Each ILP solve takes milliseconds. The total pipeline (5 lineups) completes in under a second. Real-time streaming adds complexity for zero user benefit.
**Instead:** Simple POST request, wait for full response, render all lineups at once.

### Anti-Pattern 3: Microservice Split
**What:** Separate services for parsing, optimization, and display.
**Why bad:** This is a single-user tool. Inter-service communication adds latency, deployment complexity, and failure modes for no benefit.
**Instead:** Single FastAPI process with well-separated modules (not services).

### Anti-Pattern 4: Client-Side Optimization
**What:** Running the ILP solver in the browser (e.g., via WASM-compiled solver).
**Why bad:** PuLP/CBC are mature Python-native tools. JavaScript ILP solvers are less capable. Server-side keeps the optimization logic in Python where it belongs.
**Instead:** Browser handles upload and display only. All computation on server.

## Component Build Order

Build order is driven by dependency chains. Each layer depends on the one before it.

```
Phase 1: Foundation
  [Contest Config Manager] -- no dependencies, just read/write JSON
  [CSV Parser]             -- no dependencies, pure data transformation
  [Card dataclass]         -- shared data model

Phase 2: Core Engine
  [Card Inventory]         -- depends on CSV Parser + Card model
  [Optimization Engine]    -- depends on Card Inventory + Contest Config
  (Can be tested with hardcoded data before any UI exists)

Phase 3: API Layer
  [FastAPI endpoints]      -- depends on all Phase 2 components
  [File upload handling]   -- depends on CSV Parser

Phase 4: Frontend
  [Upload UI]              -- depends on API endpoints
  [Lineup Display]         -- depends on API optimize response
  [Config Editor]          -- depends on Config API endpoints
```

**Critical path:** The Optimization Engine is the riskiest and most valuable component. It should be built and tested first (Phase 2), even before the API layer, using hardcoded test data. This validates the ILP formulation before any UI work begins.

## Project Structure

```
gb-golf-optimizer/
  backend/
    app.py                  # FastAPI app, route definitions
    config.py               # Load/save contest config JSON
    models.py               # Card dataclass, Contest dataclass
    parser.py               # CSV parsing and validation
    optimizer.py            # ILP solver (PuLP), multi-lineup generation
    inventory.py            # Card inventory management, projection merging
  frontend/
    index.html              # Single page app
    style.css
    app.js                  # Upload, display, config editing
  config/
    contests.json           # Contest definitions (editable)
  tests/
    test_parser.py
    test_optimizer.py       # Critical: test constraints, card locking
    test_inventory.py
  requirements.txt
```

## Scalability Considerations

| Concern | Current Scale (1 user) | If Scale Grows |
|---------|----------------------|----------------|
| ILP solve time | <100ms per lineup, 5 lineups < 500ms total | Not a concern even at 1000 cards |
| CSV parsing | Instant for 200-400 rows | Not a concern |
| Memory | ~1MB for card inventory | Not a concern |
| Concurrent users | Not needed (single user) | Add request queuing if ever needed |
| Data persistence | None needed | Add SQLite only if multi-session history is requested |

This application will never need to scale beyond a single user running a handful of optimizations per week. Architecture decisions should optimize for simplicity and correctness, not scalability.

## Sources

- PuLP library documentation (coin-or.github.io/pulp) -- HIGH confidence on ILP formulation patterns
- FastAPI documentation (fastapi.tiangolo.com) -- HIGH confidence on API structure
- DFS optimizer community patterns (training data, multiple sources) -- MEDIUM confidence on sequential ILP with exclusion approach; this is the standard pattern used by pydfs-lineup-optimizer and similar tools
- Project requirements from PROJECT.md -- HIGH confidence on domain constraints
