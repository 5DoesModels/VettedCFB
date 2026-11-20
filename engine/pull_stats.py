# Pull season player stats (all FBS players) for participation / production measures.
# The API key is read from ~/cfbd_key.txt or the CFBD_KEY environment variable. Never commit it.
import json, os, sys, urllib.request

KEY = (os.environ.get('CFBD_KEY') or open(os.path.expanduser('~/cfbd_key.txt')).read()).strip()
OUT = os.path.expanduser('~/cfbd_pull')
for y in [int(a) for a in sys.argv[1:]] or range(2009, 2026):
    path = f'{OUT}/stats_{y}.json'
    if os.path.exists(path): continue
    req = urllib.request.Request(f'https://api.collegefootballdata.com/stats/player/season?year={y}',
                                 headers={'Authorization': f'Bearer {KEY}'})
    r = urllib.request.urlopen(req, timeout=120)
    rows = json.load(r)
    json.dump(rows, open(path, 'w'))
    print(y, len(rows), 'rows; calls left', r.headers.get('x-calllimit-remaining'))
