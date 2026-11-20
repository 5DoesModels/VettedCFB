# Vetted player tags (v1.32). Factual labels built from official data only; every tag has a rule that can be checked.
# History tags describe a player's comparable group (route, stars, position), never a prediction for him.
import json, sys, csv, math, collections, re
sys.path.insert(0, '/home/claude/concept')
from schoolstate import SS
E = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/vetted-cfb/engine'
O = '/home/claude/concept/'
P = json.load(open(E + '/data/pool2.json'))['players']
R = json.load(open(E + '/data/recruits.json'))
PRED = json.load(open(O + 'pred.json'))
nm = lambda s: re.sub(r'[^a-z]', '', re.sub(r'\b(jr|sr|ii|iii|iv|v)\b', '', (s or '').lower()))

# high school rating for players with several records (JC decision 9): an earlier HighSchool record with the same name
hs = collections.defaultdict(list)
for r in R:
    if r['recruitType'] == 'HighSchool': hs[nm(r['name'])].append(r)
def hs_stars(p):
    if p['recruitType'] == 'HighSchool': return p['stars'] or 0
    c = [r for r in hs[nm(p['name'])] if r['year'] <= p['year'] and p['year'] - r['year'] <= 4]
    return (c[-1]['stars'] or 0) if len(c) == 1 else (p['stars'] or 0)

# NFL career facts by draft year + overall pick (nflverse draft_picks)
NFL = {}
for row in csv.DictReader(open('/home/claude/nfl/draft_picks.csv')):
    try: NFL[(int(row['season']), int(row['pick']))] = dict(pb=int(row['probowls'] or 0), ap=int(row['allpro'] or 0), to=int(row['to'] or 0))
    except ValueError: pass
last_pick = {}
for p in P:
    if p['draftYear']: last_pick[p['draftYear']] = None
D = json.load(open(E + '/data/draft.json'))
for d in D: last_pick[d['year']] = max(last_pick.get(d['year']) or 0, d['overall'])
LASTNFL = max(v['to'] for v in NFL.values())

# group statistics (from pred.json, same definitions as the Predictions page)
dco, tco, DY, TY = PRED['dco'], PRED['tco'], PRED['dy'], PRED['ty']
def top10(c):
    ok = {k: v[0] / v[1] for k, v in c.items() if v[1] >= 20}
    n = max(1, math.ceil(len(ok) * 0.10))
    cut = sorted(ok.values(), reverse=True)[n - 1]
    return {k for k, v in ok.items() if v >= cut}, cut
TOPD, cutd = top10(dco); TOPT, cutt = top10(tco)
gkey = lambda route, stars, pg: (('H' if route == 'HighSchool' else 'J' if route == 'JUCO' else '') + str(stars or 0) + pg) if route in ('HighSchool', 'JUCO') else None

DEFS = {
 'dia': ['Diamond in the Rough', 'Rated two or three stars out of high school (247Sports Composite) and later selected in the NFL Draft, any round.'],
 't10': ['Top-10 Pick', 'Selected with one of the first ten picks of the NFL Draft.'],
 'r1': ['First-Rounder', 'Selected in the first round of the NFL Draft.'],
 'hype': ['Lived Up to the Hype', 'A five-star recruit who was selected in the first round.'],
 'irr': ['Mr. Irrelevant', 'The very last pick of his NFL Draft.'],
 'pay': ['Portal Payoff', 'Transferred through the portal to a new school, then was drafted.'],
 'jour': ['Journeyman', 'Played for three or more colleges on record (his signing school, portal moves and the school he was drafted from).'],
 'home': ['Hometown Hero', 'Signed with a school in his home state out of high school and was drafted from that same school.'],
 'pb': ['Pro Bowler', 'Selected to at least one Pro Bowl in the NFL.'],
 'ap': ['All-Pro', 'Named first-team All-Pro at least once in the NFL.'],
 'vet': ['NFL Veteran', f'Reached a fifth NFL season (NFL data through {LASTNFL}).'],
 'tr': ['Transferred', 'Has a transfer portal entry listing a school other than the one he signed with (2021 on).'],
 'juco': ['JUCO Route', 'Signed with his college out of junior college.'],
 'hd': ['History: Draft Pipeline', f'His comparable group (signing route, star rating and position; 20+ players, {DY[0]}–{DY[1]} classes) is in the top 10% of all groups for share drafted ({round(100*cutd)}% or higher). This describes past players like him, not a prediction for him.'],
 'ht': ['History: Portal Movers', f'His comparable group (signing route, star rating and position; 20+ players, {TY[0]}–{TY[1]} classes) is in the top 10% of all groups for share that later transferred ({round(100*cutt)}% or higher). This describes past players like him, not a prediction for him.'],
}
OUT = {}
def add(key, code, gk):
    e = OUT.setdefault(key, [[], gk]);
    if code not in e[0]: e[0].append(code)
    if gk and not e[1]: e[1] = gk
