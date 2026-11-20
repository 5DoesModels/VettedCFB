# Methodology tests (research only, nothing published changes):
# 1) draft-point weight sensitivity  2) eligible-FBS-season denominator  3) drafted D-floor impact
# 4) grouping calibration  5) analytics association statistics
import json, collections, math, os, shutil, subprocess, sys, tempfile
E = sys.argv[1]; O = '/home/claude/concept/'
D = json.load(open(O + 'data.json')); PROGS = [p['name'] for p in D['progs']]; NCL = D['meta']['ncl']
SA = {'Army', 'Navy', 'Air Force'}
def last(r):
    d = [m[1] for m in r['mv'] if m[1]]; return d[-1] if d else r['committedTo']
def cred(r): return r['draftTeam'] if r['draftYear'] else last(r)
def graded(P): return [r for r in P if r['exp'] is not None and not (not r['draftYear'] and any(m[1] and m[0] >= 2025 for m in r['mv'])) and cred(r) not in SA]
def progscore(P):
    t = collections.defaultdict(float)
    for r in graded(P): t[cred(r)] += r['pts'] - r['exp']
    return t
def rank(t): L = sorted(PROGS, key=lambda k: -t.get(k, 0)); return {k: i + 1 for i, k in enumerate(L)}
def rho(a, b): n = len(PROGS); return 1 - 6 * sum((a[k] - b[k]) ** 2 for k in PROGS) / (n * (n * n - 1))
def topn(rk, n): return {k for k, v in rk.items() if v <= n}
out = {}

# ---------- 1) draft-point weights: refit the whole expected-points model under each scale
base = json.load(open(E + '/data/pool2.json'))['players']; t0 = progscore(base); r0 = rank(t0)
SCALES = {
 'smooth': "def tier(d):\n    if d is None: return 'Undrafted',0\n    import math\n    return 'Pick',round(100*math.exp(-(d['overall']-1)/45),2)\n",
 'rounds': "def tier(d):\n    if d is None: return 'Undrafted',0\n    return 'Round',{1:50,2:30,3:20,4:12,5:8,6:5,7:3}.get(d['round'],3)\n",
}
src = open(E + '/model2.py').read()
i0 = src.index('def tier(d):'); i1 = src.index('drafted={v:D[k]')
out['weights'] = {}
for name, fn in SCALES.items():
    tmp = tempfile.mkdtemp(); os.makedirs(tmp + '/data')
    for f in os.listdir(E + '/data'):
        if f.endswith('.json') and f != 'pool2.json': os.symlink(E + '/data/' + f, tmp + '/data/' + f)
    shutil.copy(E + '/setaside.json', tmp + '/setaside.json')
    open(tmp + '/model2.py', 'w').write(src[:i0] + fn + src[i1:])
    subprocess.run([sys.executable, '-I', 'model2.py'], cwd=tmp, capture_output=True)
    P = json.load(open(tmp + '/data/pool2.json'))['players']; t = progscore(P); rk = rank(t)
    mv = sorted(PROGS, key=lambda k: -abs(rk[k] - r0[k]))[:8]
    out['weights'][name] = dict(rho=round(rho(r0, rk), 4), top10=len(topn(r0, 10) & topn(rk, 10)), top25=len(topn(r0, 25) & topn(rk, 25)),
        movers=[[k, r0[k], rk[k]] for k in mv], top10list=[k for k in sorted(PROGS, key=lambda k: rk[k])[:10]])
    shutil.rmtree(tmp)
out['weights']['current_top10'] = [k for k in sorted(PROGS, key=lambda k: r0[k])[:10]]
print('WEIGHTS', {k: (v['rho'], v['top10'], v['top25']) for k, v in out['weights'].items() if k != 'current_top10'})

# ---------- 2) eligible FBS signing seasons as the denominator
C = json.load(open(E + '/data/coaches.json')); fbs_yrs = collections.defaultdict(set)
for c in C:
    for s in c['seasons']:
        if 2002 <= s['year'] <= 2023 and (s['games'] or 0) > 0: fbs_yrs[s['school']].add(s['year'])
elig = {k: max(1, len(fbs_yrs.get(k, ()))) for k in PROGS}
a = {k: t0.get(k, 0) / NCL for k in PROGS}; b = {k: t0.get(k, 0) / elig[k] for k in PROGS}
ra, rb = rank(a), rank(b)
short = sorted([k for k in PROGS if elig[k] < 22], key=lambda k: elig[k])
out['denom'] = dict(rho=round(rho(ra, rb), 4), top25=len(topn(ra, 25) & topn(rb, 25)), n_short=len(short),
    short=[[k, elig[k], ra[k], rb[k], round(a[k], 1), round(b[k], 1)] for k in short])
