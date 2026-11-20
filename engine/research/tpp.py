# Transfer Pipeline Points (TPP) research: share each player's development residual (actual - class-adjusted
# expected draft points) across the schools where he verifiably spent seasons. Research only: the official
# (last-school) scores are not touched. Output: tpp.json (site experimental view) + tpp_report.json (numbers for the report).
import json, collections, os, re, math, sys
E = sys.argv[1]; O = '/home/claude/concept/'; CP = '/root/cfbd_pull/'
P = json.load(open(E + '/data/pool2.json'))['players']
RAW = json.load(open(E + '/data/recruits.json'))
rid = {(x['name'], x['year'], x.get('committedTo')): str(x['id']) for x in RAW}
SA_SCH = {'Army', 'Navy', 'Air Force'}
def last(r):
    d = [m[1] for m in r['mv'] if m[1]]
    return d[-1] if d else r['committedTo']
def cred(r): return r['draftTeam'] if r['draftYear'] else last(r)
# same graded set as the site (prep3 SC)
SC = [r for r in P if r['exp'] is not None and not (not r['draftYear'] and any(m[1] and m[0] >= 2025 for m in r['mv'])) and cred(r) not in SA_SCH]
def nm(s): return re.sub(r'[^a-z]', '', re.sub(r'\b(jr|sr|ii|iii|iv|v)\b', '', s.lower()))

# ---------- rosters: (year, team) by athlete id, recruit id, and name+team
ath = collections.defaultdict(set); recs = collections.defaultdict(set); byname = collections.defaultdict(set)
RY = [y for y in range(2004, 2027) if os.path.exists(f'{CP}ros_{y}.json')]
for y in RY:
    for r in json.load(open(f'{CP}ros_{y}.json')):
        ath[str(r['id'])].add((y, r['team']))
        for q in r.get('recruitIds') or []: recs[str(q)].add((y, r['team']))
        byname[(nm(f"{r['firstName']} {r['lastName']}"), r['team'])].add(y)
# ---------- stats: per (name, team, season): production by position family, and whether any stat was recorded
STATY = [y for y in range(2009, 2026) if os.path.exists(f'{CP}stats_{y}.json')]
prod = collections.defaultdict(lambda: collections.defaultdict(float)); seen = set()
for y in STATY:
    for s in json.load(open(f'{CP}stats_{y}.json')):
        k = (nm(s['player']), s['team'], s['season']); seen.add(k)
        try: v = float(s['stat'])
        except: continue
        c, t = s['category'], s['statType']
        d = prod[k]
        if c in ('passing', 'rushing', 'receiving') and t == 'YDS': d[c] += v
        if c == 'defensive':
            if t == 'TOT': d['tkl'] += v
            if t == 'SACKS': d['sk'] += v
            if t == 'TFL': d['tfl'] += v
            if t == 'PD': d['pd'] += v
        if c == 'interceptions' and t == 'INT': d['int'] += v
def production(pg, d):
    if pg == 'QB': return d['passing'] + 2 * d['rushing']
    if pg in ('RB', 'WR', 'TE', 'ATH'): return d['rushing'] + d['receiving']
    if pg in ('DL', 'EDGE', 'LB', 'DB'): return d['tkl'] + 2 * d['tfl'] + 4 * d['sk'] + 3 * d['int'] + 2 * d['pd']
    return 0.0   # OL, specialists: no comparable production stat

