"""Build coach_honors.json: each head coach's honors and penalties with Vetted points (v1.39, approved by JC Nov. 22-23, 2026).
Credit goes to the head coach of that school that season, using the same rule as player credit (most games; an interim who
took over and didn't stay gets no credit, the coach who started the season does).
Inputs (this folder unless noted): honors_2002_2025.json (sourced awards, titles, CFP fields, conference champions),
postseason_games_2002_2025.json and head_coaches_2026.json (from CFBD), ../season/changes_2026.json, and CFBD coaches.json (argv[1]).
Usage: python3 build_coach_honors.py <path to coaches.json> <out coach_honors.json>"""
import json, sys, os, collections
H_ = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(sys.argv[1])); OUT = sys.argv[2]
H = json.load(open(os.path.join(H_, 'honors_2002_2025.json')))
POST = json.load(open(os.path.join(H_, 'postseason_games_2002_2025.json')))
J26 = json.load(open(os.path.join(H_, 'head_coaches_2026.json')))
CH26 = json.load(open(os.path.join(H_, '..', 'season', 'changes_2026.json')))['changes']
MAJ = ('Heisman', 'Maxwell', 'Walter Camp Player')
PT = dict(title=5, runner=3, cfp=1.5, conf=1.5, w10=0.75, coy=0.25, major=0.3, player=0.1,
          midfire=-2, endlose=-1, worse=-1, sub500=-0.5)
NOTFIRED = {('Jerry Kill', 2015), ('Mike Leach', 2022)}   # medical retirement; died during the season
nm_ = lambda c: f"{c['firstName']} {c['lastName']}"
# head coach of each school-season (same rule as prep3, v1.37 interim fix)
HC, HG = {}, {}; byk = collections.defaultdict(list); cy = collections.defaultdict(set); car = collections.defaultdict(list)
for c in C:
    nm = nm_(c)
    for s in c['seasons']:
        g = s['games'] or 0; k = (s['school'], s['year'])
        if g >= 1 and g > HG.get(k, -1): HC[k] = nm; HG[k] = g
        if g >= 1 or s['year'] == 2026: cy[(nm, s['school'])].add(s['year'])
        if g >= 1: byk[k].append((nm, g))
        if g >= 1 and s['year'] <= 2025: car[nm].append(s)
for k, v in byk.items():
    top = HC.get(k); sch, y = k
    if len(v) < 2 or not top or y - 1 in cy[(top, sch)] or y + 1 in cy[(top, sch)]: continue
    st = [n for n, g in v if n != top and y - 1 in cy[(n, sch)]]
    if st: HC[k] = st[0]
OUTD = collections.defaultdict(list)
def add(nm, y, kind, label, sch, p): OUTD[nm].append([y, kind, label, sch, p])
def credit(sch, y, kind, label, p):
    nm = HC.get((sch, y))
    if nm: add(nm, y, kind, label, sch, p)
for aw, L in H['coy'].items():
    for y, v in L.items(): credit(v.split('|')[1], int(y), 'coy', f'{aw} Coach of the Year', PT['coy'])
for y, (w, l) in H['title'].items():
    if w: credit(w, int(y), 'title', 'National champion', PT['title'])
    credit(l, int(y), 'runner', 'National title game', PT['runner'])
for y, L in H['cfp'].items():
    for t in L:
        if t not in (H['title'].get(y) or []): credit(t, int(y), 'cfp', 'College Football Playoff', PT['cfp'])
for k, v in H['conf'].items():
    y, cf = k.split('|')
    for t in v['ch']: credit(t, int(y), 'conf', cf + ' champion' + (' (shared)' if len(v['ch']) > 1 else ''), PT['conf'])
for aw, L in H['players'].items():
    for y, v in L.items():
        n, s = v.split('|'); credit(s, int(y), 'player', f'{aw}: {n}', PT['major'] if aw in MAJ else PT['player'])
for nm, ss in car.items():
    ss.sort(key=lambda s: s['year']); stints = []
    for s in ss:
        if stints and stints[-1]['sch'] == s['school'] and stints[-1]['y1'] == s['year'] - 1: stints[-1]['y1'] = s['year']; stints[-1]['ss'].append(s)
        else: stints.append(dict(sch=s['school'], y0=s['year'], y1=s['year'], ss=[s]))
    for st in stints:
        for i, s in enumerate(st['ss']):
            if s['year'] < 2002: continue
            if (s['wins'] or 0) >= 10: add(nm, s['year'], 'w10', f"{s['wins']}-{s['losses']} season", s['school'], PT['w10'])
            # losing seasons count from his third year at a school (years one and two are mostly the roster he inherited)
            if s['games'] >= 6 and s['wins'] < s['losses'] and (s['year'] - st['y0']) >= 2:
                add(nm, s['year'], 'sub500', f"{s['wins']}-{s['losses']} season", s['school'], PT['sub500'])
    for i, st in enumerate(stints):
        last = st['ss'][-1]; y = last['year']
        if y < 2002: continue
        if y == 2025 and J26.get(nm) == st['sch']: continue
        nxt = stints[i + 1] if i + 1 < len(stints) else None
        moved = (nxt and nxt['y0'] == y + 1) or (y == 2025 and nm in J26 and J26[nm] != st['sch'])
        oth = sum(g for n, g in byk[(st['sch'], y)] if n != nm)
        if (nm, y) in NOTFIRED or (st['y0'] == y and oth > 0): continue
        if oth > 0 and not (moved and oth <= POST.get(f"{st['sch']}|{y}", 0) + 1): add(nm, y, 'midfire', 'Replaced mid-season', st['sch'], PT['midfire'])
        elif not moved and last['wins'] < last['losses']: add(nm, y, 'endlose', 'Job ended after a losing season', st['sch'], PT['endlose'])
    for st in stints:
        if st['y0'] < 2005: continue
        pre = [(s2['wins'], s2['losses']) for y in range(st['y0'] - 3, st['y0']) for n, g in byk[(st['sch'], y)] for s2 in car[n] if s2['school'] == st['sch'] and s2['year'] == y]
        post = [(s2['wins'], s2['losses']) for s2 in st['ss'][:3]]
        if len(post) < 2 or len(pre) < 3: continue
        pw = sum(a for a, b in pre) / max(1, sum(a + b for a, b in pre)); qw = sum(a for a, b in post) / max(1, sum(a + b for a, b in post))
        if qw < pw - 0.10: add(nm, st['y0'], 'worse', f"First {len(post)} seasons {round(100*qw)}% vs {round(100*pw)}% the 3 seasons before him", st['sch'], PT['worse'])
for x in CH26: add(x['out'], 2026, 'midfire', 'Fired mid-season', x['school'], PT['midfire'])
out = dict(v=1, points=PT, coaches={k: sorted(v) for k, v in OUTD.items()})
json.dump(out, open(OUT, 'w'), separators=(',', ':'))
print('coach_honors.json', len(OUTD), 'coaches', collections.Counter(x[1] for v in OUTD.values() for x in v))
