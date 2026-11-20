# "Next big hire": Group of Five head coaches who win, recruit above their school's level and develop.
# Builds the list for the current season (2026) and backtests the same formula at the end of 2021-2025.
import json, sys, math, collections
E = sys.argv[1]; O = '/home/claude/concept/'; CP = '/root/cfbd_pull/'
C = json.load(open(E + '/data/coaches.json'))
REC26 = {r['team']: r for r in json.load(open(CP + 'records_2026.json')) if r.get('classification') == 'fbs'}
TR = json.load(open(CP + 'team_rec.json'))
D = json.load(open(O + 'data.json'))
G = {c['name']: c for c in D['coaches']}

P4 = {'SEC', 'Big Ten', 'Big 12', 'ACC'}
def power(conf, year, school):
    if school == 'Notre Dame': return True
    return conf in P4 or (conf == 'Pac-12' and year <= 2023)

# seasons: (school, year) -> [coach, wins, games, conf]; 2026 from the live records
S = {}
for c in C:
    nm = f"{c['firstName']} {c['lastName']}"
    for s in c['seasons']:
        g = s['games'] or 0
        key = (s['school'], s['year'])
        if s['year'] == 2026:
            r = REC26.get(s['school'])
            if not r: continue
            w, g = r['total']['wins'], r['total']['games']
            if key not in S or S[key][2] < 1: S[key] = [nm, w, g, r['conference'], r['expectedWins']]
        elif g > (S.get(key, [None, 0, -1])[2]):
            S[key] = [nm, s['wins'] or 0, g, s.get('conference'), None]
BY = collections.defaultdict(list)            # coach -> [(year, school, w, g, conf, xw)]
for (sch, y), (nm, w, g, cf, xw) in S.items(): BY[nm].append((y, sch, w, g, cf, xw))
for v in BY.values(): v.sort()

# class rank by school/year (CFBD team rankings 2016-2026; 2027 ranked from current commits)
RK = {(t['team'], int(y)): t['rank'] for y, L in TR.items() for t in L}
c27 = collections.defaultdict(list)
for x in json.load(open(CP + 'r2027.json')):
    if x.get('committedTo') and x.get('rating'): c27[x['committedTo']].append(x['rating'])
FL = {f['name']: f for f in json.load(open(E + '/flips_2027.json'))['flips']}
pts = {s: sum((r * 100 - 70) * math.exp(-((i / 14) ** 2)) for i, r in enumerate(sorted(v, reverse=True))) for s, v in c27.items()}
for i, s in enumerate(sorted(pts, key=lambda s: -pts[s])): RK[(s, 2027)] = i + 1

def pctl(vals):
    xs = sorted(v for v in vals if v is not None)
    return lambda v: 50 if v is None else 100 * (sum(1 for x in xs if x < v) + 0.5 * sum(1 for x in xs if x == v)) / len(xs)

def board(Y):
    """Coaches leading a non-power FBS program in season Y, scored at the end of season Y."""
    rows = []
    for nm, ss in BY.items():
        cur = [s for s in ss if s[0] == Y and s[3] > 0]
        if not cur: continue
        y, sch, w, g, cf, xw = cur[0]
        if power(cf, Y, sch): continue
        recent = [s for s in ss if Y - 2 <= s[0] <= Y and s[3] > 0]
        rg = sum(s[3] for s in recent); rw = sum(s[2] for s in recent)
        if rg < 18: continue                      # needs about a season and a half as an FBS head coach
        here = [s for s in ss if s[1] == sch and s[3] > 0 and s[0] <= Y]
        start = min(s[0] for s in here)
        before = [S[(sch, yy)] for yy in range(start - 3, start) if (sch, yy) in S and S[(sch, yy)][2] > 0]
        hw = sum(s[2] for s in here) / sum(s[3] for s in here)
        bw = sum(b[1] for b in before) / sum(b[2] for b in before) if before else None
        mine = [RK.get((sch, yy)) for yy in range(start, Y + 2)]   # classes he signed (signing day falls before his first season)
        mine = [m for m in mine if m]
        prior = [RK.get((sch, yy)) for yy in range(start - 3, start)]
        prior = [p for p in prior if p]
        lift = (sum(prior) / len(prior) - sum(mine) / len(mine)) if mine and prior else None
        dev = G[nm]['g']['dev'][1] if nm in G and G[nm]['g'].get('dev') else None
        rows.append(dict(name=nm, school=sch, conf=cf, yrs=len(here), w=sum(s[2] for s in here), l=sum(s[3] - s[2] for s in here),
                         rw=rw, rl=rg - rw, wp=rw / rg, turn=None if bw is None else hw - bw, before=bw,
                         rank=round(sum(mine) / len(mine)) if mine else None, prior=round(sum(prior) / len(prior)) if prior else None,
                         lift=lift, dev=dev, p4=any(power(s[4], s[0], s[1]) for s in ss if s[0] < start and s[3] > 0), sa=sch in ('Army','Navy','Air Force'), xw=None if xw is None else w - xw, last=mine[-1] if mine else None))
    pw, pt, pl, px = pctl([r['wp'] for r in rows]), pctl([r['turn'] for r in rows]), pctl([r['lift'] for r in rows]), pctl([r['xw'] for r in rows])
    for r in rows:
        parts = dict(win=pw(r['wp']), turn=pt(r['turn']), rec=pl(r['lift']), dev=50 if r['dev'] is None else r['dev'])
        r['parts'] = {k: round(v) for k, v in parts.items()}
        r['score'] = round(.40 * parts['win'] + .20 * parts['turn'] + .30 * parts['rec'] + .10 * parts['dev'], 1)
    rows.sort(key=lambda r: -r['score'])
    return rows

def moved_up(nm, Y):
    nxt = [s for s in BY.get(nm, []) if s[0] == Y + 1]
    cur = [s for s in BY.get(nm, []) if s[0] == Y]
    return bool(nxt) and bool(cur) and nxt[0][1] != cur[0][1] and power(nxt[0][4], Y + 1, nxt[0][1]), (nxt[0][1] if nxt else None)

bt = []
for Y in range(2021, 2026):
    b = board(Y); top = b[:10]
    hits = [(r['name'], r['school'], moved_up(r['name'], Y)[1]) for r in top if moved_up(r['name'], Y)[0]]
    allmoves = sum(1 for r in b if moved_up(r['name'], Y)[0])
    bt.append(dict(y=Y, n=len(b), top=len(top), hits=len(hits), moves=allmoves, names=hits))
    print(Y, 'pool', len(b), 'top10 hired up', len(hits), 'of', allmoves, 'total moves up', hits)
past = {}
KEEP = ('name','school','conf','yrs','w','l','rw','rl','wp','before','rank','prior','p4','sa','score')
for Y in range(2021, 2026):
    bd = board(Y); out = []
    for r in bd[:25]:
        up, to = moved_up(r['name'], Y)
        nxt = [s for s in BY.get(r['name'], []) if s[0] == Y + 1]
        x = {k: (round(r[k], 3) if isinstance(r[k], float) else r[k]) for k in KEEP}
        x['next'] = to if (nxt and to != r['school']) else None; x['up'] = up
        out.append(x)
    past[Y] = dict(n=len(bd), rows=out)
cur = board(2026)
for r in cur[:15]: print(round(r['score']), r['name'], r['school'], f"{r['w']}-{r['l']}", r['parts'], r['rank'], r['prior'])
json.dump(dict(asof='2026-11-19', rows=[{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()} for r in cur], bt=bt, past=past), open(O + 'rising.json', 'w'), separators=(',', ':'))
