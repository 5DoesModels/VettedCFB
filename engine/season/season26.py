"""Build site/season.json: 2026 records so far and in-season head coaching changes.
Display only (v1.38, JC Nov. 22): 2026 games count toward grades only after the season ends.
Inputs: CFBD /games?year=2026 (regular, FBS) saved to games.json, CFBD /coaches?year=2026 saved to coaches_2026.json,
and changes_2026.json (hand-maintained, sourced). Usage: python3 season26.py <dir with the two CFBD files> <out season.json>"""
import json, sys, os
D = sys.argv[1]; OUT = sys.argv[2]; HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(D, 'games.json'))); C = json.load(open(os.path.join(D, 'coaches_2026.json')))
CH = json.load(open(os.path.join(HERE, 'changes_2026.json')))
done = sorted([g for g in G if g.get('completed') and g['homePoints'] is not None], key=lambda g: g['startDate'])
def rec(team, lo=None, hi=None):
    r = [0, 0]
    for g in done:
        if team not in (g['homeTeam'], g['awayTeam']): continue
        d = g['startDate'][:10]
        if (lo and d <= lo) or (hi and d > hi): continue
        win = (g['homePoints'] > g['awayPoints']) == (g['homeTeam'] == team)
        r[0 if win else 1] += 1
    return r
teams = sorted({g['homeTeam'] for g in G} | {g['awayTeam'] for g in G})
T = {t: rec(t) for t in teams}
chg = {x['school']: x for x in CH['changes']}
coach = {}
for c in C:
    nm = f"{c['firstName']} {c['lastName']}"
    for s in c['seasons']:
        if s['year'] != 2026: continue
        sch = s['school']; x = chg.get(sch)
        if x and x['out'] == nm:
            coach[nm] = dict(s=sch, r=rec(sch, hi=x['date']), st='fired', d=x['date'], i=x['interim'], ir=rec(sch, lo=x['date']))
        elif sch in T:
            coach[nm] = dict(s=sch, r=T[sch], st='active')
interim = {x['school']: dict(n=x['interim'], r=rec(x['school'], lo=x['date']), out=x['out'], d=x['date'], next=x.get('next')) for x in CH['changes']}
weeks = max(g['week'] for g in done)
out = dict(v=1, season=2026, asof=CH['asof'], week=weeks, games=len(done), t=T, c=coach, interim=interim)
json.dump(out, open(OUT, 'w'), separators=(',', ':'))
print('season.json', len(coach), 'coaches', len(interim), 'changes, through week', weeks)
