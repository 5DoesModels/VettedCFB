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
out = dict(v=1, asof=S['asof'], n=len(rows), corr=round(corr, 3), bins=bins(rows), years=yrs, team=team)
json.dump(out, open(OUT, 'w'), separators=(',', ':'))
print('portalwin.json', len(rows), 'team-seasons, corr', round(corr, 3), out['bins'])