# ---------- build each graded player's school path
def path(r):
    y0 = r['year']; lastyr = (r['draftYear'] - 1) if r['draftYear'] else None
    known = [r['committedTo']] + [m[1] for m in r['mv'] if m[1]] + ([r['draftTeam']] if r['draftYear'] else [])
    order = []
    for k in known:
        if k and k not in order: order.append(k)
    ss = set(ath.get(str(r.get('athleteId')), set())) | set(recs.get(rid.get((r['name'], r['year'], r['committedTo'])), set()))
    for k in order:   # name + team fallback, only for schools already in his known path
        for y in byname.get((nm(r['name']), k), ()):
            if y0 <= y <= y0 + 6: ss.add((y, k))
    ss = {(y, t) for (y, t) in ss if y0 <= y <= (lastyr if lastyr else y0 + 6) and t in order}
    if not lastyr: lastyr = max([y for y, _ in ss] + [y0 + 3])
    seasons = {k: sorted(y for y, t in ss if t == k) for k in order}
    src = {k: 'roster' if seasons[k] else None for k in order}
    # infer missing seasons from portal arrival dates when the roster record is missing
    arr = {m[1]: m[0] for m in r['mv'] if m[1]}
    for i, k in enumerate(order):
        if seasons[k]: continue
        start = y0 if i == 0 else arr.get(k)
        nxt = order[i + 1] if i + 1 < len(order) else None
        end = (arr.get(nxt) - 1) if nxt and arr.get(nxt) else (lastyr if not nxt else None)
        if start is not None and end is not None and end >= start:
            seasons[k] = list(range(start, end + 1)); src[k] = 'portal dates'
        elif k == r['draftTeam'] and r['draftYear'] and not nxt:
            seasons[k] = [lastyr]; src[k] = 'draft school (final season only)'
    unc = [k for k in order if not seasons[k]]
    # production per school
    pr = {k: sum(production(r['pg'], prod.get((nm(r['name']), k, y), collections.defaultdict(float))) for y in seasons[k]) for k in order}
    app = {k: sum(1 for y in seasons[k] if (nm(r['name']), k, y) in seen) for k in order}
    return order, seasons, src, pr, app, unc

players = []; uncertain = []
for r in SC:
    order, seasons, src, pr, app, unc = path(r)
    schools = [k for k in order if seasons[k]]
    multi = len(order) > 1
    rec = dict(r=r, order=order, seasons=seasons, src=src, pr=pr, app=app, schools=schools, multi=multi, unc=unc)
    if multi and (unc or not schools or (cred(r) not in schools)): uncertain.append(rec)
    players.append(rec)

def weights(p, method, lam=0.5):
    """Share of the residual for each school. Players with one school, or an uncertain path, keep last-school credit."""
    r = p['r']; c = cred(r)
    if not p['multi'] or p['unc'] or c not in p['schools']: return {c: 1.0}
    S = p['schools']; t = {k: len(p['seasons'][k]) for k in S}; T = sum(t.values())
    wa = {k: t[k] / T for k in S}
    if method == 'V1': return {c: 1.0}
    if method == 'A': return wa
    if method == 'P':   # A2: seasons he actually played (recorded game stats); OL/specialists and no-stat cases fall back to roster seasons
        ap = {k: p['app'][k] for k in S}; TA = sum(ap.values())
        return {k: ap[k] / TA for k in S} if TA > 0 and p['r']['pg'] not in ('OL', 'ST') else wa
    tp = sum(p['pr'][k] for k in S)
    wb = {k: p['pr'][k] / tp for k in S} if tp > 0 else wa      # production share; falls back to time (OL, no stats)
    if method == 'B': return wb
    return {k: lam * wa[k] + (1 - lam) * wb[k] for k in S}       # 'C' hybrid

def program_scores(method, lam=0.5):
    tot = collections.defaultdict(float); n = collections.defaultdict(float); nres = 0.0
    for p in players:
        R = p['r']['pts'] - p['r']['exp']; nres += R
        for k, w in weights(p, method, lam).items(): tot[k] += R * w; n[k] += w
    return tot, n, nres

# programs on the site (FBS with 150+ graded players under V1)
V1t, V1n, total_res = program_scores('V1')
data = json.load(open(O + 'data.json')); PROGS = [p['name'] for p in data['progs']]; NCL = data['meta']['ncl']
def rank(tot):
    L = sorted(PROGS, key=lambda k: -tot.get(k, 0)); return {k: i + 1 for i, k in enumerate(L)}
