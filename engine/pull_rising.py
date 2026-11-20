# Pull current-season team records and team recruiting class rankings for the "Next big hire" list.
# The API key is read from ~/cfbd_key.txt or the CFBD_KEY environment variable. Never commit it.
import json, os, urllib.request

KEY = (os.environ.get('CFBD_KEY') or open(os.path.expanduser('~/cfbd_key.txt')).read()).strip()
OUT = os.path.expanduser('~/cfbd_pull')
os.makedirs(OUT, exist_ok=True)

def get(path):
    req = urllib.request.Request('https://api.collegefootballdata.com' + path, headers={'Authorization': f'Bearer {KEY}'})
    r = urllib.request.urlopen(req, timeout=60)
    print(path, 'calls left:', r.headers.get('x-calllimit-remaining'))
    return json.load(r)

json.dump(get('/records?year=2026'), open(f'{OUT}/records_2026.json', 'w'))
json.dump(get('/teams/fbs?year=2026'), open(f'{OUT}/fbs_2026.json', 'w'))
# team recruiting rankings for every class 2015-2027 in one call each is many calls; the endpoint takes a year, so pull only what we need
tr = {}
for y in range(2016, 2028):
    tr[y] = get(f'/recruiting/teams?year={y}')
json.dump(tr, open(f'{OUT}/team_rec.json', 'w'))