print('DENOM', out['denom']['rho'], out['denom']['top25'], out['denom']['short'][:10])

# ---------- 3) drafted D-floor: how many drafted players would grade below D without it
pc = D['meta']['pcut']   # [[percentile, residual cutoff], ...] descending
GC = [(99, 'S'), (96, 'A+'), (90, 'A'), (85, 'A-'), (80, 'B+'), (72, 'B'), (65, 'B-'), (58, 'C+'), (45, 'C'), (35, 'C-'), (27, 'D+'), (18, 'D'), (10, 'D-'), (0, 'F')]
def letter(v):
    c = next((x for x in pc if v >= x[1]), None); p = c[0] if c else 0; return next(L for cc, L in GC if p >= cc)
G = graded(base); dr = [r for r in G if r['draftYear']]
lifted = [r for r in dr if letter(r['pae'] if 'pae' in r else r['pts'] - r['exp']) in ('D-', 'F')]
out['dfloor'] = dict(drafted=len(dr), lifted=len(lifted), share=round(100 * len(lifted) / len(dr), 1),
    by_round=dict(collections.Counter(r['round'] for r in lifted)), by_stars=dict(collections.Counter(r['stars'] for r in lifted)),
    examples=[[r['name'], r['year'], r['stars'], r['round'], r['overall'], round(r['pts'] - r['exp'], 1)] for r in sorted(lifted, key=lambda r: r['pts'] - r['exp'])[:8]])
print('DFLOOR', out['dfloor']['lifted'], 'of', out['dfloor']['drafted'], out['dfloor']['by_round'], out['dfloor']['by_stars'])

# ---------- 4) calibration of groups (complete classes): actual / expected; 1.00 = calibrated
mat = [r for r in G if r['k'] == 8]
def cal(rs): a_ = sum(r['pts'] for r in rs); e_ = sum(r['exp'] for r in rs); return [len(rs), round(a_ / e_, 2) if e_ else None]
five = sorted([r for r in mat if r['stars'] == 5 and r['recruitType'] == 'HighSchool'], key=lambda r: -(r['rating'] or 0))
h = len(five) // 3
out['cal'] = {'5-star top third (rating)': cal(five[:h]), '5-star middle third': cal(five[h:2 * h]), '5-star bottom third': cal(five[2 * h:]),
    'JUCO': cal([r for r in mat if r['recruitType'] == 'JUCO']), 'Prep school': cal([r for r in mat if r['recruitType'] == 'PrepSchool']),
    'High school': cal([r for r in mat if r['recruitType'] == 'HighSchool'])}
for g in ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'EDGE', 'LB', 'DB']: out['cal']['Position ' + g] = cal([r for r in mat if r['pg'] == g])
for s in (5, 4, 3, 2, 0): out['cal'][f'{s}-star' if s else 'Unranked'] = cal([r for r in mat if (r['stars'] or 0) == s])
print('CAL', out['cal'])

# ---------- 5) "Does it win" association: n, correlation CI, partial correlation controlling for recruiting
A = D['ana']; n = len(A)
def corr(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y); sx = math.sqrt(sum((a - mx) ** 2 for a in x)); sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)
dev = [a[1] for a in A]; tal = [a[2] for a in A]; win = [a[3] for a in A]
def ci(r, n):
    z = math.atanh(r); se = 1 / math.sqrt(n - 3); return [round(math.tanh(z - 1.96 * se), 2), round(math.tanh(z + 1.96 * se), 2)]
rdw, rtw, rdt = corr(dev, win), corr(tal, win), corr(dev, tal)
partial = (rdw - rtw * rdt) / math.sqrt((1 - rtw ** 2) * (1 - rdt ** 2))
out['assoc'] = dict(n=n, r_dev_win=round(rdw, 2), ci_dev_win=ci(rdw, n), r_tal_win=round(rtw, 2), ci_tal_win=ci(rtw, n), r_dev_tal=round(rdt, 2),
    partial_dev_win_given_tal=round(partial, 2), ci_partial=ci(partial, n - 1), r2_tal=D['stats']['r2_tal'], r2_both=D['stats']['r2_both'])
print('ASSOC', out['assoc'])
json.dump(out, open(O + 'mtests.json', 'w'), indent=1)
