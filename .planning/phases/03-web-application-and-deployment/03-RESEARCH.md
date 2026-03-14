# Phase 3: Web Application and Deployment - Research

**Researched:** 2026-03-13
**Domain:** Flask web layer, file upload handling, Jinja2 templating, Gunicorn/Nginx/systemd deployment
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Single-page app — upload form at top, results render below it on the same page
- After generating lineups, the upload form collapses with a small "Change files" toggle to reveal it again
- While optimization runs, a full-page loading overlay is shown
- Files persist in the form so user can change one file and re-run without re-uploading both
- Contests displayed as sequential sections: The Tips first, then The Intermediate Tee below
- Each lineup rendered as a table — one row per player, columns: Player | Collection | Salary | Multiplier | Proj Score
- Lineup totals appear both as a summary header above each lineup table AND as a footer row within the table
- If a lineup could not be built (infeasibility notice), show a clear message in its place
- Unmatched player report appears between the upload form and the lineup results
- Only shown when there are exclusions — hidden entirely on a clean run
- Format: simple list, one row per excluded card with the reason inline (e.g., "Ludvig Åberg — no projection found")
- Covers all three exclusion reasons: no projection found, $0 salary (not in field), expired card
- URL: `gameblazers.silverreyes.net/golf`
- Server setup: systemd service + Nginx reverse proxy
- The VPS already runs Open Claw — Nginx config must coexist with it (separate server block for the subdomain, no port conflicts)
- No existing website published at silverreyes.net to protect

### Claude's Discretion
- Flask vs FastAPI choice (both listed in project constraints; either works)
- HTML/CSS framework (vanilla or lightweight library — no heavy frontend framework needed)
- Gunicorn worker count and bind port
- Exact Nginx server block configuration
- Styling details (colors, fonts, spacing)

### Deferred Ideas (OUT OF SCOPE)
- NFL optimizer — future project on the same subdomain at `/nfl`
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DISP-01 | User can view all generated lineups in the browser, showing for each lineup: player name, collection, salary, multiplier, projected score, and lineup totals (total salary, total projected score) | Flask + Jinja2 template loops over `OptimizationResult.lineups`; `Lineup.cards` yields `Card` fields; `Lineup.total_salary` / `Lineup.total_projected_score` computed in `__post_init__` |
| DISP-02 | Lineups are clearly grouped by contest (The Tips vs The Intermediate Tee) | `OptimizationResult.lineups` is a `dict[contest_name, list[Lineup]]`; template iterates contests in fixed display order |
| DEPL-01 | App is deployed and accessible via the Hostinger KVM 2 VPS (silverreyes.net or subdomain) | systemd unit + Gunicorn + Nginx reverse proxy on separate subdomain server block; `SCRIPT_NAME=/golf` env var for path prefix |
</phase_requirements>

---

## Summary

Phase 3 wraps the already-complete optimization engine in a minimal Flask web layer, adds Jinja2 HTML templates for file upload and results display, and deploys the whole thing to a VPS behind Nginx. The scope is deliberately narrow — there is no database, no authentication, no async processing, and no JavaScript framework.

Flask is the correct choice over FastAPI here. The application is synchronous by nature (optimization is CPU-bound and completes in under a second for this data size), the templated HTML response pattern is Flask's native model, and Flask requires fewer moving parts for this level of complexity. FastAPI's strengths (async I/O, OpenAPI schema generation) add complexity without benefit.

The trickiest deployment concern is the `/golf` path prefix combined with a subdomain. The right pattern is `SCRIPT_NAME=/golf` in the systemd environment, Nginx keeping the prefix intact when proxying, and Flask's `url_for()` throughout templates. This avoids hardcoded path strings and ensures the app works correctly behind the reverse proxy without stripping logic.

