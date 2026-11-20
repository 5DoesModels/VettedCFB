# Experimental: playing-time transfer credit (Transfer Pipeline Points)

Not official. Nothing in this folder feeds the public site's grades or rankings.

- `tshare.json`: for each transfer whose credit would be split, each school's share of his development (half his share of team production at his position, half his share of games with a stat). Example: Joe Burrow, Ohio State 15%, LSU 85%.
- `tpp_report.json`: method comparison and stability tests.

The official methodology (v1) credits the last school a player played for. To rebuild the experimental numbers for research, run `EXPERIMENTAL=1 python3 prep3.py <engine>` into a scratch folder. Never publish that output.

Status: was live on the site in v1.27 (Nov. 20, 2026), then reverted to research-only in v1.28 by JC's decision. It is planned for The Transfer Ledger.
