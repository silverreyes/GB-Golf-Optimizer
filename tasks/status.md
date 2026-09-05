# Status

<!-- MACHINE-READABLE HEADER — AN INTERFACE, NOT PROSE. DO NOT REFORMAT.
     Law: the status contract (FrontOffice/tasks/proposal-status-contract.md);
     this crib paraphrases it and the contract governs on any difference.
     Seat duties: AIKB/global/head-coach.md "Status upkeep".

     SHAPE — seven keys, each exactly once, one per line, plain text,
     `- **Key:** value` at column 0, in ONE contiguous block: nothing wedged
     between the key lines, nothing below the block, no superseded copies
     kept anywhere — git history is the history. Key order is convention,
     not law. A column-0 key line is selected as the header EVEN INSIDE A
     COMMENT, so every example in this crib stays indented.

     KEYS
       - **Deployment:** live | pre-deploy | retired
       - **State:** in-drive | stalled-owner | stalled-agent | between-drives | soaking | parked | idle
       - **Line:** the glance line, <=90 chars — content per state, below
       - **Until:** local date [HH:MM] — mandatory iff soaking/parked, else
         the literal n/a; never empty
       - **Phase:** where the project is in its life — one line, ~120 chars,
         no markup
       - **Next:** the next few acts only — <=3 acts, ~240 chars, no markup,
         never a narrative or an archive of context
       - **Updated:** bare YYYY-MM-DD — bump whenever any value changes

     WHAT THE LINE NAMES, PER STATE (judged, not regexed):
       in-drive: what the drive is building right now
       stalled-owner: THE SPECIFIC ACT OWED — never just "waiting on owner"
       stalled-agent: what's grinding and what clears it
       between-drives: what the next drive would be if played
       soaking: what's soaking AND the at-zero act
       parked: the wake trigger behind the date (earliest plausible date)
       idle: what finished, and what if anything would ever wake it

     WRITE-TIME CHECKLIST (the validator cannot judge these; you must):
     plain words that read cold — a codename appears only beside its plain
     meaning; the State tag honestly says whose ball it is; idle is
     re-derived at every visit, never carried forward; Updated bumped.

     TRAPS, ALL MEASURED: a bold column-0 bullet naming a key BELOW the
     header starts a second candidate block, and the deployed renderer reads
     last-match-wins — it silently REPLACES your declared value on the
     board. An empty value is a violation and can swallow the next line.
-->

- **Deployment:** retired
- **State:** parked
- **Line:** Golf offline for the NFL-season offseason; revisit Feb 2027 as the new season nears
- **Until:** 2027-02-01
- **Phase:** Offseason since 2026-08-26 — /golf is a static placeholder, app+cron stopped; M0 gameplan ratified 2026-08-04, unstarted
- **Next:** At the Feb 2027 revisit, bring golf back per deploy/RETURN-TO-SERVICE.md (verify DataGolf key, restore service, re-enable cron), then start the M0 gameplan.
- **Updated:** 2026-09-04