**Primary recommendation:** Flask 3.x with Jinja2 templates, Gunicorn (unix socket), systemd service, and a dedicated Nginx server block for the `gameblazers.silverreyes.net` subdomain. Use `SCRIPT_NAME=/golf` for path prefix handling.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.x (>=3.0) | HTTP routing, request handling, Jinja2 integration | Synchronous WSGI; simplest path for template-rendered apps; no async overhead needed |
| Gunicorn | 23.x (>=20.0) | Production WSGI server | Standard Flask production server; unix socket binding avoids port conflicts |
| Werkzeug | (bundled with Flask) | `secure_filename`, `ProxyFix` middleware | Werkzeug's `secure_filename` is mandatory before writing uploaded files; `ProxyFix` required behind Nginx |
| Jinja2 | (bundled with Flask) | HTML templating | Flask's native template engine; already included |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | Not needed directly | Flask uses Werkzeug to parse multipart | Already handled by Flask/Werkzeug |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flask | FastAPI | FastAPI is async-first; no benefit here since optimization is sync/CPU-bound, and template rendering is not FastAPI's strength |
| Gunicorn unix socket | TCP port (e.g. 127.0.0.1:5000) | Either works; unix socket is slightly cleaner for same-machine proxy but port is simpler to debug |
| Vanilla CSS | Bootstrap / Pico CSS | Lightweight options fine but vanilla is zero-dependency |

**Installation:**
```bash
pip install flask gunicorn
```

Add to `pyproject.toml` under `[project].dependencies`:
```
"flask>=3.0",
"gunicorn>=20.0",
```

---

## Architecture Patterns

### Recommended Project Structure
```
gbgolf/
├── web/
│   ├── __init__.py         # create_app() factory, registers blueprint
│   ├── routes.py           # upload + optimize route handler
│   ├── templates/
│   │   └── index.html      # single-page template
│   └── static/
│       └── style.css       # minimal styling
wsgi.py                     # entry point for Gunicorn: from gbgolf.web import create_app; app = create_app()
```

The `web/` subpackage sits alongside the existing `data/` and `optimizer/` packages inside `gbgolf/`. The `wsgi.py` at project root is the Gunicorn entry point.

### Pattern 1: Application Factory

**What:** `create_app()` function in `gbgolf/web/__init__.py` constructs and returns the Flask app. Loads `contest_config.json` once at startup and stashes it on `app.config`.

**When to use:** Always — even for simple apps, the factory pattern enables testing with different config and avoids circular import issues.

```python
# Source: https://flask.palletsprojects.com/en/stable/patterns/appfactories/
import json, os
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from gbgolf.data import load_config

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Required when running behind Nginx reverse proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "contest_config.json")
    app.config["CONTESTS"] = load_config(os.path.abspath(config_path))
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

    from gbgolf.web.routes import bp
    app.register_blueprint(bp)

    return app
```

### Pattern 2: Upload Route with Temp Files

**What:** Single POST route receives two file inputs, writes them to temp files, calls `validate_pipeline`, then `optimize`, renders results template.

**When to use:** Always for CSV upload handling — temp files allow passing file paths to the data layer without modifying it.

**Critical note on `validate_pipeline` signature:** The actual public API is:
```
validate_pipeline(roster_path: str, projections_path: str, config_path: str) -> ValidationResult
```
The CONTEXT.md mentions passing `contests` as the third argument, but the real `gbgolf/data/__init__.py` expects a `config_path` string and loads config internally. The web layer should pass the config file path, not a pre-loaded list.

```python
# Source: https://flask.palletsprojects.com/en/stable/patterns/fileuploads/
import os, tempfile
from flask import Blueprint, render_template, request, current_app
from werkzeug.utils import secure_filename
from gbgolf.data import validate_pipeline
from gbgolf.optimizer import optimize

bp = Blueprint("main", __name__)

@bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    roster_file = request.files.get("roster")
    projections_file = request.files.get("projections")

    # Write uploads to named temp files (delete=False required on Windows;
    # manually unlink in finally block)
    roster_tmp = projections_tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", mode="wb"
        ) as rf:
            roster_file.save(rf)
            roster_tmp = rf.name

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", mode="wb"
        ) as pf:
            projections_file.save(pf)
            projections_tmp = pf.name

        config_path = current_app.config["CONFIG_PATH"]
        validation = validate_pipeline(roster_tmp, projections_tmp, config_path)
        result = optimize(validation.valid_cards, current_app.config["CONTESTS"])

        return render_template(
            "index.html",
            validation=validation,
            result=result,
            show_results=True,
        )
    except ValueError as e:
        return render_template("index.html", error=str(e))
    finally:
        for path in [roster_tmp, projections_tmp]:
            if path and os.path.exists(path):
                os.unlink(path)
```

**Windows note:** `NamedTemporaryFile` on Windows holds an exclusive lock while open, so the file cannot be read by another process while the context manager is active. The pattern above writes the upload into the temp file directly via `file.save(rf)`, then closes it (exiting the `with` block) before passing the path to `validate_pipeline`. This avoids the Windows file-locking issue.

