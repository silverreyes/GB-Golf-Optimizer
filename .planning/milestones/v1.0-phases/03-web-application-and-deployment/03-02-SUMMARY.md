---
phase: 03-web-application-and-deployment
plan: 02
subsystem: infra
tags: [systemd, gunicorn, nginx, deployment, vps]

requires:
  - phase: 03-web-application-and-deployment
    provides: Flask app with wsgi:app entry point and SCRIPT_NAME=/golf support

provides:
  - systemd service unit (deploy/gbgolf.service) for Gunicorn with 2 workers and unix socket
  - Nginx server block (deploy/gameblazers.silverreyes.net.nginx) proxying /golf to gbgolf.sock
  - Step-by-step deployment guide (deploy/DEPLOY.md) through smoke test

affects: []

tech-stack:
  added: []
  patterns:
    - "systemd + Gunicorn unix socket pattern for Flask WSGI deployment"
    - "Nginx location block with no trailing slash on proxy_pass preserves SCRIPT_NAME prefix"

key-files:
  created:
    - deploy/gbgolf.service
    - deploy/gameblazers.silverreyes.net.nginx
    - deploy/DEPLOY.md
  modified: []

key-decisions:
  - "SCRIPT_NAME=/golf set as systemd Environment variable — Flask/Werkzeug reads it to generate correct URLs under /golf prefix"
  - "proxy_pass has no trailing slash so full /golf URI passes intact to Gunicorn; X-Forwarded-Prefix header also set for belt-and-suspenders"
  - "2 workers chosen to match 2 vCPUs on Hostinger KVM 2 — avoids core contention on simultaneous requests with sync workers"
  - "Separate server_name block for gameblazers.silverreyes.net ensures zero interference with Open Claw on same Nginx instance"

patterns-established:
  - "Placeholder pattern: <deploy_user> and /path/to/GBGolfOptimizer as named placeholders for user substitution"

requirements-completed: [DEPL-01]

duration: 5min
completed: 2026-03-13
---

# Phase 3 Plan 02: VPS Deployment Configuration Summary

**systemd Gunicorn service + Nginx reverse proxy config + step-by-step deployment guide for gameblazers.silverreyes.net/golf on Hostinger KVM 2**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-13T00:00:00Z
- **Completed:** 2026-03-13
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- systemd unit file ready to copy to `/etc/systemd/system/` — starts Gunicorn bound to a unix socket with `SCRIPT_NAME=/golf` and 2 workers matching the 2 vCPUs
- Nginx server block ready to copy to `/etc/nginx/sites-available/` — proxies the `/golf` location to the unix socket without stripping the prefix, coexists with Open Claw
- Deployment guide walks through all 17 steps from SSH to smoke test, including conflict checks, Let's Encrypt setup, and service management quick reference

## Task Commits

Each task was committed atomically:

1. **Task 1: Create deployment configuration files** - `6b6969f` (chore)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `deploy/gbgolf.service` - systemd service unit for Gunicorn (2 workers, unix socket, SCRIPT_NAME=/golf)
- `deploy/gameblazers.silverreyes.net.nginx` - Nginx server block for subdomain with /golf location block
- `deploy/DEPLOY.md` - Step-by-step deployment guide with numbered steps through smoke test, DNS and SSL optional steps, Open Claw coexistence note, and service management quick reference

## Decisions Made

- `SCRIPT_NAME=/golf` set as systemd `Environment=` variable — Flask/Werkzeug reads this to generate correct absolute URLs when mounted at a path prefix
- `proxy_pass http://unix:/path/to/GBGolfOptimizer/gbgolf.sock;` has no trailing slash — this ensures the full `/golf/...` URI is forwarded intact to Gunicorn rather than the prefix being stripped
- `X-Forwarded-Prefix /golf` header added as belt-and-suspenders for any middleware that checks it
- 2 Gunicorn sync workers chosen to match the 2 vCPUs on the Hostinger KVM 2 — sync workers are appropriate since the optimizer is CPU-bound
- Separate `server_name gameblazers.silverreyes.net` block chosen over adding a `location` to an existing block — ensures zero interference with any Open Claw config

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**Manual VPS deployment required.** See [deploy/DEPLOY.md](../../../../deploy/DEPLOY.md) for complete instructions:

1. Replace `<deploy_user>` and `/path/to/GBGolfOptimizer` placeholders in both config files
2. Copy `deploy/gbgolf.service` to `/etc/systemd/system/` and enable/start the service
3. Copy `deploy/gameblazers.silverreyes.net.nginx` to `/etc/nginx/sites-available/` and enable the site
4. Verify with `sudo nginx -t && sudo systemctl reload nginx`
5. Smoke test: `curl -s -o /dev/null -w "%{http_code}" http://gameblazers.silverreyes.net/golf/`

## Next Phase Readiness

All deployment artifacts are complete. The project is fully ready for production deployment:

- Phase 1 (data foundation): complete
- Phase 2 (optimization engine): complete
- Phase 3 (web layer + deployment): complete

User can deploy by following `deploy/DEPLOY.md` on the Hostinger KVM 2 VPS.

---
*Phase: 03-web-application-and-deployment*
*Completed: 2026-03-13*
