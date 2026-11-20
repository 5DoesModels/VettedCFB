"""Vetted CFB shared data foundation, Stage 0 (build FND-0.1).

One-way: this script READS the official engine data and the cached raw CFBD pulls and WRITES only to its own
output folder. Nothing in the official pipeline (model2.py, prep3.py, pred.py, the site) reads from here.

Record types (7): Player, Recruitment, School stint, Transfer event, Player-season, Outcome, Tag.
Reference tables (2): School, Coach-season.
Every row carries provenance: src (where it came from), st (verified | derived | reported | experimental | unknown),
and the build version. Missing, zero and not-applicable are stored as different values, never collapsed.

Usage: python3 build_foundation.py OUT_DIR
"""
import json, re, os, sys, glob, hashlib, collections, time

BV = 'FND-0.2'
ENG = '/home/claude/vetted-cfb/engine/data/'
RAW = '/root/cfbd_pull/'
GAMES = '/home/claude/foundation/raw_box/'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/foundation/build'
os.makedirs(OUT, exist_ok=True)
LOG = []
def note(*a):
    s = ' '.join(str(x) for x in a); LOG.append(s); print(s, flush=True)

def nm(s):  # normalized name: lower, no suffixes, letters only
    return re.sub(r'[^a-z]', '', re.sub(r'\b(jr|sr|ii|iii|iv|v)\b', '', (s or '').lower()))
def last(s):
    t = [x for x in re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?', '', (s or '').lower()).replace('.', ' ').split() if x]
    return re.sub(r'[^a-z]', '', t[-1]) if t else ''
def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]

# ---------------------------------------------------------------- inputs
t0 = time.time()
R = json.load(open(ENG + 'recruits.json'))                 # 90,121 recruitment records, 2002-2026 classes
POOL = {p['i']: p for p in json.load(open(ENG + 'pool2.json'))['players']}   # official linkage results (v1.28)
PORTAL = json.load(open(ENG + 'portal.json'))
DRAFT = json.load(open(ENG + 'draft.json'))
COACH = json.load(open(ENG + 'coaches.json'))
ROS = {y: json.load(open(f'{RAW}ros_{y}.json')) for y in range(2004, 2027)}
for _y, _rows in ROS.items():
    for _x in _rows: _x['season'] = _y          # roster 'year' is the class year (1-5), not the season
INPUTS = {f: sha(f) for f in [ENG + 'recruits.json', ENG + 'pool2.json', ENG + 'portal.json', ENG + 'draft.json',
                              ENG + 'coaches.json'] + [f'{RAW}ros_{y}.json' for y in range(2004, 2027)]}

# ---------------------------------------------------------------- reference: schools
roster_teams = {x['team'] for y in ROS for x in ROS[y]}
fbs_years = collections.defaultdict(set)
for c in COACH:
    for s in c['seasons']:
        fbs_years[s['school']].add(s['year'])
all_names = collections.Counter()
for r in R:
    if r['committedTo']: all_names[r['committedTo']] += 1
for p in PORTAL:
    all_names[p['origin']] += 1
    if p['destination']: all_names[p['destination']] += 1
for d in DRAFT: all_names[d['collegeTeam']] += 1
for t in roster_teams: all_names[t] += 1
schools = []
outside = sorted(n for n in all_names if n not in roster_teams)
alias_suspects = []
for a in outside:  # e.g. "Adams" vs "Adams State", "Ashland" vs "Ashland University": flag, never merge automatically
    for b in outside:
        if a != b and (b.startswith(a + ' ') or nm(b) == nm(a)):
            alias_suspects.append([a, b])
for n in sorted(all_names):
    schools.append(dict(name=n, in_roster_data=n in roster_teams,
                        fbs_seasons=sorted(fbs_years.get(n, [])),
                        st='verified' if n in roster_teams else 'reported', src='cfbd names across sources', bv=BV))
coach_seasons = []
for c in COACH:
    for s in c['seasons']:
        coach_seasons.append(dict(coach_id=c['id'], coach=f"{c['firstName']} {c['lastName']}", school=s['school'], year=s['year'],
                                  games=s['games'], wins=s['wins'], losses=s['losses'], src='cfbd coaches', st='verified', bv=BV))
note('schools', len(schools), 'outside roster coverage', len(outside), 'possible alias pairs', len(alias_suspects), '| coach-seasons', len(coach_seasons))

# ---------------------------------------------------------------- roster athletes and identity checks
ath = collections.defaultdict(list)     # athlete id -> roster rows
for y in sorted(ROS):
    for x in ROS[y]:
        ath[x['id']].append(x)
collision = {}                          # athlete id -> list of reasons (flag, never merge or split automatically)
coll_verdict = {}                       # athlete id -> likely_collision | unresolved | coverage_gap | same_season_overlap
team_seasons = collections.defaultdict(set)
for _y, _rows in ROS.items():
    for _x in _rows: team_seasons[_y].add(_x['team'])
