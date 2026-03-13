# GB Golf Optimizer

## What This Is

A web application for optimizing GameBlazers fantasy golf lineups. Users upload their weekly roster export (CSV from GameBlazers), the app applies the current week's projections, and generates optimal lineups for each available contest — prioritizing the cash contest first, then using remaining cards for non-cash contests.

## Core Value

Generate the best possible cash contest lineups from the user's available player cards, maximizing expected score within salary and collection constraints.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can upload their GameBlazers roster CSV export
- [ ] Admin can upload/replace weekly projections CSV (player name + projected fantasy score)
- [ ] App generates 3 optimal lineups for The Tips (cash contest) — 6 golfers each
- [ ] App generates 2 optimal lineups for The Intermediate Tee (non-cash) using cards not used in Tips lineups
- [ ] Each card is locked to one lineup — no card appears in more than one lineup across all contests
- [ ] Optimizer respects salary cap constraints (min and max) per contest
- [ ] Optimizer respects collection constraints (Weekly/Core limits) per contest
- [ ] Effective card value calculated as projected_score × multiplier
- [ ] Lineups displayed clearly in the browser with player, salary, multiplier, and projected value
- [ ] Contest configuration (salary caps, roster sizes, collection limits) stored in an editable config file
- [ ] App deployed to Hostinger KVM 2 VPS (silverreyes.net or subdomain)

### Out of Scope

- Scraping GameBlazers for contest data — manual config file update instead (contests change infrequently)
- Automatic projection fetching — user manually averages projections from sites like DataGolf, FantasyNational, etc.
- User accounts / authentication — single shared app, no login required
- Mobile-native app — web app accessible from any browser
- RUC (Recycling Useless Cards) optimization — out of scope for v1

## Context

- **GameBlazers** (gameblazers.com) is a fantasy golf platform where users collect player cards with salaries and multipliers (1.0–1.5). Each week, users enter contests by building lineups from their card collection.
- **Roster export**: GameBlazers provides a CSV export with columns: Player, Positions, Team, Multiplier, Overall, Franchise, Rookie, Tradeable, Salary, Collection, Status, Expires.
- **Overall column**: Used by GameBlazers for the RUC card-burning system only — irrelevant to lineup optimization.
- **Franchise / Rookie columns**: Boolean flags only — not collection types, no optimizer constraints needed.
- **Salary $0 cards**: Indicate player is not in the tournament field this week — must be excluded from optimization.
- **Duplicate player cards**: The same player can appear multiple times with different multipliers and salaries — each card is a distinct optimizer variable. However, a golfer may only appear once per lineup regardless of how many cards are owned.
- **Two current contests**:
  - **The Tips** (cash): 6 golfers, salary $30,000–$64,000, max 3 Weekly Collection cards, max 6 Core cards, 3 entries
  - **The Intermediate Tee** (non-cash, pack/credit prizes): 5 golfers, salary $20,000–$52,000, max 2 Weekly Collection cards, max 5 Core cards, 2 entries
- **Scoring system** (same for both contests): Points for eagles (+8), birdies (+4), pars (-0.5), bogeys (-1), double bogeys (-3), double eagle or better (+15), birdie streaks (+3), bogey-free round (+2), hole-in-one (+5), plus finish position bonuses (1st = +30 pts, scaling down).
- **Projections**: User averages projections from multiple DFS golf sites (e.g. DataGolf, FantasyNational) and uploads a simple CSV each week. Projections represent expected fantasy points for that week's tournament.
- **Hosting**: Hostinger KVM 2 VPS — full Linux server, supports Python/Node.js.

## Constraints

- **Tech Stack**: Python backend (Flask or FastAPI) + HTML/CSS/JS frontend — Python has strong constraint-solving libraries (PuLP, OR-Tools)
- **Hosting**: Hostinger KVM 2 VPS at silverreyes.net — deployment must work on Linux VPS
- **Data input**: No scraping — all inputs are file uploads (roster CSV, projections CSV) or manual config
- **Card locking**: Each card may only appear in exactly one lineup across all contests in a session

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Manual projections upload (CSV) | Simpler than scraping; user averages multiple sources themselves | — Pending |
| Contest config as editable file | Contests change infrequently; scraping is fragile and complex | — Pending |
| Python backend for optimization | PuLP/OR-Tools handle ILP (integer linear programming) constraints cleanly | — Pending |
| Cash contest optimized first | Maximize prize money; non-cash lineups use leftover cards | — Pending |
| Cards locked per lineup | GameBlazers rule — same card cannot appear in multiple lineup entries | — Pending |
| One golfer per lineup | GameBlazers rule — same golfer may only appear once per lineup regardless of how many cards owned | — Pending |
| Franchise/Rookie are flags only | Confirmed with user — not collection types, no ILP constraints needed | ✓ Good |

---
*Last updated: 2026-03-13 after clarifications*
