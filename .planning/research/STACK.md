# Technology Stack

**Project:** GB Golf Optimizer
**Researched:** 2026-03-13
**Confidence note:** WebSearch and WebFetch were unavailable during research. Versions and recommendations are based on training data (cutoff May 2025). All libraries recommended here are mature and stable -- unlikely to have breaking changes, but exact latest versions should be confirmed via `pip index versions <package>` before installing.

## Recommended Stack

### Runtime
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | Backend language | Required for PuLP/optimization; 3.12 is stable and widely deployed. Avoid 3.13 unless confirmed stable on target VPS. |

### Web Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | ~0.115+ | HTTP API + file upload handling | Async by default, built-in file upload via `UploadFile`, automatic OpenAPI docs, type validation with Pydantic. For this project's scope Flask would also work, but FastAPI's `UploadFile` handling and automatic request validation reduce boilerplate. |
| Uvicorn | ~0.30+ | ASGI server | Standard production server for FastAPI. Use `--workers 2` on KVM 2 (2 vCPU). |
| Jinja2 | ~3.1+ | HTML templating | FastAPI supports Jinja2 templates natively. Renders server-side HTML -- no need for a JS framework for this app's complexity level. |
| python-multipart | ~0.0.9+ | Form/file parsing | Required by FastAPI for file upload endpoints. Often missed during install. |

### Optimizer (ILP Solver)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PuLP | ~2.8+ | ILP model definition + solver interface | **Primary recommendation.** See detailed rationale below. |
| CBC (via PuLP) | bundled | ILP solver engine | Ships with PuLP -- zero extra install. Handles this problem size (< 500 variables) in milliseconds. |

### Data Processing
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pandas | ~2.2+ | CSV parsing, data manipulation | Standard for CSV ingestion. `read_csv()` handles encoding edge cases, column type inference. Overkill for simple CSV reads but worth it for the data manipulation needed (filtering $0 salary cards, calculating effective values, grouping by collection). |

### Frontend
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| HTML + Jinja2 templates | -- | Page rendering | Server-side rendering is correct for this app. No SPA needed -- it is a form-submit-and-display-results workflow. |
| Tailwind CSS (via CDN) | 3.x | Styling | Clean utility-first CSS without build tooling. CDN play script (`<script src="https://cdn.tailwindcss.com">`) is fine for a single-user tool -- no build step required. |
| Vanilla JavaScript | ES6+ | File upload UX, minor interactivity | Minimal JS for drag-and-drop upload, loading spinners, and maybe tab switching between contest results. No framework needed. |

