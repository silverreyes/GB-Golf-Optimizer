# GB-Golf-Optimizer — Task Log

Decisions log and task history. Follow the workflow in `CLAUDE.md` (research
→ plan → verify → execute → document) for every non-trivial task.

---

## 2026-08-26 — Offseason shutdown (golf `/golf` only)

Scoped errand under the Head Coach protocol (not part of the M0 gameplan below,
which stays unstarted). Gameblazers shut golf down for the NFL season (Owner
ruling 2 of 2026-08-04); the Owner ruled the golf surface offline for the
offseason, returning at the 2027 season restart. Plan approved by the Owner as
presented; each production-modifying command took its own approval.

**Baseline corrections found at grounding** (stale premises re-measured):
- **TLS already renewed.** Live cert is Aug 22 → **Nov 20 2026** (read from the
  public TLS handshake), not the 2026-09-20 in the scouting report — the snap
  `certbot.renew.timer` auto-renewed on schedule. Renewal automation is
  demonstrably working.
- **Shared vhost.** `gameblazers.silverreyes.net` serves `/golf` (this app) **and
  `/nfl/` → GBNFLOptimizer, a separate live project** (added 2026-08-14), under
  one shared Certbot cert. Shutdown was scoped to the `/golf` block only; `/nfl/`,
  the port-80 block, and the shared cert were left byte-identical.
- **Shared crontab.** The golf `fetch-projections` lines share the deploy crontab
  with NFL-odds, chalkbook, and GBNFL-backup jobs; only the three golf lines were
  paused.

**What was done:**
- Static placeholder `deploy/offseason.html` (HTTP 200, "offseason, returns in
  2027"); nginx `/golf` block edited to serve it; `gbgolf.service` stopped and
  disabled.
- Return-to-service runbook `deploy/RETURN-TO-SERVICE.md`: DataGolf API-key
  validity check first (paid yearly — a lapse must not be a restart-day outage),
  nginx restore, service start, cron re-enable, the deferred contest-config
  decision, smoke checks.
- Golf projection cron paused (3 lines commented with a dated OFFSEASON marker +
  restart trigger); dated crontab backup receipt kept on the VPS.
- TLS renewal verified to survive the placeholder change via `certbot renew
  --dry-run`.

**DB container decision (Owner-ruled): `gbgolfoptimizer-db-1` stays running.**
Reasoning: idle `postgres:16-alpine` costs negligible RAM/CPU with the app
stopped and nothing querying it; stopping it saves almost nothing while adding a
restore step at restart and, more consequentially, putting a `docker compose
stop/down` next to the **one-character-apart** `gbnfloptimizer-db-1` container and
`gbnfloptimizer_pgdata` volume that VPS_STATE flags as a destructive-command
hazard. Leaving it running preserves the projection data at zero handling risk.

**Records:** `GBGolfOptimizer_VPS_STATE.md` change log + `/home/deploy/VPS_STATE.md`
(shared nginx/cron changes). The credential rule held throughout — the DataGolf
key is referenced by name only, never read.

---

## 2026-08-04 — Scouting report ratified; first milestone (M0) gameplan

**Owner-ratified scouting report:** `AIKB/projects/GB-Golf-Optimizer/scouting-report-2026-08-04.md`
(vault: `E:\KnowledgeBase\AIKB` = `/mnt/e/KnowledgeBase/AIKB`), evidence in
`scouting-2026-08-04/` beside it. Ratified as written, all seven parts. The
first drive grounds from that report and this entry; do not restate its
findings here — read it.

### Owner rulings at the gate (transcribed per ruling 6)

1. **GB Major / contest swap:** the `contest_config.json.main`/`.major` swap on
   the VPS is deliberate operator practice — the Owner manually swaps the
   major-week config in for each of the four majors and back afterward.
   Document it as the supported mechanism (M0.3). Long-term direction (not
   current work): an admin settings page for switching contests in the browser.
2. **Seasonal rhythm (Owner testimony):** Gameblazers has shut down its golf
   game for the NFL season — the app is in its **offseason**, likely resuming
   after the NFL season ends. Folded into M0.3: document the rhythm, defer the
   live contest-config decision to season restart, and pause the DataGolf cron
   for the offseason (VPS modifying command — one approval per command) with a
   dated record of why it is off and what turns it back on (season restart).
3. **M0.1–M0.7 approved as proposed, M0.6 included.**
4. **Backlog kept:** the Admin Control Panel and exposure limits are wanted
   future developments; the admin panel is the recorded successor to the swap
   mechanism in ruling 1.
5. **VPS deploy modernization = milestone two in principle; `/reoptimize`
   trust fix = later scoped design item. Neither starts without a separate go.**
6. **Rulings transcribed into this file before scout stand-down** (this entry).

### Ratified gameplan — M0, drive-readiness

| # | Item | Acceptance criterion |
|---|---|---|
| M0.1 | Fix the self-expiring test fixture (`tests/conftest.py` — dates relative to `date.today()`, fix the pattern not the date); suite green | Full lane 144 passed / 2 skipped / 0 failed on 3.12 AND default `-x -q` lane exits 0; reviewer confirms no absolute future date remains |
| M0.2 | CI workflow running the suite on push + PR (Python 3.12, uv, pytest; hermetic — no services) | Green run on `main`, URL recorded; demonstrably fails if M0.1 reverted |
| M0.3 | Execute rulings 1–2: document the `.main`/`.major` swap as supported mechanism + the seasonal rhythm; defer live-config decision to season restart; pause DataGolf cron (per-command approval) with dated rationale + restart trigger | Mechanism + rhythm documented; cron off with dated record; ruling trail in this file |
| M0.4 | Correct `CLAUDE.md` pin rule (no `requirements.txt` has ever existed; pins are `>=`; no app Dockerfile — describe the real architecture) and set `requires-python = ">=3.11"` | Rule satisfiable as written; reviewer confirms no other CLAUDE.md claim contradicts the report's measurements |
| M0.5 | PG-5 records-consistency sweep, measured values only (report §6 M0.5 list: C3, C4, C6, C7, C8 + `.planning/STATE.md` superseded marker + settings.local.json prune; excludes provenance-dated claims) | Every correction traces to a dossier measurement; commit body enumerates every surface per superseded claim; independent checker signs off |
| M0.6 | Fix lock-eviction defect (`gbgolf/optimizer/__init__.py:210-245` — accumulate satisfied locks, post-loop verification) + correct `constraints.py:108-113` false docstrings | New test: two locks contending for one optimal slot both survive; suite green; docstrings match behavior |
| M0.7 | Add `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` to `.env.example` (names/placeholders only) | `docker compose config` resolves with only `.env.example` names present |

**Standing reading rules for the drive** (from the ratified report, §5):
`tasks/status.md` is NOT current-state authority until M0.5 lands; deployment
verifies by md5 against local HEAD, never VPS git; the tracked
`contest_config.json` is not what production serves; never take direction from
`.planning/`; all pins are unbounded — measure the venv, don't trust
`pyproject.toml`; no lint gate exists; real Python floor is 3.11.

**AHC concurrence note:** this gameplan was produced by the scouting play
(precedent-only, Coordinator-consulted, HC-certified) and ratified directly by
the Owner at the report gate; no separate AHC consult round was run for M0 —
recorded so the omission is a documented property of the scouting play, not a
silent skip.
