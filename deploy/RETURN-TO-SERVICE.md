# GB Golf Optimizer — Return-to-Service Runbook

Golf was taken **offseason on 2026-08-26**: `/golf` serves a static placeholder,
`gbgolf.service` is stopped and disabled, and the DataGolf projection cron is
paused. Gameblazers shut golf down for the NFL season (Owner ruling); it returns
**at the 2027 golf season restart**. This runbook is the exact reversal.

**Trigger to run this:** the 2027 golf season is starting and the Owner wants
golf live again.

**Scope discipline — read before touching anything on the VPS.** The
`gameblazers.silverreyes.net` nginx vhost is **shared**: `/golf` is this app,
`/nfl/` is **GBNFLOptimizer, a different live project**, and both sit under **one
shared Certbot certificate**. Only ever edit the `location /golf` block. Never
touch the `/nfl/` block, the `/.well-known` block, the TLS lines, or the port-80
server block. There is also a `gbnfloptimizer-db-1` container and a
`gbnfloptimizer_pgdata` volume **one character away** from golf's own
`gbgolfoptimizer-db-1` / `gbgolfoptimizer_pgdata` — verify the literal string
before any docker command.

VPS: `deploy@193.46.198.60`, app at `/opt/GBGolfOptimizer`. Deploy-user `sudo` is
password-required; the `sudo` steps below need an operator at the keyboard.

---

## Step 0 — Verify the DataGolf API key is still valid (do this FIRST)

The DataGolf Scratch Plus key is **paid yearly**. A lapsed renewal would present
at restart as a silent "0 players / fetch fails" outage. Catch it deliberately,
before re-enabling anything, by running one manual fetch against the live key:

```bash
ssh deploy@193.46.198.60
cd /opt/GBGolfOptimizer && FLASK_APP=gbgolf.web:create_app .venv/bin/flask fetch-projections
```

- **Expected:** `OK: {Tournament Name} | {N} players | fetch_id={N}` with N > 0.
- **If it fails with an auth/403/empty error:** the key has lapsed or rotated.
  Renew the DataGolf account subscription and update `DATAGOLF_API_KEY` in
  `/opt/GBGolfOptimizer/.env` (the operator edits `.env` directly on the VPS;
  it is `chmod 600`, git-ignored, and never synced by `deploy.sh`). Do **not**
  proceed until a manual fetch returns OK. Never paste the key value into a
  command, a log, a commit, or this repo — reference it by name only.

Also confirm the DataGolf account's renewal date in the DataGolf dashboard so the
next yearly lapse is anticipated, not discovered.

---

## Step 1 — Restore the `/golf` nginx block (proxy back to Gunicorn)

The offseason change replaced the `location /golf` block's proxy body with a
static placeholder. Restore it to the live-service form. Edit
`/etc/nginx/sites-enabled/gameblazers.silverreyes.net` and make the `/golf`
block exactly this (leave every other block byte-identical):

```nginx
    # GB Golf Optimizer at /golf
    # proxy_pass has NO trailing slash — full URI including /golf passes through to Gunicorn
    # SCRIPT_NAME=/golf in systemd env tells Flask/Werkzeug where the app is mounted
    location /golf {
        include proxy_params;
        proxy_pass http://unix:/opt/GBGolfOptimizer/gbgolf.sock;
        proxy_set_header X-Forwarded-Prefix /golf;
    }
```

Then validate and reload (this reloads the whole vhost, `/nfl/` included — so
`nginx -t` must pass first):

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Step 2 — Start and re-enable the app service

```bash
sudo systemctl enable --now gbgolf
sudo systemctl status gbgolf --no-pager
```

Confirm `active (running)` with a live Gunicorn master PID.

## Step 3 — Re-enable the projection cron

Un-comment the **three** golf `fetch-projections` lines in the deploy user's
crontab (the ones marked with the `OFFSEASON 2026-08-26` note). Leave the
NFL-odds, chalkbook, and GBNFLOptimizer-backup lines exactly as they are.

```bash
crontab -e   # remove the OFFSEASON comment markers from the 3 golf fetch lines
crontab -l   # verify the 3 golf lines are active and nothing else changed
```

The restored schedule (Tue/Wed fetch cadence): `0 14,16,18,20,22 * * 2,3`,
`0 0 * * 3,4`, `0 2 * * 3,4`, each running
`cd /opt/GBGolfOptimizer && FLASK_APP=gbgolf.web:create_app .venv/bin/flask fetch-projections >> logs/fetch.log 2>&1`.

## Step 4 — Resolve the contest-config decision (deferred by Owner ruling)

The Owner deferred the live contest-config choice to season restart. Production
serves whichever of `/opt/GBGolfOptimizer/contest_config.json.main` /
`.major` is copied to `contest_config.json` (the operator-swap mechanism; see
`tasks/todo.md`). Decide the season-opening contest and set it:

```bash
cd /opt/GBGolfOptimizer
cp contest_config.json.main contest_config.json   # or .major for a major week
```

(The `.major` config is the four-majors-week swap; `.main` is the standard slate.
Confirm the intended one with the Owner before copying.)

## Step 5 — Smoke-check

```bash
curl -s -o /dev/null -w "golf: HTTP %{http_code}\n" https://gameblazers.silverreyes.net/golf/
curl -s -o /dev/null -w "nfl:  HTTP %{http_code}\n" https://gameblazers.silverreyes.net/nfl/
tail -5 /opt/GBGolfOptimizer/logs/fetch.log
```

- `/golf` → 200 serving the real app (not the placeholder), `/nfl/` → still 200.
- The next scheduled fetch (or a manual one from Step 0) lands a fresh `fetch_id`.

## Step 6 — Records

- `GBGolfOptimizer_VPS_STATE.md` — Change Log entry: golf returned to service,
  date, cron re-enabled, contest config chosen.
- `/home/deploy/VPS_STATE.md` — note the nginx `/golf` and cron changes (shared
  resources).
- `tasks/todo.md` — close the offseason errand entry with the restart date.

---

## Notes on what was NOT changed at shutdown (so restart expects them unchanged)

- **TLS:** the shared Certbot cert renews automatically via the
  `snap.certbot.renew.timer`; it was untouched by the placeholder change and is
  not part of restart. (At offseason shutdown it had already auto-renewed to
  2026-11-20.)
- **Database:** `gbgolfoptimizer-db-1` was **left running** through the offseason
  (Owner decision) — its projection data is intact; no DB restore is needed at
  restart.
- **VPS git checkout:** deploys are file-copy (`deploy/deploy.sh`), not git;
  verify deployed code by `md5sum` against local HEAD, never by `git status` on
  the VPS.
