# Vetted CFB

**Who really develops college football players?** Vetted CFB compares every FBS signee's NFL Draft outcome with what players of similar recruiting ratings and positions typically achieve, then grades programs and head coaches on the gap.

- **Website (preview, hidden from search engines):** https://vettedcfb.5models.workers.dev
- **Data range:** recruiting classes 2002–2026 (graded 2002–2023), NFL Drafts 2003–2026, transfer portal 2021–2026
- **Methodology:** version 1 (last-school credit), data refreshed Nov. 19, 2026. Full explanation on the site's Methods page.

## What the numbers measure

Vetted CFB compares players' NFL Draft outcomes with expectations based on their original recruiting profiles and positions. The results show how a program's players performed relative to those expectations. They do not isolate the causal contribution of an individual school, coach or staff member.

## Repository layout

- `site/` – the website: one `index.html` plus JSON data files. Served as static assets by a Cloudflare Worker (`wrangler.jsonc`). Pushing to `main` rebuilds the site.
- `engine/` – Python scripts that pull data from the College Football Data API and build the files in `site/`:
  - `model2.py` – expected and actual draft points for every signee (class-adjusted expected draft points)
  - `prep3.py` – rankings, grades, report cards and most site data
  - `pred.py`, `nfl.py`, `roster.py`, `rising.py` – predictions, NFL careers, roster studies, G5 Coaches to Watch
  - `pull_*.py` – data pulls (need a CFBD API key in `~/cfbd_key.txt` or `CFBD_KEY`; keys are never committed)
  - `setaside.json` – players left out of grading (careers cut short); `flips_2027.json` – manual 2027 commitment fixes

Raw data files and API keys are not committed.

## Data sources

College Football Data API (recruiting, draft, rosters, portal, coaches, stats); nflverse / Pro Football Reference (NFL careers). Recruiting ratings are the 247Sports Composite as provided by the API.
