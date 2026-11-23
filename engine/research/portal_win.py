"""Build site/portalwin.json: transfers in vs winning, by FBS team-season (2021-2026), plus roster-building context.
Not part of any grade (v1.39, JC Nov. 23). Transfers in = CFBD portal entries listing that school as destination for that
season's window. Record: CFBD coach seasons (2021-2025) and season.json (2026 so far, display only).
HS signees: CFBD recruiting (high school route) by signing school and class. Kept = HS signees from the 2020-2023 classes with
no move to another school in our roster/portal records.
Usage: python3 portal_win.py <engine data dir> <season.json> <out portalwin.json>"""
import json, sys, collections, statistics as st, math
D, SZ, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
P = json.load(open(D + '/portal.json')); C = json.load(open(D + '/coaches.json')); X = json.load(open(D + '/pool2.json'))['players']
S = json.load(open(SZ))
inc = collections.Counter((x['season'], x['destination']) for x in P if x.get('destination'))
W = collections.defaultdict(lambda: [0, 0])
for c in C:
    for s in c['seasons']:
        if 2021 <= s['year'] <= 2025 and s['games']: W[(s['year'], s['school'])][0] += s['wins']; W[(s['year'], s['school'])][1] += s['losses']
for t, (w, l) in S['t'].items(): W[(2026, t)] = [w, l]
rows = [[y, t, inc.get((y, t), 0), w, l] for (y, t), (w, l) in sorted(W.items()) if w + l >= 8]
def bins(R):
    out = []
    for lo, hi in ((0, 10), (11, 20), (21, 30), (31, 99)):
        g = [r for r in R if lo <= r[2] <= hi]
        if g: out.append([f'{lo}-{hi}' if hi < 99 else f'{lo}+', len(g), round(100 * st.mean(r[3] / (r[3] + r[4]) for r in g), 1), round(100 * sum(1 for r in g if r[3] / (r[3] + r[4]) >= .769) / len(g), 1)])
    return out
x = [r[2] for r in rows]; yv = [r[3] / (r[3] + r[4]) for r in rows]; mx, my = st.mean(x), st.mean(yv)
corr = sum((a - mx) * (b - my) for a, b in zip(x, yv)) / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in yv))
yrs = []
for y in range(2021, 2027):
    g = [r for r in rows if r[0] == y]; top = sorted(g, key=lambda r: -(r[3] / (r[3] + r[4])))[:12]
    yrs.append([y, st.median(r[2] for r in g), st.median(r[2] for r in top), [[r[1], r[2], r[3], r[4]] for r in top]])
hs = collections.Counter((r['year'], r['committedTo']) for r in X if r['recruitType'] == 'HighSchool' and r['committedTo'] and 2021 <= r['year'] <= 2026)
keep = collections.defaultdict(lambda: [0, 0])
for r in X:
    if r['recruitType'] == 'HighSchool' and r['committedTo'] and 2020 <= r['year'] <= 2023:
        mv = any(m[1] and m[1] != r['committedTo'] for m in r['mv']); keep[r['committedTo']][0] += (not mv); keep[r['committedTo']][1] += 1
teams = sorted({r[1] for r in rows})
team = {t: dict(r=[[r[0], r[2], r[3], r[4]] for r in rows if r[1] == t], hs=[[y, hs.get((y, t), 0)] for y in range(2021, 2027)], kept=keep.get(t)) for t in teams}
# v1.43 (JC, Nov. 22): 2026 so far. Transfers in without players who followed a head coach from his old FBS head job
# (origin = the school he coached in 2025), records through season.json, and the latest CFP committee top 25 (sourced file).
import os
E = os.path.dirname(os.path.abspath(__file__)) + '/..'
H26 = json.load(open(E + '/awards/head_coaches_2026.json')); CFP = json.load(open(E + '/season/cfp_2026.json'))
last25 = {}
for c in C:
    s25 = [s for s in c['seasons'] if s['year'] == 2025 and s['games']]
    if s25: last25[f"{c['firstName']} {c['lastName']}"] = max(s25, key=lambda s: s['games'])['school']
moved = {sch: (last25[nm], nm) for nm, sch in H26.items() if last25.get(nm) and last25[nm] != sch}
n26 = collections.Counter(); f26 = collections.Counter()
for x in P:
    d = x.get('destination')
    if x['season'] != 2026 or not d: continue
    if d in moved and x['origin'] == moved[d][0]: f26[d] += 1
    else: n26[d] += 1
R26 = [[t, n26.get(t, 0), w, l, f26.get(t, 0), (CFP['top25'].index(t) + 1) if t in CFP['top25'] else 0] for t, (w, l) in S['t'].items() if w + l >= 8]
def grp(G):
    k = len(G); return dict(n=k, w=sum(r[2] for r in G), l=sum(r[3] for r in G), l3=sum(r[3] >= 3 for r in G), l4=sum(r[3] >= 4 for r in G), l5=sum(r[3] >= 5 for r in G),
        losing=sum(r[2] < r[3] for r in G), p10=sum(r[2] / (r[2] + r[3]) >= .769 for r in G), cfp=sum(r[5] > 0 for r in G), cfp12=sum(0 < r[5] <= 12 for r in G))
big = sorted([r for r in R26 if r[1] >= 30], key=lambda r: (-r[1], r[0]))
y26 = dict(cut=30, cfpdate=CFP['date'], rows=big, big=grp(big), few=grp([r for r in R26 if r[1] <= 15]), rest=grp([r for r in R26 if r[1] < 30]), all=grp(R26),
           moved=[[sch, o, nm, f26.get(sch, 0)] for sch, (o, nm) in sorted(moved.items())])
out = dict(v=1, asof=S['asof'], n=len(rows), corr=round(corr, 3), bins=bins(rows), years=yrs, team=team, y26=y26)
json.dump(out, open(OUT, 'w'), separators=(',', ':'))
print('portalwin.json', len(rows), 'team-seasons, corr', round(corr, 3), out['bins'])