GC = [(99, 'S'), (96, 'A+'), (90, 'A'), (85, 'A-'), (80, 'B+'), (72, 'B'), (65, 'B-'), (58, 'C+'), (45, 'C'), (35, 'C-'), (27, 'D+'), (18, 'D'), (10, 'D-'), (0, 'F')]
def grades(tot):
    vals = sorted(tot.get(k, 0) for k in PROGS); n = len(vals)
    def pct(v): return 100 * (sum(1 for x in vals if x < v) + 0.5 * sum(1 for x in vals if x == v)) / n
    return {k: next(L for c, L in GC if pct(tot.get(k, 0)) >= c) for k in PROGS}
def spearman(a, b):
    ks = PROGS; n = len(ks); d2 = sum((a[k] - b[k]) ** 2 for k in ks); return 1 - 6 * d2 / (n * (n * n - 1))
def top(rk, n=25): return {k for k, v in rk.items() if v <= n}

rV1 = rank(V1t); gV1 = grades(V1t)
res = {}
for m, lam in (('A', None), ('P', None), ('B', None), ('C25', .25), ('C50', .5), ('C75', .75)):
    meth = m[0]; t, n_, tr = program_scores(meth, lam if lam is not None else .5)
    assert abs(tr - total_res) < 1e-6 and abs(sum(t.values()) - sum(V1t.values())) < 1e-6   # conservation: no credit created or lost
    rk = rank(t); g = grades(t)
    diff = sorted(PROGS, key=lambda k: -(t.get(k, 0) - V1t.get(k, 0)))
    res[m] = dict(rho=round(spearman(rV1, rk), 4), top25=len(top(rV1) & top(rk)), top10=len(top(rV1, 10) & top(rk, 10)),
        gchg=sum(1 for k in PROGS if g[k] != gV1[k]), gchg_letter=sum(1 for k in PROGS if g[k][0] != gV1[k][0]),
        gain=[[k, round((t[k] - V1t.get(k, 0)) / NCL, 2), rV1[k], rk[k], gV1[k], g[k]] for k in diff[:12]],
        lose=[[k, round((t[k] - V1t.get(k, 0)) / NCL, 2), rV1[k], rk[k], gV1[k], g[k]] for k in diff[::-1][:12]],
        top=[[k, round(t[k] / NCL, 1), rk[k], g[k]] for k in sorted(PROGS, key=lambda k: rk[k])[:25]])
    print(m, 'rho', res[m]['rho'], 'top25 kept', res[m]['top25'], 'top10 kept', res[m]['top10'], 'grade changes', res[m]['gchg'], '(letter', res[m]['gchg_letter'], ')')
# sensitivity: hybrid weight from 0 to 1 in 0.05 steps
sens = []; prev = None
for i in range(21):
    lam = i / 20; t, _, _ = program_scores('C', lam); rk = rank(t)
    sens.append([lam, round(spearman(rV1, rk), 4), len(top(rV1) & top(rk)), (len(top(prev) & top(rk)) if prev else None), (round(spearman(prev, rk), 4) if prev else None)])
    prev = rk
# sensitivity also for hybrid of played-seasons and production
sensP=[]
for i in range(21):
    lam=i/20
    def wC(p,lam=lam):
        a=weights(p,'P'); b=weights(p,'B'); return {k: lam*a.get(k,0)+(1-lam)*b.get(k,0) for k in set(a)|set(b)}
    tot=collections.defaultdict(float)
    for p in players:
        R=p['r']['pts']-p['r']['exp']
        for k,w in wC(p).items(): tot[k]+=R*w
    rk=rank(tot); sensP.append([lam, round(spearman(rV1,rk),4), len(top(rV1)&top(rk))])
print('sensP',sensP)
print('sensitivity (lam: rho vs V1, top25 vs V1, top25 vs previous step)', [(s[0], s[1], s[2], s[3]) for s in sens])