### Pattern 3: Jinja2 Results Template

**What:** Single `index.html` renders the upload form, conditional exclusion report, and lineup results in one page.

```jinja2
{# Source: Flask Jinja2 docs https://flask.palletsprojects.com/en/stable/templating/ #}

{# Upload form — collapsed after results available #}
<details {% if not show_results %}open{% endif %} id="upload-section">
  <summary>{% if show_results %}Change files{% else %}Upload files{% endif %}</summary>
  <form method="post" enctype="multipart/form-data">
    <label>Roster CSV: <input type="file" name="roster" accept=".csv" required></label>
    <label>Projections CSV: <input type="file" name="projections" accept=".csv" required></label>
    <button type="submit">Generate Lineups</button>
  </form>
</details>

{# Loading overlay — shown while form submits via CSS/JS toggle #}
<div id="loading-overlay" style="display:none;">Optimizing...</div>

{# Exclusion report — only if there are exclusions #}
{% if validation and validation.excluded %}
<section id="exclusion-report">
  <h2>Unmatched Players</h2>
  <ul>
    {% for excl in validation.excluded %}
      <li>{{ excl.player }} — {{ excl.reason }}</li>
    {% endfor %}
  </ul>
</section>
{% endif %}

{# Lineup results — grouped by contest #}
{% set contest_order = ["The Tips", "The Intermediate Tee"] %}
{% for contest_name in contest_order %}
  {% set lineups = result.lineups.get(contest_name, []) %}
  <section>
    <h2>{{ contest_name }}</h2>
    {% for lineup in lineups %}
      <h3>Lineup {{ loop.index }} — Salary: ${{ lineup.total_salary | int }} | Proj: {{ "%.2f"|format(lineup.total_projected_score) }}</h3>
      <table>
        <thead><tr><th>Player</th><th>Collection</th><th>Salary</th><th>Multiplier</th><th>Proj Score</th></tr></thead>
        <tbody>
          {% for card in lineup.cards %}
          <tr>
            <td>{{ card.player }}</td>
            <td>{{ card.collection }}</td>
            <td>${{ card.salary }}</td>
            <td>{{ card.multiplier }}</td>
            <td>{{ "%.2f"|format(card.projected_score or 0) }}</td>
          </tr>
          {% endfor %}
        </tbody>
        <tfoot>
          <tr><td colspan="2"><strong>Totals</strong></td>
              <td><strong>${{ lineup.total_salary }}</strong></td>
              <td></td>
              <td><strong>{{ "%.2f"|format(lineup.total_projected_score) }}</strong></td></tr>
        </tfoot>
      </table>
    {% else %}
      <p class="infeasible">No lineup could be built for this contest.</p>
    {% endfor %}
    {# Infeasibility notices for this contest #}
    {% for notice in result.infeasibility_notices %}
      {% if contest_name in notice %}
        <p class="infeasible">{{ notice }}</p>
      {% endif %}
    {% endfor %}
  </section>
{% endfor %}
```

### Pattern 4: Loading Overlay via HTML/JS

**What:** A minimal JavaScript snippet on form submit shows the loading overlay. No framework needed.

```html
<script>
  document.querySelector("form").addEventListener("submit", function() {
    document.getElementById("loading-overlay").style.display = "flex";
  });
</script>
```

### Anti-Patterns to Avoid
- **Async view functions:** Do not make the upload handler `async def`. The core optimizer uses PuLP's CBC solver synchronously; mixing sync and async in Flask adds complexity with no benefit.
- **Storing uploads in a permanent folder:** Use temp files and delete them in a `finally` block. Do not keep CSV files on disk after the request completes — the app has no user isolation and CSVs may contain private data.
- **Stripping `/golf` prefix at Nginx:** If Nginx strips the prefix before proxying, `url_for()` generates broken internal links missing the prefix. Set `SCRIPT_NAME=/golf` in the systemd environment and let Flask/Werkzeug handle it instead.
- **Hardcoding `/golf` in templates:** Always use `url_for()` for internal links. Hardcoded paths break if the prefix ever changes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sanitizing uploaded filenames | Custom filename cleaning | `werkzeug.utils.secure_filename` | Prevents directory traversal (`../../etc/passwd` → safe name) |
| Proxy header trust | Manual header parsing | `werkzeug.middleware.proxy_fix.ProxyFix` | Flask's official pattern; handles X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Prefix correctly |
| WSGI production server | `flask run` in production | Gunicorn | Flask dev server is single-threaded, not signal-safe, not suitable for production |