for p in P:
    key = f"{p['name']}|{p['year']}"
    gk = gkey(p['recruitType'], p['stars'], p['pg'])
    moved = [m for m in (p.get('mv') or []) if m[1] and m[1] != p['committedTo']]
    schools = [p['committedTo']] + [m[1] for m in (p.get('mv') or []) if m[1]] + ([p['draftTeam']] if p.get('draftTeam') else [])
    distinct = []
    for s in schools:
        if s and (not distinct or distinct[-1] != s) and s not in distinct: distinct.append(s)
    if moved: add(key, 'tr', gk)
    if p['recruitType'] == 'JUCO': add(key, 'juco', gk)
    if len(distinct) >= 3: add(key, 'jour', gk)
    if p['draftYear']:
        st = hs_stars(p)
        if st in (2, 3): add(key, 'dia', gk)
        if p['overall'] <= 10: add(key, 't10', gk)
        elif p['round'] == 1: add(key, 'r1', gk)
        if (p['stars'] or 0) == 5 and p['round'] == 1: add(key, 'hype', gk)
        if p['overall'] == last_pick.get(p['draftYear']): add(key, 'irr', gk)
        if moved: add(key, 'pay', gk)
        if p['draftTeam'] == p['committedTo'] and not moved and SS.get(p['committedTo']) and SS.get(p['committedTo']) == p['stateProvince'] and p['recruitType'] == 'HighSchool': add(key, 'home', gk)
        n = NFL.get((p['draftYear'], p['overall']))
        if n:
            if n['ap'] >= 1: add(key, 'ap', gk)
            if n['pb'] >= 1: add(key, 'pb', gk)
            if n['to'] - p['draftYear'] + 1 >= 5: add(key, 'vet', gk)
# current players (Predictions rows): history tags, transfer and JUCO tags
G = PRED['g']
for r in PRED['rows']:
    key = f"{r[0]}|{r[1]}"
    gk = gkey(r[12], r[3], G[r[2]])
    if gk in TOPD: add(key, 'hd', gk)
    if gk in TOPT and not r[9]: add(key, 'ht', gk)
    for b in r[13] or []:
        add(key, {'moved': 'tr', 'juco': 'juco'}[b], gk)
    if key in OUT and not OUT[key][1]: OUT[key][1] = gk
grp = {}
for e in OUT.values():
    k = e[1]
    if k and k not in grp: grp[k] = (dco.get(k) or [0, 0]) + (tco.get(k) or [0, 0])
out = dict(v=1, defs=DEFS, dy=DY, ty=TY, grp=grp, p={k: [v[0], v[1]] for k, v in OUT.items()})
s = json.dumps(out, separators=(',', ':')); open(O + 'tags.json', 'w').write(s)
cnt = collections.Counter(c for v in OUT.values() for c in v[0])
print('tags.json', len(s) // 1024, 'KB', len(OUT), 'players', dict(cnt), 'top10 cuts', round(cutd, 3), round(cutt, 3), len(TOPD), len(TOPT))