# ---------- coverage + counts
multi = [p for p in players if p['multi']]; drafted_multi = [p for p in multi if p['r']['draftYear']]
msch = [p for p in multi if len(p['order']) >= 3]
def srcs(p): return [p['src'][k] for k in p['order']]
cov = collections.Counter()
for p in drafted_multi:
    s = srcs(p); cov['all roster' if all(x == 'roster' for x in s) else 'uncertain' if p['unc'] else 'partly inferred'] += 1
byyr = collections.defaultdict(lambda: [0, 0, 0])
for p in multi:
    y = p['r']['year']; byyr[y][0] += 1; byyr[y][1] += 0 if p['unc'] else 1; byyr[y][2] += 1 if all(p['src'][k] == 'roster' for k in p['order']) else 0
prodcov = sum(1 for p in drafted_multi if not p['unc'] and sum(p['pr'][k] for k in p['schools']) > 0)
schools_inv = set(k for p in multi for k in p['schools'])
# ---------- examples
def ex(p):
    r = p['r']; R = r['pts'] - r['exp']
    out = dict(n=r['name'], y=r['year'], g=r['pg'], st=r['stars'], signed=r['committedTo'], fin=cred(r), dy=r['draftYear'], o=r['overall'], pts=r['pts'], exp=round(r['exp'], 1), res=round(R, 1),
               sch=[[k, p['seasons'][k], p['src'][k], round(p['pr'][k]), p['app'][k]] for k in p['order']])
    for m in ('A', 'P', 'B', 'C'):
        out[m] = {k: round(w, 3) for k, w in weights(p, m, .5).items()}
    return out
EXN = ['Jordan Addison', 'Mansoor Delane', 'Joe Burrow', 'Bo Nix', 'Cam Ward', 'Jayden Daniels', 'Michael Penix Jr.', 'Caleb Williams', 'Jalen Hurts', 'Kyler Murray', 'Baker Mayfield', 'Justin Fields', 'Kenny Pickett', 'Travis Hunter', 'Jaxson Dart', 'Dillon Gabriel']
exs = [ex(p) for p in drafted_multi if p['r']['name'] in EXN]
big = sorted([p for p in drafted_multi if not p['unc']], key=lambda p: -abs((p['r']['pts'] - p['r']['exp']) * (1 - weights(p, 'A').get(cred(p['r']), 0))))[:15]
report = dict(n_graded=len(players), total_residual=round(total_res, 3), n_multi=len(multi), n_drafted_multi=len(drafted_multi), n_3plus=len(msch),
    n_3plus_drafted=sum(1 for p in msch if p['r']['draftYear']), schools_involved=len(schools_inv), uncertain=len(uncertain),
    uncertain_drafted=sum(1 for p in uncertain if p['r']['draftYear']), drafted_cov=dict(cov), prodcov=prodcov, byyr={y: v for y, v in sorted(byyr.items())},
    roster_years=[RY[0], RY[-1]], stat_years=[STATY[0], STATY[-1]], methods=res, sens=sens, sensP=sensP,
    examples=exs, biggest=[ex(p) for p in big],
    uncertain_list=[[p['r']['name'], p['r']['year'], p['order'], p['unc'], p['r']['draftYear'] or None] for p in uncertain if p['r']['draftYear']][:60])
json.dump(report, open(O + 'tpp_report.json', 'w'), indent=1, default=str)
print('graded', len(players), 'multi-school', len(multi), 'drafted multi', len(drafted_multi), '3+ schools', len(msch), 'schools', len(schools_inv), 'uncertain', len(uncertain), 'uncertain drafted', report['uncertain_drafted'])
print('drafted coverage', dict(cov), 'with production data', prodcov)
for e in exs: print(e['n'], e['res'], [(s[0], s[1], s[2], s[3]) for s in e['sch']], 'A', e['A'], 'P', e['P'], 'B', e['B'])