**Key insight:** All non-trivial web infrastructure concerns (filename safety, proxy headers, WSGI serving) are already solved by Flask/Werkzeug/Gunicorn. The only custom code needed is the route handler and template.

---

## Common Pitfalls

### Pitfall 1: Windows NamedTemporaryFile File Lock
**What goes wrong:** `NamedTemporaryFile` on Windows holds an exclusive lock while the context manager is open. Passing the `.name` path to `validate_pipeline` while still inside the `with` block causes a `PermissionError` because the CSV reader tries to open a file that the temp file handle still owns.
**Why it happens:** Windows file locking semantics differ from Unix — on Unix you can open the same file multiple times; on Windows you cannot.
**How to avoid:** Write the upload into the temp file using `file.save(rf)` inside the `with` block, let the block close the file, then pass `rf.name` to `validate_pipeline` outside the block. Use `delete=False` and manually `os.unlink()` in a `finally` block.
**Warning signs:** `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`

### Pitfall 2: ProxyFix Missing — URL Generation Broken Behind Nginx
**What goes wrong:** Without `ProxyFix`, Flask sees `http://127.0.0.1` as the request origin (the Gunicorn-facing address), not `https://gameblazers.silverreyes.net`. `url_for()` generates `http://127.0.0.1/golf/...` links, and `request.url` is wrong.
**Why it happens:** Nginx proxies requests and sets `X-Forwarded-*` headers, but Flask doesn't trust them by default.
**How to avoid:** Wrap the app with `ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)` in `create_app()`.
**Warning signs:** Links in the page point to `127.0.0.1` or `http://` when the site is served over `https://`.

### Pitfall 3: SCRIPT_NAME Not Set — /golf Prefix Lost
**What goes wrong:** Without `SCRIPT_NAME=/golf`, Flask routes to `/` but the browser requests `/golf/` — Nginx proxies it correctly but Flask sees `/golf` as part of the path rather than the mount prefix, causing 404s.
**Why it happens:** Flask needs to know its mount prefix to strip it from incoming paths and prepend it to outgoing `url_for()` calls.
**How to avoid:** Set `Environment="SCRIPT_NAME=/golf"` in the systemd service `[Service]` section. Gunicorn reads this env var and sets it in the WSGI environ.
**Warning signs:** The app returns 404 for all routes when accessed via `/golf/`.

### Pitfall 4: Port Conflict With Open Claw
**What goes wrong:** If Gunicorn is bound to the same TCP port as the existing Open Claw application, the service fails to start.
**Why it happens:** Two processes cannot bind the same port.
**How to avoid:** Use a unix socket (`--bind unix:/path/to/gbgolf.sock`) or choose a port not used by Open Claw. Verify available ports with `ss -tlnp` on the VPS before choosing.
**Warning signs:** `OSError: [Errno 98] Address already in use` in Gunicorn logs.

### Pitfall 5: MAX_CONTENT_LENGTH Not Set
**What goes wrong:** A user accidentally uploads a large file (e.g., multi-MB Excel export), Flask holds the entire request in memory.
**Why it happens:** Flask accepts any content length by default.
**How to avoid:** Set `app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024` (5 MB is far more than any expected CSV). Flask raises `RequestEntityTooLarge` on excess; catch it and show a user-friendly message.

---

## Code Examples

### systemd Service File
```ini
# /etc/systemd/system/gbgolf.service
[Unit]
Description=GB Golf Optimizer (Gunicorn)
After=network.target

[Service]
User=<deploy_user>
Group=www-data
WorkingDirectory=/path/to/GBGolfOptimizer
Environment="PATH=/path/to/venv/bin"
Environment="SCRIPT_NAME=/golf"
ExecStart=/path/to/venv/bin/gunicorn \
    --workers 2 \
    --bind unix:/path/to/GBGolfOptimizer/gbgolf.sock \
    -m 007 \
    wsgi:app

[Install]
WantedBy=multi-user.target
```

### Nginx Server Block (subdomain + path prefix)
```nginx
# /etc/nginx/sites-available/gameblazers.silverreyes.net
server {
    listen 80;
    server_name gameblazers.silverreyes.net;

    # /golf proxied to gbgolf Gunicorn; prefix kept intact (no trailing slash after port)
    location /golf {
        include proxy_params;
        proxy_pass http://unix:/path/to/GBGolfOptimizer/gbgolf.sock;
        proxy_set_header X-Forwarded-Prefix /golf;
    }

    # Future: /nfl location block added here when NFL optimizer is built
}
```