for a, rows in ath.items():
    rows.sort(key=lambda x: x['season'])
    ys = sorted({x['season'] for x in rows})
    why = []
    gaps = [(p, q) for p, q in zip(ys, ys[1:]) if q - p >= 3]
    if gaps: why.append('gap of %d+ seasons (%s)' % (max(q - p for p, q in gaps), ', '.join(f'{p}->{q}' for p, q in gaps)))
    if ys[-1] - ys[0] + 1 > 7: why.append(f'span {ys[0]}-{ys[-1]} longer than 7 seasons')
    lasts = {last(x['firstName'] + ' ' + x['lastName']) for x in rows}
    if len(lasts) > 1: why.append('different last names under one id: ' + '/'.join(sorted(lasts)))
    by_year = collections.defaultdict(set)
    for x in rows: by_year[x['season']].add(x['team'])
    multi = [y for y, t in by_year.items() if len(t) > 1]
    if multi: why.append('on 2+ team rosters in the same season: ' + ','.join(map(str, sorted(multi))))
    if why:
        # Hometown, height and weight are stored once per athlete id and repeat on every row, so they cannot confirm identity.
        holes = all(t not in team_seasons.get(g, ()) for p_, q_ in gaps for g in range(p_ + 1, q_)
                    for t in {x['team'] for x in rows if x['season'] in (p_, q_)}) if gaps else False
        if len(lasts) > 1: verdict = 'likely_collision'                       # different last names under one id
        elif gaps and holes and ys[-1] - ys[0] + 1 <= 7: verdict = 'coverage_gap'   # the schools have no roster data for the missing seasons
        elif gaps or ys[-1] - ys[0] + 1 > 7: verdict = 'unresolved'          # absent from rosters that exist, or implausibly long career
        else: verdict = 'same_season_overlap'                                 # listed by two schools in one season (snapshot timing)
        collision[a] = why; coll_verdict[a] = verdict
note('roster athlete ids', len(ath), '| negative (CFBD placeholder-style) ids', sum(1 for a in ath if a.startswith('-')),
     '| ids flagged for possible collision', len(collision), collections.Counter(coll_verdict.values()))
BAD = {a for a, v in coll_verdict.items() if v in ('likely_collision', 'unresolved')}

# ---------------------------------------------------------------- recruit -> athlete links (ordered methods)
rid = {str(r['id']): i for i, r in enumerate(R)}
L = collections.defaultdict(dict)       # recruit idx -> athlete id -> method
for a, rows in ath.items():
    for x in rows:
        for k in x.get('recruitIds') or []:
            if str(k) in rid: L[rid[str(k)]][a] = 'roster_recruit_id'
for i, r in enumerate(R):
    if r.get('athleteId') and str(r['athleteId']) in ath:
        L[i].setdefault(str(r['athleteId']), 'cfbd_athlete_id')
name_team = collections.defaultdict(set)  # (name, team, year) -> athlete ids
for a, rows in ath.items():
    for x in rows: name_team[(nm(x['firstName'] + ' ' + x['lastName']), x['team'], x['season'])].add(a)
ambiguous = []
for i, r in enumerate(R):
    if L.get(i) or not r['committedTo']: continue
    cand = set()
    for y in (r['year'], r['year'] + 1):          # first season at the signing school: signing year or the next
        cand |= name_team.get((nm(r['name']), r['committedTo'], y), set())
    if len(cand) == 1: L[i][cand.pop()] = 'name_school_window'
    elif len(cand) > 1: ambiguous.append(dict(recruit=r['name'], year=r['year'], school=r['committedTo'], athlete_ids=sorted(cand)))
# Recruit with no roster link yet: a portal entry from his signing school (same name, within 6 seasons of signing)
# whose destination roster has exactly one player with that name links him there (name + school + season window, flagged).
pn = collections.defaultdict(list)
for e, p in enumerate(PORTAL): pn[(nm(p['firstName'] + ' ' + p['lastName']), p['origin'])].append(p)
via_portal = 0
for i, r in enumerate(R):
    if L.get(i) or not r['committedTo']: continue
    hits = set()
    for p in pn.get((nm(r['name']), r['committedTo']), ()):
        if r['year'] < p['season'] <= r['year'] + 6 and p['destination']:
            hits |= {a for y in (p['season'], p['season'] + 1) for a in name_team.get((nm(r['name']), p['destination'], y), ())}
    if len(hits) == 1: L[i][hits.pop()] = 'name_school_window'; via_portal += 1
note('recruits linked through a portal entry from the signing school', via_portal)
# Maintained identity-resolution file (JC decision 4): only entries with status "approved" are applied.
IRF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'identity_resolution.json')
manual = json.load(open(IRF))['cases'] if os.path.exists(IRF) else []
applied = 0
for c in manual:
    if c.get('status') != 'approved': continue
    i = rid.get(str(c.get('recruit_id')))
    if i is None: continue
    if c['decision'] == 'link' and c.get('athlete_id') in ath: L[i] = {c['athlete_id']: 'manual_approved'}; applied += 1
    elif c['decision'] == 'separate': L.pop(i, None); applied += 1
note('identity-resolution cases', len(manual), '| approved and applied', applied)
conflicts = []
for i, m in L.items():
    if len(m) > 1:
        conflicts.append(dict(recruit=R[i]['name'], year=R[i]['year'], school=R[i]['committedTo'], links=m))