### Deployment
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| systemd | -- | Process management | Native on Hostinger KVM 2 (Ubuntu/Debian). Manages Uvicorn as a service with auto-restart. |
| Nginx | -- | Reverse proxy + static files | Terminates HTTPS (via Certbot/Let's Encrypt), proxies to Uvicorn on localhost:8000. |
| Certbot | -- | TLS certificates | Free HTTPS for silverreyes.net subdomain. |
| venv | -- | Python isolation | Standard `python -m venv` -- no Docker needed for this scope. |

### Dev Tooling
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | ~8.x | Testing | Standard Python test runner. Critical for testing optimizer constraint logic. |
| ruff | ~0.5+ | Linting + formatting | Single tool replaces flake8 + black + isort. Fast, opinionated. |
| pip-tools | ~7.x | Dependency pinning | `pip-compile` generates pinned `requirements.txt` from `requirements.in`. Reproducible deploys. |

---

## Optimizer Library: Detailed Comparison

This is the most consequential stack decision. The app's core value is ILP optimization.

### Recommendation: PuLP (with bundled CBC solver)

**PuLP wins because:**
1. **Zero-config solver**: CBC ships inside the PuLP package. `pip install pulp` and you have a working ILP solver. No system-level dependencies, no separate binary installs.
2. **Readable model code**: PuLP's API maps directly to mathematical ILP notation. Variables, constraints, and objective functions read like the math they represent.
3. **Problem size match**: This problem has ~200-500 binary decision variables (one per card-slot combination) and ~20-50 constraints. CBC solves this in <100ms. Industrial-grade solvers are unnecessary.
4. **DFS optimizer precedent**: PuLP is the de facto library for DFS lineup optimizers in the Python community. Numerous open-source DFS optimizers use PuLP+CBC.
5. **Lightweight**: ~15MB installed. No C++ build dependencies.

### Why NOT Google OR-Tools

| Factor | PuLP | OR-Tools |
|--------|------|----------|
| Install size | ~15 MB | ~200+ MB |
| Install complexity | `pip install pulp` | Large binary wheels; platform-specific issues common |
| API complexity | Simple, Pythonic | Verbose, Java-ported API style |
| Solver included | Yes (CBC bundled) | Yes (SCIP, GLOP, CP-SAT) |
| Problem fit | Perfect for this size | Designed for much larger/harder problems |
| VPS friendliness | Excellent | Heavy -- eats RAM on a 8GB KVM 2 |

OR-Tools is the right choice when you need CP-SAT (constraint programming), vehicle routing, or problems with 100K+ variables. For a DFS optimizer with < 500 variables, it is massive overkill. The API is also harder to read and maintain.

### Why NOT scipy.optimize.linprog / milp

`scipy.optimize.milp` (added in scipy 1.9) supports mixed-integer linear programming, but:
- The API is matrix-based (pass coefficient arrays), not symbolic. Building constraints as numpy arrays is error-prone and hard to debug compared to PuLP's `lpSum(x[i] for i in players) <= 6`.
- No warm-start or solver tuning.
- scipy is 50+ MB for one function you could get from PuLP at 15 MB.

### Why NOT Gurobi / CPLEX

Commercial solvers. Free academic licenses exist but add licensing complexity for zero benefit at this problem size. CBC matches their performance for problems under 10K variables.

---

## Architecture Decision: Server-Side Rendering (NOT SPA)

**Use Jinja2 templates served by FastAPI. Do NOT build a React/Vue/Svelte frontend.**

Rationale:
- The app is a **form submission workflow**: upload CSV, click optimize, view results. This is exactly what server-rendered HTML handles well.
- No real-time updates, no complex client state, no offline mode needed.
- Single-user tool with no auth -- no JWT/session complexity.
- Eliminates: Node.js, npm, a build pipeline, CORS configuration, API serialization layer, and a separate deployment artifact.
- Jinja2 + Tailwind CSS produces clean, responsive pages with zero JavaScript build tooling.

The small amount of JS needed (file drag-and-drop, loading indicator) is handled with vanilla JS in a `<script>` tag.

---

## Deployment Architecture: Hostinger KVM 2

**Hostinger KVM 2 specs**: 2 vCPU, 8 GB RAM, 100 GB NVMe, Ubuntu-based.

### Deployment Approach

```
Internet --> Nginx (port 443/80) --> Uvicorn (localhost:8000) --> FastAPI app
```

1. **Nginx** handles TLS termination, static files (CSS/JS), and reverse proxy.
2. **Uvicorn** runs the FastAPI app with 2 workers (matches vCPU count).
3. **systemd** manages the Uvicorn process (auto-restart on crash, start on boot).
4. **No Docker** -- unnecessary for a single Python app on a dedicated VPS. Direct venv deployment is simpler and uses less RAM.
5. **No database** -- CSV uploads are processed in-memory; no persistence needed beyond the uploaded files (which can live in a `/data/` directory on disk).

### File Storage

Uploaded CSVs are small (< 1 MB). Store in a simple directory structure:
```
/opt/gbgolf/data/
  roster/current.csv       # Latest uploaded roster
  projections/current.csv  # Latest uploaded projections
  config/contests.json     # Contest configuration
```

No database. No S3. Files on disk, overwritten each upload.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Framework | FastAPI | Flask | Flask works fine but lacks built-in type validation, async, and auto-docs. FastAPI's `UploadFile` is cleaner than Flask's `request.files`. |
| Framework | FastAPI | Django | Massive overkill. ORM, admin, auth, migrations -- none needed here. |
| Optimizer | PuLP (CBC) | OR-Tools | 10x heavier install, verbose API, overkill for < 500 variables. |
| Optimizer | PuLP (CBC) | scipy.milp | Matrix-based API is hard to read/debug vs PuLP's symbolic constraints. |
| Frontend | Jinja2 + Tailwind | React/Vue SPA | No complex client state; SSR eliminates entire JS build pipeline. |
| Frontend | Tailwind CSS CDN | Bootstrap | Tailwind produces cleaner, more custom designs. CDN play script avoids build tools. |
| Deployment | systemd + Nginx | Docker | Adds complexity for zero benefit on a single-app VPS. |
| Deployment | venv | conda | conda is heavier and unnecessary when all deps are pip-installable. |
| Data | pandas | csv stdlib | pandas handles edge cases (encoding, type coercion) and enables easy data manipulation for the optimizer input prep. |
| Data | File on disk | SQLite/PostgreSQL | No relational queries needed. Current roster + current projections is the entire data model. |

---

## Installation

```bash
# Create project and venv
mkdir -p /opt/gbgolf && cd /opt/gbgolf
python3.12 -m venv venv
source venv/bin/activate

# Core dependencies
pip install fastapi uvicorn[standard] python-multipart jinja2 pulp pandas

# Dev dependencies
pip install -D pytest ruff pip-tools

# Pin dependencies
pip freeze > requirements.txt
```

### requirements.in (for pip-tools)
```
fastapi
uvicorn[standard]
python-multipart
jinja2
pulp
pandas
```

### Key Versions (verify before install)
| Package | Expected Version Range | Notes |
|---------|----------------------|-------|
| fastapi | 0.110 - 0.115+ | Stable API since 0.100+ |
| uvicorn | 0.27 - 0.30+ | Standard extras include watchfiles for dev reload |
| pulp | 2.7 - 2.9+ | CBC solver bundled since 2.0 |
| pandas | 2.1 - 2.2+ | pyarrow backend optional but not needed |
| jinja2 | 3.1+ | Stable for years |
| python-multipart | 0.0.6 - 0.0.9+ | Required for FastAPI file uploads |

---

## What NOT to Install

| Package | Why Not |
|---------|---------|
| SQLAlchemy / any ORM | No database needed |
| celery / any task queue | Optimization runs in < 1 second; no async job processing needed |
| redis | No caching layer needed for single-user tool |
| docker | Direct venv deployment is simpler on dedicated VPS |
| node / npm | No JS build pipeline; Tailwind via CDN |
| pydantic-settings | Overkill; contest config is a simple JSON file loaded at startup |
| gunicorn | Uvicorn handles both dev and production; gunicorn adds no value for 2 workers |

---

## Sources

- PuLP documentation: https://coin-or.github.io/pulp/ (MEDIUM confidence -- training data, not live-verified)
- FastAPI documentation: https://fastapi.tiangolo.com/ (MEDIUM confidence -- training data, not live-verified)
- OR-Tools documentation: https://developers.google.com/optimization (MEDIUM confidence -- training data)
- General DFS optimizer patterns: Community knowledge from training data (LOW confidence on specific version numbers)

**Version confidence: MEDIUM** -- All libraries recommended are mature and stable. Exact latest versions should be confirmed via PyPI before installing, but the APIs and capabilities described are accurate as of the training cutoff.
