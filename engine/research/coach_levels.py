"""Build site/coachlvl.json: each head coach's record at the power-conference level vs the Group of Five level (2002-2025 FBS
seasons, CFBD coach seasons), plus a card for current head coaches without a Vetted report card. Display only; not part of any
grade (v1.44, JC Nov. 22). Power = SEC, Big Ten, Big 12, ACC, Pac-10/Pac-12 through 2023, Big East through 2012, Notre Dame.
Everything else in FBS = Group of Five. FCS and lower seasons aren't in our source and aren't counted.
Usage: python3 coach_levels.py <engine data dir> <head_coaches_2026.json> <season.json> <data.json> <out coachlvl.json>"""
import json, sys
D, H26, SZ, DJ, OUT = sys.argv[1:6]
C = json.load(open(D + '/coaches.json')); H = json.load(open(H26)); S = json.load(open(SZ)); DD = json.load(open(DJ))
graded = {c['name'] for c in DD['coaches']}
def power(s):
    cf, y = s['conference'], s['year']
    if cf in ('SEC', 'Big Ten', 'Big 12', 'ACC', 'Pac-10'): return True
    if cf == 'Pac-12': return y <= 2023
    if cf == 'Big East': return y <= 2012
    return s['school'] == 'Notre Dame'
out = {}
cur = {n: sch for n, sch in H.items()}
for c in C:
    nm = f"{c['firstName']} {c['lastName']}"
    ss = [s for s in c['seasons'] if 2002 <= s['year'] <= 2025 and s['games']]
    if not ss and nm not in cur: continue
    lv = {'p': [0, 0, 0, 0.0, 0], 'g': [0, 0, 0, 0.0, 0]}   # seasons, wins, losses, srs*games, games with srs
    st = []
    for s in sorted(ss, key=lambda s: s['year']):
        k = 'p' if power(s) else 'g'; L = lv[k]
        L[0] += 1; L[1] += s['wins']; L[2] += s['losses']
        if s.get('srs') is not None: L[3] += s['srs'] * s['games']; L[4] += s['games']
        if st and st[-1][0] == s['school'] and st[-1][2] == s['year'] - 1 and st[-1][5] == k: st[-1][2] = s['year']; st[-1][3] += s['wins']; st[-1][4] += s['losses']
        else: st.append([s['school'], s['year'], s['year'], s['wins'], s['losses'], k])
    rec = {k: ([v[0], v[1], v[2], round(v[3] / v[4], 1) if v[4] else None] if v[0] else None) for k, v in lv.items()}
    def pct(r): return r[1] / max(1, r[1] + r[2])
    P, G = rec['p'], rec['g']; tag = None
    if P and P[0] >= 2 and pct(P) >= .65 and G and G[0] >= 2 and pct(G) >= .65: tag = 'both'
    elif P and P[0] >= 2 and pct(P) >= .65: tag = 'power'
    elif G and G[0] >= 3 and pct(G) >= .65 and P and P[0] >= 2 and pct(P) < .55: tag = 'nocarry'
    elif G and G[0] >= 2 and not P: tag = 'untested'
    e = dict(p=P, g=G, st=st, tag=tag)
    s26 = [s for s in c['seasons'] if s['year'] == 2026]
    if s26 and nm in cur and cur[nm] == s26[0]['school'] and S['t'].get(s26[0]['school']):
        w, l = S['t'][s26[0]['school']]; e['n26'] = [s26[0]['school'], 'p' if power(s26[0]) and s26[0]['conference'] != 'Pac-12' else 'g', w, l]
    if nm in cur and nm not in graded:
        sch = cur[nm]; e['now'] = sch; e['r26'] = S['t'].get(sch)
    if nm in out:   # same name twice in the source: keep the one with more seasons
        if sum(x[0] for x in (out[nm]['p'], out[nm]['g']) if x) >= sum(x[0] for x in (P, G) if x): continue
    out[nm] = e
# current head coaches with no CFBD seasons at all
for nm, sch in cur.items():
    if nm not in out: out[nm] = dict(p=None, g=None, st=[], tag=None, now=sch, r26=S['t'].get(sch))
    elif nm not in graded: out[nm]['now'] = sch; out[nm]['r26'] = S['t'].get(sch)
json.dump(dict(v=1, asof=S['asof'], c=out), open(OUT, 'w'), separators=(',', ':'))
print('coachlvl.json', len(out), 'coaches;', sum(1 for v in out.values() if v.get('now')), 'current head coaches without a report card')
