# Status

<!-- Machine-readable header under the status contract (ratified 2026-08-06,
     amended 2026-08-26). Seven keys, plain text, one contiguous block ending
     at the first blank line. Bump Updated: whenever any other value changes.
     Validate with: python3 /mnt/e/KnowledgeBase/AIKB/scripts/status_contract.py tasks/status.md --mode shape -->

- **Deployment:** retired
- **State:** parked
- **Line:** Golf offline for the NFL-season offseason; revisit Feb 2027 as the new season nears
- **Until:** 2027-02-01
- **Phase:** Offseason since 2026-08-26 — /golf is a static placeholder, app+cron stopped; M0 gameplan ratified 2026-08-04, unstarted
- **Next:** At the Feb 2027 revisit, bring golf back per deploy/RETURN-TO-SERVICE.md (verify DataGolf key, restore service, re-enable cron), then start the M0 gameplan.
- **Updated:** 2026-08-26

<!-- Everything below this line is archive: no value is ever taken from down
     here. Newest superseded block first. Archive bullets are intentionally
     indented so they are never read as column-0 keys (second-candidate-block
     trap). -->

## Archive

Superseded 2026-08-26 (pre-contract shape; migrated to the seven-key header above):

  - State: idle
  - Phase: v1.2.2 (duplicate-card-instance fix) shipped 2026-04-29 — confirmed
    still the live version today via direct site check (page heading shows
    v1.2.2; DataGolf cron fetch is current, "fetched today at 2:00 AM,"
    matching the documented Wed/Thu 02:00 UTC schedule). Post-release infra
    hardening followed: dedicated Postgres for GBGolf 2026-05-19,
    deploy-script pip-install fix 2026-05-19, TLS cert migration off an
    expired wildcard cert 2026-06-22. Admin Control Panel is PROPOSED
    (2026-05-20, DB-backed contest-config design decided) but has zero
    implementation.
  - Waiting on: nothing — unattended, not blocked. No product/infra commit
    since 2026-06-22 (31 days); no feature/fix work since 2026-05-19 (65
    days). Everything from 2026-07-22 onward is AIKB/Head-Coach vault-wiring
    housekeeping.
  - Until: n/a
  - Next action: Two VPS cleanup items in GBGolfOptimizer_VPS_STATE.md's Open
    Follow-ups (logged 2026-06-22, file untouched since — not re-verified
    against the live VPS, so treat as "last known state" (unverified)) are
    now overdue: (1) sync
    /etc/nginx/sites-available/gameblazers.silverreyes.net to the live
    sites-enabled copy, which still references a deleted cert lineage —
    routine, no sign-off needed; (2) decide on dropping the leftover gbgolf
    DB/role inside the retired gamepredictor-postgres-1 container, deferred
    as a fallback since 2026-05-20 ("give it a few days," now 2+ months
    overdue). That drop is destructive — bring it to Silver for sign-off per
    CLAUDE.md's rule before running it. If bigger scope is wanted instead,
    the Admin Control Panel already has its design decided and is unstarted.
  - Updated: 2026-07-23
