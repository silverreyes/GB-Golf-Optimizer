# Status

<!-- ═══════════════════════════════════════════════════════════════════════════
     MACHINE-READABLE HEADER — THIS IS AN INTERFACE, NOT PROSE. DO NOT REFORMAT.
     Written under the status contract (FrontOffice/tasks/proposal-status-contract.md,
     RATIFIED and amended 2026-08-06). The contract is the record of law; this crib
     paraphrases it and the contract governs on any difference. Seat duties live in
     AIKB/global/head-coach.md "Status upkeep".

     THE SHAPE (§4, §4.1)
       Seven keys, each exactly ONCE, each value on ONE line, plain text, in
       `- **Key:** value` form starting at column 0. They form ONE CONTIGUOUS BLOCK
       that starts at the first column-0 key line naming one of the seven and runs
       to the next blank line OR END OF FILE — a file whose header is the last thing
       in it is legal.
       Every non-blank line inside that block must itself be a well-formed key line
       naming one of the seven. A stray comment, prose line, or plain bullet wedged
       BETWEEN two key lines is a violation.
       Key ORDER is not law. The order below is convention; the key-set is the rule.

       Every example key line in this comment is INDENTED ON PURPOSE. There is NO
       comment exemption (§4.1, measured as F-12): a column-0 key line naming one of
       the seven IS selected as the header even inside an HTML comment. Protection
       above the header is positional only — indent, or be selected. Keep it that way.

     THE SEVEN KEYS
       - **Deployment:**  live | pre-deploy | retired
       - **State:**  in-drive | stalled-owner | stalled-agent | between-drives | soaking | parked | idle
       - **Line:**  the glance line, <= 90 chars — see the table below
       - **Until:**  `YYYY-MM-DD HH:MM` or `YYYY-MM-DD` local, or `n/a`; MANDATORY iff soaking/parked, `n/a` otherwise
       - **Phase:**  one line, free text — where the project is in its life; markup-free, soft cap ~120 chars (§4.2)
       - **Next:**  the next few acts only — short plain lines read at a glance; markup-free; soft cap ~240 chars / <=3 acts (§4.2, revised 2026-08-26 PM)
       - **Updated:**  bare `YYYY-MM-DD`, nothing else

     WHAT THE LINE MUST NAME, PER STATE (§5.1) — required, and judged, not regexed
       | State           | The Line must name                                        |
       | in-drive        | what the drive is building right now                      |
       | stalled-owner   | THE SPECIFIC ACT OWED — a ruling on X, a kickoff for Y,    |
       |                 | a desk act. "Waiting on owner" alone is a violation,       |
       |                 | not a description.                                        |
       | stalled-agent   | what's grinding and what clears it                        |
       | between-drives  | what the next drive would be if played                    |
       | soaking         | what's soaking AND the at-zero act                        |
       | parked          | the wake trigger — the external event behind the machine  |
       |                 | date                                                      |
       | idle            | what finished, and what — if anything — would EVER wake it |

     AUTHOR'S CHECKLIST — the write-time judgment point (§5.1, §5.2, §5.3 F-5 rider).
     The validator cannot judge 1–3; you must. Before you commit:
       1. CONTENT — does the Line name what the table above requires for your state?
       2. PLAIN WORDS — would the Owner understand it cold, two weeks away, without
          opening anything? No codenames, ticket shorthand, or milestone labels
          standing alone.
            FAILS:  "Silver's decision on the S2B hold"  — "S2B hold" means nothing.
            FAILS:  "Next drive would be M1"             — "M1" names a label, not a drive.
            PASSES: "hold on 134 unscored predictions (S2-B)" — codename ALONGSIDE
                    its plain meaning, which is the only way a codename may appear.
          Don't spend the 90 chars restating the tag: `between-drives` already says
          nothing is wrong, so "nothing is blocked" is wasted budget.
       3. WHOSE BALL — does the State tag honestly say whose ball it is? "Needs the
          Owner to re-dispatch" is stalled-owner, not stalled-agent (§3.1).
       4. IDLE IS A CLAIM — never carry `idle` over from a previous file. Re-derive
          it: no drive open, none contemplated, no wake event (§3.3).
       5. BUMP `Updated:` — every time any of the seven values changes. The whole
          staleness system runs off this one field, and it is the easiest to forget.
       6. PARKED? Declare the EARLIEST PLAUSIBLE wake date (§6.2). "late August"
          becomes the earliest date it could plausibly be — the board must wake you
          no later than reality could — and the Line carries the approximation and
          the event.
       7. `Phase:` / `Next:` READ COLD (§4.2, brevity amendment 2026-08-26,
          `Next:` bound revised the same afternoon). Both are DRILL-DOWN prose and
          carry a readability discipline:
            - PLAIN TEXT, no markdown — no `**bold**`, `` `backticks` ``, heading
              `#`, or list bullets. The validator soft-flags these as an ADVISORY
              (not a violation); the sweep reports them as findings. Re-compose in
              plain words.
            - `Phase:` — soft cap ~120 chars on the stripped value (a sweep nudge,
              never a render-time violation). One line, still.
            - `Next:` — the NEXT FEW ACTS ONLY, short plain lines read at a glance;
              soft cap ~240 chars on the stripped value / <=3 acts (re-measurable,
              a sweep nudge, never a render-time violation). NOT a running narrative
              or an archive of context — anything past the next few acts goes in
              your own records, not the board. Composed to read cold; an over-long,
              unreadable, or jargon-laden `Next:` is a sweep finding, same class as
              a bad `Line:`. [Owner 2026-08-26 PM, superseding the morning "in full,
              any length": *"The next field can get ridiculously long… I'm not going
              to read all that."*]

     TRAPS THAT HAVE ALREADY BITTEN
       - BELOW the header, a bold bullet naming one of the seven keys starts a SECOND
         CANDIDATE BLOCK — a violation. Detection is not extraction: no value is ever
         TAKEN from below the header, but the whole file IS scanned to find these
         (§4.1). Nothing goes below the header block. Superseded headers are not
         kept; git history is the history.
         Worse today: the deployed renderer reads the whole file LAST-MATCH-WINS, so
         such a bullet does not merely violate, it SILENTLY REPLACES your declared
         value on the board. Its legacy keymap makes `State:`, `Phase:`, `Until:` and
         `Updated:` the four names live to this right now; `Deployment:`, `Line:` and
         `Next:` are inert until the §11.1 cutover.
       - Do NOT leave a value empty. An empty `Line:` is a violation; an empty value
         on any other key is a violation; and under that same legacy renderer an empty
         value SWALLOWS THE NEXT LINE and the swallowed key vanishes from the board.
       - `Until:` never legally empties. Its rest state is the literal `n/a`.
     ═══════════════════════════════════════════════════════════════════════════ -->

- **Deployment:** retired
- **State:** parked
- **Line:** Golf offline for the NFL-season offseason; revisit Feb 2027 as the new season nears
- **Until:** 2027-02-01
- **Phase:** Offseason since 2026-08-26 — /golf is a static placeholder, app+cron stopped; M0 gameplan ratified 2026-08-04, unstarted
- **Next:** At the Feb 2027 revisit, bring golf back per deploy/RETURN-TO-SERVICE.md (verify DataGolf key, restore service, re-enable cron), then start the M0 gameplan.
- **Updated:** 2026-09-04
