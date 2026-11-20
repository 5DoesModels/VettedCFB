# Pull committed recruits for future classes (2027+) from the College Football Data API.
# The API key is read from ~/cfbd_key.txt or the CFBD_KEY environment variable. Never commit it.
import json, os, sys, urllib.request

KEY = (os.environ.get('CFBD_KEY') or open(os.path.expanduser('~/cfbd_key.txt')).read()).strip()
OUT = os.path.expanduser('~/cfbd_pull')
os.makedirs(OUT, exist_ok=True)

for year in [int(y) for y in sys.argv[1:]] or [2027, 2028, 2029]:
    req = urllib.request.Request(
        f'https://api.collegefootballdata.com/recruiting/players?year={year}&classification=HighSchool',
        headers={'Authorization': f'Bearer {KEY}'})
    rows = json.load(urllib.request.urlopen(req, timeout=60))
    json.dump(rows, open(f'{OUT}/r{year}.json', 'w'))
    print(year, len(rows), 'recruits,', sum(1 for r in rows if r.get('committedTo')), 'committed')
