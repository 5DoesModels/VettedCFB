# Vetted CFB shared data foundation (Stage 0)

Build: **FND-0.1** · Status: **for review, not used anywhere on the site**

This folder holds the code that builds one shared, provenance-tagged set of player records for the future
Predictions page, Player Pathway, Transfer Ledger and other features.

## Rules this folder follows

- **One-way.** The foundation reads the official engine data and cached raw CFBD pulls. Nothing in the official
  pipeline (`model2.py`, `prep3.py`, `pred.py`, `link.py`, the site) reads from here.
- **Official grades unchanged.** Every build is followed by a fingerprint check of the official data files
  (`site/*.json`, `site/f/*.json`, engine `data/*.json`). FND-0.1: unchanged.
- **Provenance on every row.** `src` (where it came from), `st` (verified, derived, reported, experimental or unknown) and `bv` (build version).
- **Missing, zero and not applicable are different values.** For example, `games_position` is a number, `not_available`
  (no data for that season, or a defensive season before 2019), `not_applicable` (offensive linemen) or `unknown_position`.
- **Never guess.** When the evidence doesn't settle an identity or a transfer, the record is marked unresolved and listed in `exceptions.json`.

## Record types (7) and reference tables (2)

| Record | Key | Notes |
|---|---|---|
| Player | `pid` | One person. Joins recruiting records and roster athlete ids. `identity_status`: linked, linked_by_name_school, identity_unresolved, recruitment_only, roster_only |
| Recruitment | `recruit_id` | One recruiting record (high school, JUCO or prep). A player can have a high school and a JUCO/prep record, never two of the same kind |
| School stint | `pid` + school + first season | Consecutive roster seasons at one school. Roster listing only; it does not show games played |
| Transfer event | one per school movement or unmatched portal entry | Category: Confirmed, Reported, Inferred school movement, Unknown/unresolved (mutually exclusive) |
| Player-season | `pid` + season + school | Roster position and participation from game-by-game box scores (2009–2025) |
| Outcome | `pid` | drafted, still_in_college, no_linked_draft_record_through_2026, unknown. At most one draft outcome per player |
| Tag | scope + key | `player` tags (transferred, juco_route) or `player_school` tags keyed by player + school + position group (Great Fit: schema only, inactive) |
| School (reference) | name | CFBD names; schools outside roster coverage and possible alias pairs are listed, never merged automatically |
| Coach-season (reference) | coach + school + year | From CFBD coaches |

## Identity linking order

1. Roster recruit ids (CFBD), accepted when last names match and first names share an initial.
2. CFBD athlete id on the recruiting record.
3. Name + school + season window (flagged): signing school roster in the signing year or the next; a portal entry from the signing school whose destination roster has one player with that name; a portal entry joining a player's old and new athlete ids.

Roster ids are checked for collisions (different last names, gaps of 3+ seasons that roster coverage doesn't explain, careers longer than 7 seasons). Hometown, height and weight repeat on every roster row for an id, so they can't confirm identity.

## Files

- `build_foundation.py` builds everything into an output folder (not committed: about 230 MB).
- `pull_games.py` caches CFBD game-level player stats (`/games/players`), raw and unchanged, one file per season, season type and week.
- `reports/` holds the review material for JC: data-quality report, transfer reconciliation, 100-match spot check, 25 hand-checked players, participation recalculation, Great Fit report.