note('recruits linked', len(L), 'of', len(R), '| ambiguous name+school', len(ambiguous), '| recruits linked to 2+ athlete ids', len(conflicts))

# ---------------------------------------------------------------- players (union of recruitments and athlete ids)
parent = {}
def find(k):
    parent.setdefault(k, k)
    while parent[k] != k:
        parent[k] = parent[parent[k]]; k = parent[k]
    return k
def union(a, b): parent[find(a)] = find(b)
held = []                                 # links not merged because names disagree or two recruitments would collide
NICK = {'mike': 'michael', 'matt': 'matthew', 'chris': 'christopher', 'nick': 'nicholas', 'josh': 'joshua', 'tony': 'anthony', 'joe': 'joseph',
        'will': 'william', 'bill': 'william', 'rob': 'robert', 'bob': 'robert', 'jim': 'james', 'jimmy': 'james', 'tom': 'thomas', 'dan': 'daniel',
        'danny': 'daniel', 'dave': 'david', 'alex': 'alexander', 'zach': 'zachary', 'zack': 'zachary', 'sam': 'samuel', 'ben': 'benjamin',
        'nate': 'nathan', 'kenny': 'kenneth', 'ken': 'kenneth', 'mitch': 'mitchell', 'ced': 'cedric', 'greg': 'gregory', 'pat': 'patrick', 'tim': 'timothy', 'jeff': 'jeffrey', 'steve': 'steven', 'stephen': 'steven', 'andy': 'andrew', 'drew': 'andrew', 'jake': 'jacob', 'cam': 'cameron', 'jon': 'jonathan', 'johnny': 'john', 'tj': 't', 'cj': 'c', 'aj': 'a', 'dj': 'd', 'jj': 'j'}
def first(s):
    t = re.sub(r'[^a-z ]', '', (s or '').lower()).split()
    return NICK.get(t[0], t[0]) if t else ''