Enable with: `sudo ln -s /etc/nginx/sites-available/gameblazers.silverreyes.net /etc/nginx/sites-enabled/`

**Why no trailing slash on proxy_pass:** When `proxy_pass` has no URI component after the address (no trailing slash), Nginx passes the full request URI including `/golf` to Gunicorn unchanged. Gunicorn reads `SCRIPT_NAME=/golf`, strips it, and Flask routes the remainder correctly.

### Gunicorn Worker Count Rationale
The Hostinger KVM 2 has 2 vCPUs. Flask docs recommend `CPU * 2` workers → 4 workers. However, since optimization is CPU-bound (PuLP/CBC), use **2 workers** to avoid contention — a single optimization request will saturate one core, so having 4 workers risks two simultaneous requests competing for the same 2 cores. For a low-traffic personal tool, 2 sync workers is correct.

### wsgi.py Entry Point
```python
# wsgi.py — at project root, beside pyproject.toml
from gbgolf.web import create_app

app = create_app()
```

Gunicorn invocation: `gunicorn wsgi:app`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `flask.escape()` | Jinja2 auto-escaping (always on by default) | Flask 2.0+ | No action needed; Jinja2 escapes all `{{ }}` output automatically |
| `flask.request.form.get()` for file checks | `request.files.get()` with presence check | Flask 1.x+ | Files are always in `request.files`, not `request.form` |
| Custom temp file cleanup | `tempfile.NamedTemporaryFile(delete=False)` + `finally: os.unlink()` | Python 3.12 added `delete_on_close`; but `delete=False` + manual unlink is still the most portable pattern | Portable across Python 3.10+ (project minimum) |

**Deprecated/outdated:**
- `flask.helpers.send_file` for CSV download: Not needed in this phase (no download feature), but relevant for v2 USBL-04.
- Running `flask run` in production: Replaced by Gunicorn for production deployments.

---

## Open Questions

1. **Open Claw port/socket assignment on the VPS**
   - What we know: Open Claw is already running; Nginx must not conflict.
   - What's unclear: What port or socket does Open Claw use? Is there an existing Nginx config to inspect?
   - Recommendation: Before writing Nginx config on the VPS, run `sudo nginx -T` and `ss -tlnp` to document current bindings. Choose a unix socket for gbgolf to avoid all port conflicts.

2. **VPS operating system and Python version**
   - What we know: Hostinger KVM 2; project requires Python >=3.10.
   - What's unclear: Whether Python 3.10+ is pre-installed or needs to be set up with pyenv/deadsnakes.
   - Recommendation: Deployment task should include a step to verify `python3 --version` and install if needed.

3. **HTTPS/SSL setup**
   - What we know: No existing website at silverreyes.net to protect; user didn't mention SSL.
   - What's unclear: Whether SSL is required for the subdomain at deployment time.
   - Recommendation: Plan for HTTP-only first (port 80); note that adding Let's Encrypt/Certbot is a straightforward follow-up step if needed.

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
| DISP-01 | Upload form POST returns HTML containing lineup table with player name, collection, salary, multiplier, proj score columns | integration | `pytest tests/test_web.py::test_lineup_table_columns -x` | ❌ Wave 0 |
| DISP-01 | Lineup footer row shows total salary and total projected score | integration | `pytest tests/test_web.py::test_lineup_totals_row -x` | ❌ Wave 0 |
| DISP-02 | Response HTML contains "The Tips" section before "The Intermediate Tee" section | integration | `pytest tests/test_web.py::test_contest_sections_order -x` | ❌ Wave 0 |
| DISP-02 | Each lineup is rendered under its correct contest heading | integration | `pytest tests/test_web.py::test_lineups_grouped_by_contest -x` | ❌ Wave 0 |
| DISP-01 | Infeasibility notice renders in place of lineup table when optimizer cannot build lineup | integration | `pytest tests/test_web.py::test_infeasibility_notice_rendered -x` | ❌ Wave 0 |
| DISP-01 | Exclusion report is hidden when there are no exclusions | integration | `pytest tests/test_web.py::test_exclusion_report_hidden_on_clean_run -x` | ❌ Wave 0 |
| DISP-01 | Exclusion report shows player name and reason for each excluded card | integration | `pytest tests/test_web.py::test_exclusion_report_content -x` | ❌ Wave 0 |
| DEPL-01 | Smoke test: GET `/golf/` returns HTTP 200 (manual verification on live server) | smoke/manual | Manual: `curl https://gameblazers.silverreyes.net/golf/` | manual-only |

