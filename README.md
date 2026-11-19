# Vetted CFB

Who really develops college football players: every signee since 2008, graded against what players like him usually do.

- `site/` is the website (served by a Cloudflare Worker; see `wrangler.jsonc`). Hidden from search engines for now.
- `engine/` holds the scripts that pull data from the College Football Data API and build the files in `site/`. Raw data and API keys are never committed.
