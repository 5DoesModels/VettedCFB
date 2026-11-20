# Pull game box scores and aggregate, per player and school season: games with a recorded stat, plus
# usage counts (pass attempts, carries, catches, tackles...). The API key is read from ~/cfbd_key.txt or
# CFBD_KEY. Never commit it. Output: ~/cfbd_pull/box_YYYY.json  {"athleteId|team": [name, team, games, {stat: total}]}
import json, os, sys, time, urllib.request, collections

KEY = (os.environ.get('CFBD_KEY') or open(os.path.expanduser('~/cfbd_key.txt')).read()).strip()
OUT = os.path.expanduser('~/cfbd_pull')
KEEP = {('passing', 'C/ATT'), ('rushing', 'CAR'), ('receiving', 'REC'), ('defensive', 'TOT'), ('defensive', 'SACKS'), ('defensive', 'PD'),
        ('interceptions', 'INT'), ('kicking', 'FG'), ('punting', 'NO'), ('kickReturns', 'NO'), ('puntReturns', 'NO')}
def get(y, w, st):
    req = urllib.request.Request(f'https://api.collegefootballdata.com/games/players?year={y}&week={w}&seasonType={st}', headers={'Authorization': f'Bearer {KEY}'})
    for _ in range(3):
        try:
            r = urllib.request.urlopen(req, timeout=180); return json.load(r), r.headers.get('x-calllimit-remaining')
        except Exception as e:
            err = e; time.sleep(3)
    raise err
for y in [int(a) for a in sys.argv[1:]] or range(2009, 2026):
    path = f'{OUT}/box_{y}.json'
    if os.path.exists(path): continue
    agg = {}; left = None
    for st, weeks in (('regular', range(1, 17)), ('postseason', (1,))):
        for w in weeks:
            games, left = get(y, w, st)
            for g in games:
                for t in g['teams']:
                    seen = set()
                    for c in t['categories']:
                        for ty in c['types']:
                            for a in ty['athletes']:
                                k = f"{a['id']}|{t['team']}"
                                x = agg.setdefault(k, [a['name'], t['team'], 0, {}])
                                if (g['id'], k) not in seen: seen.add((g['id'], k)); x[2] += 1
                                if (c['name'], ty['name']) in KEEP:
                                    s = a['stat']
                                    try: v = float(s.split('/')[1]) if '/' in s else float(s)
                                    except: v = 0
                                    key = c['name'] + ':' + ty['name']; x[3][key] = x[3].get(key, 0) + v
    json.dump(agg, open(path, 'w'), separators=(',', ':'))
    print(y, len(agg), 'player-seasons; calls left', left, flush=True)