### Flask Test Client Pattern
```python
# tests/test_web.py — Wave 0 setup
import io, pytest
from gbgolf.web import create_app

@pytest.fixture
def client(tmp_path):
    # Write minimal valid CSVs so the pipeline succeeds
    roster = tmp_path / "roster.csv"
    projections = tmp_path / "proj.csv"
    roster.write_text(SAMPLE_ROSTER_CSV, encoding="utf-8")
    projections.write_text(SAMPLE_PROJECTIONS_CSV, encoding="utf-8")

    app = create_app()
    app.config["TESTING"] = True
    # Point config to real contest_config.json at project root
    with app.test_client() as client:
        yield client, roster, projections
```

Flask's built-in `test_client()` allows POST requests with `content_type="multipart/form-data"` and `data={"roster": (io.BytesIO(b"..."), "roster.csv"), "projections": (io.BytesIO(b"..."), "proj.csv")}`. No real HTTP server needed.

### Sampling Rate
- **Per task commit:** `pytest tests/test_web.py -x -q`
- **Per wave merge:** `pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_web.py` — all DISP-01, DISP-02 integration tests
- [ ] Flask + test client: add `flask>=3.0` to `[project.optional-dependencies].dev` if not already present (it is not — only pytest is listed currently)

---

## Sources

### Primary (HIGH confidence)
- Flask 3.1.x official docs — file uploads pattern, application factory, Nginx deployment, Gunicorn deployment, templating
  - https://flask.palletsprojects.com/en/stable/patterns/fileuploads/
  - https://flask.palletsprojects.com/en/stable/patterns/appfactories/
  - https://flask.palletsprojects.com/en/stable/deploying/nginx/
  - https://flask.palletsprojects.com/en/stable/deploying/gunicorn/
- Project source code — `gbgolf/data/__init__.py`, `gbgolf/optimizer/__init__.py`, `gbgolf/data/models.py` — verified actual API signatures

### Secondary (MEDIUM confidence)
- DigitalOcean — Flask + Gunicorn + Nginx + systemd configuration guide (Ubuntu 22.04): https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04
- Little Umbrellas — Flask WSGI URL prefix with SCRIPT_NAME: https://dlukes.github.io/flask-wsgi-url-prefix.html
- Nginx proxy_pass trailing slash behavior: https://www.getpagespeed.com/server-setup/nginx/nginx-proxy-pass-trailing-slash

### Tertiary (LOW confidence)
- Python tempfile Windows locking: https://github.com/python/cpython/issues/58451 — documents the Windows exclusive-lock behavior; mitigated by the `delete=False` + close-before-read pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Flask/Gunicorn/Nginx verified against official docs and project constraints
- Architecture: HIGH — patterns from official Flask docs; API signatures verified against actual project source
- Pitfalls: HIGH (Windows temp file, ProxyFix, SCRIPT_NAME) / MEDIUM (Open Claw port conflict — requires VPS inspection)
- Deployment config: MEDIUM — based on well-established DigitalOcean guide; exact paths depend on VPS filesystem layout

**Research date:** 2026-03-13
**Valid until:** 2026-06-13 (stable ecosystem — Flask 3.x, Nginx, systemd are not fast-moving)

---

### API Signature Correction Notice

The CONTEXT.md states: `gbgolf.data.validate_pipeline(roster_path, projections_path, contests)` where `contests` is described as a pre-loaded list.

**The actual signature is:**
```python
validate_pipeline(roster_path: str, projections_path: str, config_path: str) -> ValidationResult
```

The third argument is a **file path string to `contest_config.json`**, not a pre-loaded list. The function loads the config internally. The web layer should store and pass the config file path, not call `load_config()` separately and pass the result to `validate_pipeline`. Store `CONFIG_PATH` in `app.config`, not a pre-loaded `CONTESTS` list, and pass it to `validate_pipeline`. A separate `load_config(config_path)` call is still needed to give `optimize()` its `contests` argument (since `validate_pipeline` returns a `ValidationResult` without exposing the parsed `ContestConfig` list).