def lparts(s):
    t = [x for x in re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?', '', (s or '').lower()).replace('.', ' ').split() if x]
    return set(re.sub(r'[^a-z]', '', p) for p in t[-1].split('-')) if t else set()
def same_person_name(rname, rows):
    """Same person if full names match, or last names match (hyphen parts count) and first names agree (nickname, short form or initials)."""
    if nm(rname) in {nm(x['firstName'] + ' ' + x['lastName']) for x in rows}: return True
    for x in rows:
        if lparts(rname) & lparts(x['firstName'] + ' ' + x['lastName']):
            f1, f2 = first(rname), first(x['firstName'])
            # same first name after nicknames, one a short form of the other (Cam/Cameron), or initials (AJ/Akii)
            if f1 and f2 and (f1 == f2 or (len(min(f1, f2, key=len)) >= 2 and max(f1, f2, key=len).startswith(min(f1, f2, key=len)))
                              or (len(min(f1, f2, key=len)) <= 2 and f1[0] == f2[0])): return True
    return False
STRENGTH = {'manual_approved': -1, 'roster_recruit_id': 0, 'cfbd_athlete_id': 1, 'name_school_window': 2}
comp_recs = collections.defaultdict(list)   # athlete id -> recruitments already joined to it
dup_records = []                            # the same recruitment listed twice by the source (same name, class, school, route)
for i, a, meth in sorted(((i, a, meth) for i, m in L.items() for a, meth in m.items()), key=lambda t: STRENGTH[t[2]]):
    find(('r', i)); find(('a', a))
    why = None
    if meth == 'manual_approved': why = None
    elif not same_person_name(R[i]['name'], ath[a]): why = 'recruit name does not match roster name'
    else:
        root = find(('a', a)); others = [j for j in comp_recs[root] if j != i]
        for j in others:   # a player can have a high school AND a JUCO/prep record, never two of the same route
            if (nm(R[j]['name']), R[j]['year'], R[j]['committedTo'], R[j]['recruitType']) == (nm(R[i]['name']), R[i]['year'], R[i]['committedTo'], R[i]['recruitType']):
                dup_records.append([R[j]['id'], R[i]['id'], R[i]['name'], R[i]['year'], R[i]['committedTo']]); continue   # exact duplicate record of one recruitment
            if R[j]['recruitType'] == R[i]['recruitType'] or nm(R[j]['name']) != nm(R[i]['name']) and first(R[j]['name'])[:3] != first(R[i]['name'])[:3]:
                why = f"athlete already joined to recruitment {R[j]['name']} ({R[j]['year']} {R[j]['recruitType']}, {R[j]['committedTo']})"; break
    if why:
        held.append(dict(recruit=R[i]['name'], year=R[i]['year'], route=R[i]['recruitType'], school=R[i]['committedTo'], athlete_id=a,
                         roster_names=sorted({x['firstName'] + ' ' + x['lastName'] for x in ath[a]}), method=meth, reason=why))
        continue
    ra, rr = find(('a', a)), find(('r', i))
    merged = comp_recs[ra] + comp_recs[rr] + [i]
    union(('r', i), ('a', a)); comp_recs[find(('a', a))] = sorted(set(merged))
note('exact duplicate recruiting records joined', len(dup_records)); note('recruit-athlete links held back', len(held), collections.Counter(h['reason'].split(' (')[0][:40] for h in held))
# Portal bridge (a name + school + season-window link, flagged): CFBD sometimes gives a player a new athlete id at his new school.
# Join the origin-roster athlete and the destination-roster athlete when a portal entry names both schools, each school's
# roster has exactly one player with that name in the matching season, and neither id fails the identity check.
bridges = []
for e, p in enumerate(PORTAL):
    if not p['destination'] or p['destination'] == p['origin']: continue
    n = nm(p['firstName'] + ' ' + p['lastName']); s_ = p['season']
    o = {a for y in (s_ - 1, s_) for a in name_team.get((n, p['origin'], y), ())}
    d = {a for y in (s_, s_ + 1) for a in name_team.get((n, p['destination'], y), ())}
    if len(o) == 1 and len(d) == 1:
        a1, a2 = o.pop(), d.pop()
        if a1 != a2 and a1 not in BAD and a2 not in BAD and find(('a', a1)) != find(('a', a2)):
            union(('a', a1), ('a', a2)); bridges.append(dict(portal_entry=e, name=p['firstName'] + ' ' + p['lastName'], origin_id=a1, destination_id=a2, origin=p['origin'], destination=p['destination'], season=s_))
note('portal bridges (new athlete id at new school, joined by name + portal entry)', len(bridges))
for i in range(len(R)): find(('r', i))
for a in ath: find(('a', a))
comp = collections.defaultdict(list)
for k in list(parent): comp[find(k)].append(k)
players, pid_of_r, pid_of_a = [], {}, {}
for n, (root, mem) in enumerate(sorted(comp.items(), key=lambda kv: str(kv[0]))):
    pid = f'P{n:06d}'
    recs = sorted(i for t, i in mem if t == 'r'); aids = sorted(a for t, a in mem if t == 'a')
    for i in recs: pid_of_r[i] = pid
    for a in aids: pid_of_a[a] = pid
    flags = []
    if len(recs) > 1: flags.append('multiple recruitment records (e.g. high school and JUCO) merged')
    if len(aids) > 1: flags.append('multiple roster athlete ids')
    if any(a in collision for a in aids): flags.append('roster id check: ' + '; '.join(sorted({coll_verdict[a] for a in aids if a in collision})))
    name = R[recs[0]]['name'] if recs else (ath[aids[0]][-1]['firstName'] + ' ' + ath[aids[0]][-1]['lastName'])
    methods = sorted({L[i][a] for i in recs for a in aids if a in L.get(i, {})})
    if recs and aids: status = 'linked' if methods and set(methods) <= {'roster_recruit_id', 'cfbd_athlete_id'} else 'linked_by_name_school'
    elif recs: status = 'recruitment_only'
    else: status = 'roster_only'
    if any(a in BAD for a in aids): status = 'identity_unresolved'
    players.append(dict(pid=pid, name=name, recruitments=[R[i]['id'] for i in recs], athlete_ids=aids, link_methods=methods,
                        identity_status=status, flags=flags, src='recruits+rosters', st='derived', bv=BV))
note('players', len(players), collections.Counter(p['identity_status'] for p in players))

# ---------------------------------------------------------------- recruitments
recruitments = []
for i, r in enumerate(R):
    recruitments.append(dict(recruit_id=r['id'], pid=pid_of_r[i], name=r['name'], class_year=r['year'], route=r['recruitType'],
                             stars=r['stars'] if r['stars'] is not None else None, rating=r['rating'], position=r['position'],
                             signed_with=r['committedTo'] or None, state=r['stateProvince'], city=r['city'],
                             src='cfbd recruiting (247Sports Composite)', st='reported', bv=BV))

# ---------------------------------------------------------------- player-seasons with participation (game-level cache if present)
SPEC = {'kickReturns', 'puntReturns', 'kicking', 'punting'}
POSCAT = {'QB': {'passing'}, 'RB': {'rushing', 'receiving'}, 'FB': {'rushing', 'receiving'}, 'WR': {'receiving'}, 'TE': {'receiving'},
          'DL': {'defensive', 'interceptions'}, 'DE': {'defensive', 'interceptions'}, 'DT': {'defensive', 'interceptions'}, 'NT': {'defensive', 'interceptions'},
          'LB': {'defensive', 'interceptions'}, 'OLB': {'defensive', 'interceptions'}, 'ILB': {'defensive', 'interceptions'},
          'DB': {'defensive', 'interceptions'}, 'CB': {'defensive', 'interceptions'}, 'S': {'defensive', 'interceptions'},
          'K': {'kicking'}, 'P': {'punting'}, 'PK': {'kicking'}}
DEF = {'DL', 'DE', 'DT', 'NT', 'LB', 'OLB', 'ILB', 'DB', 'CB', 'S'}
OL = {'OL', 'OT', 'OG', 'C', 'G', 'T', 'IOL', 'LS'}
gl = collections.defaultdict(lambda: collections.defaultdict(set))   # (athlete, team, season) -> game id -> categories
gfiles = sorted(glob.glob(GAMES + 'gp_*.json'))
games_seen = collections.defaultdict(set)
for f in gfiles:
    y = int(os.path.basename(f).split('_')[1])
    for g in json.load(open(f)):
        for t in g['teams']:
            games_seen[(t['team'], y)].add(g['id'])
            for c in t['categories']:
                for ty in c['types']:
                    for x in ty['athletes']:
                        gl[(x['id'], t['team'], y)][g['id']].add(c['name'])
note('game-level files', len(gfiles), '| athlete-team-seasons with game records', len(gl))

# ---------------------------------------------------------------- padded roster seasons (JC decision 3)
# A roster listing before the player's enrollment (before his first class year, or at his JUCO signing school before
# that JUCO class year) is hidden unless game records show he played that season. Hidden rows stay in the data.
recs_of = collections.defaultdict(list)
for i, r in enumerate(R): recs_of[pid_of_r[i]].append(r)
HIDDEN = {}
for a, rows in ath.items():
    rs = recs_of.get(pid_of_a[a])
    if not rs: continue
    y0 = min(r['year'] for r in rs)
    for x in rows:
        y, t = x['season'], x['team']
        why = None
        if y < y0: why = f'listed {y}, before his first signing class ({y0})'
        else:
            for r in rs:
                if r['recruitType'] in ('JUCO', 'PrepSchool') and r['committedTo'] == t and y < r['year']:
                    why = f'listed at {t} in {y}, before his {r["recruitType"]} signing class ({r["year"]})'
        if why and not gl.get((a, t, y)): HIDDEN[(a, t, y)] = why
drafted_in = {}   # pid -> draft year (official recruit linkage, or draft collegeAthleteId = roster id)
for i, r in enumerate(R):
    q = POOL.get(i)
    if q and q.get('draftYear'): drafted_in[pid_of_r[i]] = q['draftYear']
for d in DRAFT:
    a = str(d.get('collegeAthleteId') or '')
    if a in pid_of_a and any(nm(d['name']) == nm(x['firstName'] + ' ' + x['lastName']) or (last(d['name']) == last(x['firstName'] + ' ' + x['lastName']) and first(d['name'])[:3] == first(x['firstName'])[:3]) for x in ath[a]):
        drafted_in.setdefault(pid_of_a[a], d['year'])
post_draft = 0
for a, rows in ath.items():
    dy_ = drafted_in.get(pid_of_a[a])
    if not dy_: continue
    for x in rows:
        if x['season'] >= dy_ and (a, x['team'], x['season']) not in HIDDEN and not gl.get((a, x['team'], x['season'])):
            HIDDEN[(a, x['team'], x['season'])] = f"listed in {x['season']}, after he was drafted in {dy_} (roster error)"; post_draft += 1
note('padded roster seasons hidden (no game record that season)', len(HIDDEN), '| of which after the draft', post_draft)
# ---------------------------------------------------------------- school stints (consecutive roster seasons at one school)
stints = []
for a, rows in ath.items():
    seq = sorted({(x['season'], x['team']) for x in rows if (a, x['team'], x['season']) not in HIDDEN})
    cur = None
    for y, t in seq:
        if cur and cur['school'] == t and y - cur['last'] <= 2:
            cur['last'] = y; cur['seasons'].append(y)
        else:
            if cur: stints.append(cur)
            cur = dict(pid=pid_of_a[a], athlete_id=a, school=t, first=y, last=y, seasons=[y])
    if cur: stints.append(cur)
hidden_by_a = collections.defaultdict(list)
for (a, t, y), why in HIDDEN.items(): hidden_by_a[a].append(dict(school=t, season=y, reason=why))
for a, h in hidden_by_a.items():
    stints.append(dict(pid=pid_of_a[a], athlete_id=a, school=h[0]['school'], first=min(x['season'] for x in h), last=max(x['season'] for x in h),
                       seasons=sorted(x['season'] for x in h), hidden=True, hidden_reason='; '.join(x['reason'] for x in h)))
for s in stints:
    s.setdefault('hidden', False)
    s.update(src='cfbd rosters', st='unknown' if s['athlete_id'] in BAD else 'verified', bv=BV,
             note='roster listing only; does not show games played')

# ---------------------------------------------------------------- transfer events (one unit: a school movement or a portal entry)
moves = []        # roster movements between consecutive seasons, different school, per player (all his athlete ids)
pid_ids = collections.defaultdict(list)
for a in ath: pid_ids[pid_of_a[a]].append(a)
for pid, ids in pid_ids.items():
    rows = [x for a in ids for x in ath[a] if (a, x['team'], x['season']) not in HIDDEN]
    seq = sorted({(x['season'], x['team'], x['id']) for x in rows})
    for (y1, t1, a1), (y2, t2, a2) in zip(seq, seq[1:]):
        if t1 != t2 and y2 > y1:
            moves.append(dict(pid=pid, athlete_id=a1, to_athlete_id=a2, bad=a1 in BAD or a2 in BAD, bridged=a1 != a2, from_season=y1, origin=t1, to_season=y2, destination=t2,
                              name=nm(ath[a1][0]['firstName'] + ' ' + ath[a1][0]['lastName'])))
pidx = collections.defaultdict(list)
for e, p in enumerate(PORTAL):
    pidx[(nm(p['firstName'] + ' ' + p['lastName']), p['origin'])].append(e)
plast = collections.defaultdict(list)
for e, p in enumerate(PORTAL): plast[(last(p['firstName'] + ' ' + p['lastName']), p['origin'])].append(e)
used = {}
events = []
for m in moves:
    gap = m['to_season'] - m['from_season']
    cand = [e for e in pidx.get((m['name'], m['origin']), []) if PORTAL[e]['season'] in (m['to_season'], m['to_season'] - 1, m['from_season'], m['from_season'] + 1) and e not in used]
    same = [e for e in cand if PORTAL[e]['destination'] == m['destination']]
    ev = dict(pid=m['pid'], athlete_id=m['athlete_id'], origin=m['origin'], roster_destination=m['destination'], portal_destination=None,
              last_season_at_origin=m['from_season'], first_season_at_destination=m['to_season'], portal_entry=None, bv=BV)
    dy = drafted_in.get(m['pid'])
    if dy and m['to_season'] >= dy:
        ev.update(category='Unknown/unresolved', sub='roster lists the player after he was drafted (roster error)', src='cfbd rosters', st='unknown')
    elif m['bad']:
        ev.update(category='Unknown/unresolved', sub='roster id fails the identity check (' + coll_verdict.get(m['athlete_id'], coll_verdict.get(m['to_athlete_id'], '')) + ')', src='cfbd rosters', st='unknown')
    elif same:
        e = same[0]; used[e] = 1
        ev.update(category='Confirmed', sub='portal entry and destination roster agree' + (' (new athlete id at destination, joined by name)' if m['bridged'] else ''), portal_entry=e, portal_destination=PORTAL[e]['destination'], src='cfbd portal + rosters', st='verified')
    elif cand:
        e = cand[0]; used[e] = 1
        if PORTAL[e]['destination']:   # conflict: keep both destinations, never overwrite; not confirmed
            ev.update(category='Reported', sub='conflict: portal destination differs from the roster destination', portal_entry=e, portal_destination=PORTAL[e]['destination'], src='cfbd portal + rosters', st='reported')
        else:
            ev.update(category='Confirmed', sub='portal entry from origin (no destination listed); same roster id shows the move', portal_entry=e, src='cfbd portal + rosters', st='verified')
    else:
        ev.update(category='Inferred school movement', sub='pre-2021 (before portal data)' if m['to_season'] <= 2020 else '2021+ (no matching portal entry)',
                  src='cfbd rosters', st='derived')
    if gap >= 3 and not m['bad']: ev['flag'] = f'{gap}-season gap; the schools have no roster data for the missing seasons'
    if ev['category'] == 'Inferred school movement' and m['to_season'] >= 2021:
        ln = last(ath[m['athlete_id']][0]['firstName'] + ' ' + ath[m['athlete_id']][0]['lastName'])
        if any(PORTAL[e]['season'] in (m['to_season'], m['to_season'] - 1) for e in plast.get((ln, m['origin']), ())):
            ev['sub'] = '2021+ (portal entry from origin with same last name, different first name: possible name variant)'
    events.append(ev)
# portal entries not tied to a roster movement
ros_at = collections.defaultdict(set)    # (name, team) -> seasons
for a, rows in ath.items():
    for x in rows: ros_at[(nm(x['firstName'] + ' ' + x['lastName']), x['team'])].add(x['season'])
entry_class = collections.Counter()
for e, p in enumerate(PORTAL):
    if e in used: entry_class['tied to a roster movement (Confirmed, or Reported when the two destinations conflict)'] += 1; continue
    n = nm(p['firstName'] + ' ' + p['lastName']); s = p['season']
    back = any(y in ros_at.get((n, p['origin']), ()) for y in (s, s + 1))
    if p['destination'] and p['destination'] == p['origin']:
        entry_class['destination is the origin school (withdrew or returned): not a transfer'] += 1; continue
    if not p['destination'] and back:
        entry_class['no destination; back on origin roster next season: not a transfer'] += 1; continue
    ev = dict(pid=None, athlete_id=None, origin=p['origin'], portal_destination=p['destination'] or None, roster_destination=None, portal_entry=e, portal_season=s, bv=BV)
    cands = [a for a in {a for y in (s - 1, s) for a in name_team.get((n, p['origin'], y), ())}]
    if len(cands) == 1: ev.update(pid=pid_of_a[cands[0]], athlete_id=cands[0])
    dest_ids = {a for y in (s, s + 1) for a in name_team.get((n, p['destination'], y), ())} if p['destination'] else set()
    if len(dest_ids) == 1:
        a2 = next(iter(dest_ids))
        if not ev['pid'] and a2 not in BAD: ev.update(pid=pid_of_a[a2], athlete_id=a2)
        ev.update(category='Reported', sub='destination roster shows a player with this name; movement not established (no origin-roster record on the same id)', roster_destination_observed=p['destination'], src='cfbd portal + rosters (name)', st='reported')
        entry_class['destination roster shows the name, movement not established (Reported event)'] += 1
    elif len(dest_ids) > 1:
        ev.update(category='Reported', sub='destination roster has 2+ players with this name', src='cfbd portal', st='reported')
        entry_class['destination listed, no roster confirmation (Reported event)'] += 1
    elif p['destination']:
        ev.update(category='Reported', sub='portal lists a destination; not confirmed on a roster' + ('' if p['destination'] in roster_teams else ' (destination outside our roster coverage)'),
                  src='cfbd portal', st='reported')
        entry_class['destination listed, no roster confirmation (Reported event)'] += 1
    else:
        ev.update(category='Unknown/unresolved', sub='portal entry, no destination and not found at origin next season', src='cfbd portal', st='unknown')
        entry_class['no destination, outcome unknown (Unknown/unresolved event)'] += 1
    events.append(ev)
ecat = collections.Counter((e['category'], e['sub']) for e in events)
note('transfer events', len(events)); [note('  ', k, v) for k, v in sorted(ecat.items())]
note('portal entries', len(PORTAL)); [note('  ', k, v) for k, v in sorted(entry_class.items())]
assert sum(entry_class.values()) == len(PORTAL)
assert sum(1 for e in events if e.get('portal_entry') is not None) + entry_class['destination is the origin school (withdrew or returned): not a transfer'] + entry_class['no destination; back on origin roster next season: not a transfer'] == len(PORTAL)

pseasons = []
for a, rows in ath.items():
    for x in rows:
        y, t, pos = x['season'], x['team'], x.get('position')
        row = dict(pid=pid_of_a[a], athlete_id=a, season=y, school=t, roster_position=pos, bv=BV, src='cfbd rosters + game-level player stats')
        if y < 2009 or y > 2025 or (t, y) not in games_seen:
            row.update(games_any='not_available', games_position='not_available', games_special_only='not_available', st='unknown')
        else:
            G = gl.get((a, t, y), {})
            row['games_any'] = len(G)
            qual = POSCAT.get(pos, set())   # kickers and punters: kicking/punting is their position statistic, not special-teams-only
            row['games_special_only'] = sum(1 for c in G.values() if c <= SPEC and not (c & qual))
            row['games_fumble_only'] = sum(1 for c in G.values() if c == {'fumbles'})
            row['games_other_only'] = sum(1 for c in G.values() if c and not (c & qual) and not c <= SPEC and c != {'fumbles'})
            if pos in DEF and 2016 <= y < 2019:   # retained for research only (JC decision 1); not comparable with 2019+
                row['games_position_research'] = sum(1 for c in G.values() if c & POSCAT[pos]); row['research_note'] = 'defensive game data 2016-2018: research only'
            if pos in OL: row['games_position'] = 'not_applicable'
            elif pos in DEF and y < 2019: row['games_position'] = 'not_available'      # D6: defensive measure 2019 onward only
            elif pos in POSCAT: row['games_position'] = sum(1 for c in G.values() if c & POSCAT[pos])
            else: row['games_position'] = 'unknown_position'
            row['st'] = 'derived'
            if not G: row['no_record_note'] = 'on roster; no stat recorded in any game'
        if (a, t, y) in HIDDEN: row.update(hidden=True, hidden_reason=HIDDEN[(a, t, y)])
        pseasons.append(row)
note('player-seasons', len(pseasons))

# ---------------------------------------------------------------- outcomes (draft linkage from the official v1.28 pipeline)
outcomes = []
draft_conflicts = []
linked_picks = set()
on2026 = {x['id'] for x in ROS[2026]}
for i, r in enumerate(R):
    p = POOL.get(i)
    pid = pid_of_r[i]
    if p and p.get('draftYear'):
        outcomes.append(dict(pid=pid, recruit_id=r['id'], type='drafted', year=p['draftYear'], round=p['round'], overall=p['overall'],
                             college_team=p['draftTeam'], src='official draft linkage v1.28 (link.py + linkfix.json)', st='derived', bv=BV))
        linked_picks.add((p['draftYear'], p['overall']))
pl_by = {p['pid']: p for p in players}
for d in DRAFT:
    if (d['year'], d['overall']) in linked_picks: continue
    a = str(d.get('collegeAthleteId') or '')
    if a in pid_of_a and pid_of_a[a] in {o['pid'] for o in outcomes}:
        draft_conflicts.append(dict(pick=[d['year'], d['overall']], name=d['name'], college=d['collegeTeam'], pid=pid_of_a[a], reason='player already has a draft outcome; athlete id shared by two people?')); continue
    if a in pid_of_a and any(nm(d['name']) == nm(x['firstName'] + ' ' + x['lastName']) or (last(d['name']) == last(x['firstName'] + ' ' + x['lastName']) and first(d['name'])[:3] == first(x['firstName'])[:3]) for x in ath[a]):
        outcomes.append(dict(pid=pid_of_a[a], type='drafted', year=d['year'], round=d['round'], overall=d['overall'], college_team=d['collegeTeam'],
                             src='cfbd draft collegeAthleteId = roster id, full name checked', st='derived', bv=BV, note='not used by official grades'))
        linked_picks.add((d['year'], d['overall']))
for d in DRAFT:
    if (d['year'], d['overall']) in linked_picks: continue
    cand = {a for y in range(d['year'] - 6, d['year']) for a in name_team.get((nm(d['name']), d['collegeTeam'], y), ())}
    if len(cand) == 1 and pid_of_a[next(iter(cand))] in {o['pid'] for o in outcomes}:
        draft_conflicts.append(dict(pick=[d['year'], d['overall']], name=d['name'], college=d['collegeTeam'], pid=pid_of_a[next(iter(cand))], reason='name match lands on a player already drafted')); continue
    if len(cand) == 1:
        a = cand.pop()
        outcomes.append(dict(pid=pid_of_a[a], type='drafted', year=d['year'], round=d['round'], overall=d['overall'], college_team=d['collegeTeam'],
                             src='name + college roster match (pre-2019 rosters often use placeholder ids)', st='derived', bv=BV, note='not used by official grades; flagged'))
        linked_picks.add((d['year'], d['overall']))
after_draft = []
dmap = {}
for o in outcomes:
    if o['type'] == 'drafted': dmap.setdefault(o['pid'], o['year'])
for pid, dy_ in dmap.items():
    for a in [a for a in ath if pid_of_a.get(a) == pid] if False else pid_ids.get(pid, []):
        late = sorted({x['season'] for x in ath[a] if x['season'] >= dy_})
        if late: after_draft.append(dict(pid=pid, athlete_id=a, draft_year=dy_, roster_seasons_after=late))
unlinked_picks = [dict(year=d['year'], overall=d['overall'], name=d['name'], college=d['collegeTeam']) for d in DRAFT if (d['year'], d['overall']) not in linked_picks]
drafted_p = {o['pid'] for o in outcomes}
for p in players:
    if p['pid'] in drafted_p: continue
    aids = p['athlete_ids']
    if any(a in on2026 for a in aids):
        outcomes.append(dict(pid=p['pid'], type='still_in_college', as_of=2026, src='2026 roster', st='derived', bv=BV))
    elif aids:
        outcomes.append(dict(pid=p['pid'], type='no_linked_draft_record_through_2026', last_roster_season=max(x['season'] for a in aids for x in ath[a]),
                             src='rosters + draft 2003-2026', st='derived', bv=BV))
    else:
        outcomes.append(dict(pid=p['pid'], type='unknown', reason='no roster record found', st='unknown', bv=BV))
note('outcomes', collections.Counter(o['type'] for o in outcomes), '| draft picks not tied to any player', len(unlinked_picks))

# ---------------------------------------------------------------- tags (player-level vs player-school)
tags = []
moved_pids = {e['pid'] for e in events if e['category'] in ('Confirmed', 'Reported') and e['pid'] and e.get('portal_entry') is not None}
for pid in sorted(moved_pids):
    tags.append(dict(scope='player', pid=pid, tag='transferred', rule='at least one Confirmed or Reported transfer event tied to a portal entry (2021+)', st='derived', bv=BV))
for rr in recruitments:
    if rr['route'] == 'JUCO':
        tags.append(dict(scope='player', pid=rr['pid'], tag='juco_route', rule='a recruitment record with route JUCO', st='reported', bv=BV))
# Great Fit is a player-school tag: key = (pid, school, position group). Schema only; inactive until JC approves the report.
TAG_SCHEMA = dict(player=['transferred', 'juco_route'], player_school=dict(great_fit=dict(key=['pid', 'school', 'position_group'], active=False)))
note('tags', collections.Counter(t['tag'] for t in tags))

# ---------------------------------------------------------------- write
def dump(name, obj):
    json.dump(obj, open(os.path.join(OUT, name + '.json'), 'w'), separators=(',', ':'))
for name, obj in [('players', players), ('recruitments', recruitments), ('school_stints', stints), ('transfer_events', events),
                  ('player_seasons', pseasons), ('outcomes', outcomes), ('tags', tags), ('schools', schools), ('coach_seasons', coach_seasons)]:
    dump(name, obj)
dump('exceptions', dict(identity_collisions={a: dict(reasons=collision[a], verdict=coll_verdict[a]) for a in sorted(collision)}, ambiguous_name_school=ambiguous,
                        recruit_multi_athlete=conflicts, held_name_mismatch=held, portal_bridges=bridges, duplicate_recruiting_records=dup_records, draft_conflicts=draft_conflicts, roster_rows_after_draft=after_draft, unlinked_draft_picks=unlinked_picks,
                        school_alias_suspects=alias_suspects, schools_outside_roster_coverage=outside))
manifest = dict(build=BV, built=time.strftime('%Y-%m-%d %H:%M'), seconds=round(time.time() - t0), inputs=INPUTS,
                game_files=len(gfiles), record_types=['Player', 'Recruitment', 'School stint', 'Transfer event', 'Player-season', 'Outcome', 'Tag'],
                reference_tables=['School', 'Coach-season'], tag_schema=TAG_SCHEMA,
                counts=dict(players=len(players), recruitments=len(recruitments), school_stints=len(stints), transfer_events=len(events),
                            player_seasons=len(pseasons), outcomes=len(outcomes), tags=len(tags), schools=len(schools), coach_seasons=len(coach_seasons)),
                transfer_events_by_category={f'{k[0]} | {k[1]}': v for k, v in sorted(ecat.items())},
                portal_entries_by_class=dict(entry_class), log=LOG)
dump('manifest', manifest)
print('BUILD OK', OUT)
