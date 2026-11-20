# Test (research only): (1) split 5-stars into three rating bands, (2) group prep-school recruits with high school
# recruits instead of JUCO. Rebuilds the whole expected-points model in a scratch folder; the live model is untouched.
import json, os, shutil, subprocess, sys, tempfile, collections
E = sys.argv[1]; O = '/home/claude/concept/'
src = open(E + '/model2.py').read()
OLD = "r['bucket']=(r['recruitType']!='HighSchool', r['stars'] or 0, min(9,int(((r['rating'] or 0.7)-0.70)*30)) if (r['stars'] or 0)<5 else 9)"
assert OLD in src
NEW = ("r['bucket']=(r['recruitType']=='JUCO', r['stars'] or 0, min(9,int(((r['rating'] or 0.7)-0.70)*30)) if (r['stars'] or 0)<5 "
       "else (12 if (r['rating'] or 0)>=0.9941 else 11 if (r['rating'] or 0)>=0.9887 else 10))")
def build(code):
    tmp = tempfile.mkdtemp(); os.makedirs(tmp + '/data')
    for f in os.listdir(E + '/data'):
        if f.endswith('.json') and f != 'pool2.json': os.symlink(E + '/data/' + f, tmp + '/data/' + f)
    shutil.copy(E + '/setaside.json', tmp + '/setaside.json')
    open(tmp + '/model2.py', 'w').write(code)
    subprocess.run([sys.executable, '-I', 'model2.py'], cwd=tmp, capture_output=True)
    P = json.load(open(tmp + '/data/pool2.json'))['players']; shutil.rmtree(tmp); return P
base = json.load(open(E + '/data/pool2.json'))['players']
alt = build(src.replace(OLD, NEW))
SA = {'Army', 'Navy', 'Air Force'}
def last(r):
    d = [m[1] for m in r['mv'] if m[1]]; return d[-1] if d else r['committedTo']
def cred(r): return r['draftTeam'] if r['draftYear'] else last(r)
def graded(P): return [r for r in P if r['exp'] is not None and not (not r['draftYear'] and any(m[1] and m[0] >= 2025 for m in r['mv'])) and cred(r) not in SA]
def cal(P):
    mat = [r for r in graded(P) if r['k'] == 8]
    def c(rs): a = sum(r['pts'] for r in rs); e = sum(r['exp'] for r in rs); return [len(rs), round(a / e, 2) if e else None]
    five = sorted([r for r in mat if r['stars'] == 5 and r['recruitType'] == 'HighSchool'], key=lambda r: -(r['rating'] or 0)); h = len(five) // 3
    return {'5-star top third': c(five[:h]), '5-star middle third': c(five[h:2 * h]), '5-star bottom third': c(five[2 * h:]),
            'Prep school': c([r for r in mat if r['recruitType'] == 'PrepSchool']), 'JUCO': c([r for r in mat if r['recruitType'] == 'JUCO']),
            'High school': c([r for r in mat if r['recruitType'] == 'HighSchool'])}
D = json.load(open(O + 'data.json')); PROGS = [p['name'] for p in D['progs']]
C = json.load(open(E + '/data/coaches.json')); FY = collections.defaultdict(set)
for c_ in C:
    for s in c_['seasons']:
        if 2002 <= s['year'] <= 2023 and (s['games'] or 0) > 0: FY[s['school']].add(s['year'])
def scores(P):
    t = collections.defaultdict(float)
    for r in graded(P):
        k = cred(r)
        if r['year'] in FY.get(k, ()): t[k] += r['pts'] - r['exp']
    return {k: t.get(k, 0) / max(1, len(FY.get(k, ()))) for k in PROGS}
GC = [(99, 'S'), (96, 'A+'), (90, 'A'), (85, 'A-'), (80, 'B+'), (72, 'B'), (65, 'B-'), (58, 'C+'), (45, 'C'), (35, 'C-'), (27, 'D+'), (18, 'D'), (10, 'D-'), (0, 'F')]
def grades(t):
    v = sorted(t.values()); n = len(v)
    def pc(x): return 100 * (sum(1 for y in v if y < x) + 0.5 * sum(1 for y in v if y == x)) / n
    return {k: next(L for cc, L in GC if pc(t[k]) >= cc) for k in PROGS}
def rank(t): L = sorted(PROGS, key=lambda k: -t[k]); return {k: i + 1 for i, k in enumerate(L)}
tb, ta = scores(base), scores(alt); rb, ra = rank(tb), rank(ta); gb, ga = grades(tb), grades(ta)
n = len(PROGS); rho = 1 - 6 * sum((rb[k] - ra[k]) ** 2 for k in PROGS) / (n * (n * n - 1))
top = lambda r, m: {k for k, v in r.items() if v <= m}
mv = sorted(PROGS, key=lambda k: -abs(ra[k] - rb[k]))[:12]
# player-level: how many player letter grades would change
pb = {(r['name'], r['year'], r['committedTo']): r['pts'] - r['exp'] for r in graded(base)}
pa = {(r['name'], r['year'], r['committedTo']): r['pts'] - r['exp'] for r in graded(alt)}
big5 = sorted([(k, round(pa[k] - pb[k], 1)) for k in pb if k in pa and abs(pa[k] - pb[k]) > 5], key=lambda x: x[1])
out = dict(cal_before=cal(base), cal_after=cal(alt), rho=round(rho, 4), top10=len(top(rb, 10) & top(ra, 10)), top25=len(top(rb, 25) & top(ra, 25)),
           grade_changes=sum(1 for k in PROGS if gb[k] != ga[k]), letter_changes=sum(1 for k in PROGS if gb[k][0] != ga[k][0]),
           movers=[[k, rb[k], ra[k], gb[k], ga[k]] for k in mv], players_moved_5plus=len(big5), examples_down=big5[:6], examples_up=big5[-6:],
           bands='5-star rating bands: top >= 0.9941, middle 0.9887-0.9940, bottom < 0.9887 (thirds of 5-stars in complete classes)')
json.dump(out, open(O + 'caltest.json', 'w'), indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k not in ('examples_down', 'examples_up')}, default=str))
print('down', big5[:6]); print('up', big5[-6:])
