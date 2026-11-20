import json,collections,sys
B='build/FND-0.2/'
L=lambda n:json.load(open(B+n+'.json'))
P={p['pid']:p for p in L('players')}; RC=L('recruitments'); ST=L('school_stints'); EV=L('transfer_events'); OC=L('outcomes'); PS=L('player_seasons')
by=lambda rows:collections.defaultdict(list,{})
def idx(rows):
    d=collections.defaultdict(list)
    for r in rows:
        if r.get('pid'): d[r['pid']].append(r)
    return d
RCi,STi,EVi,OCi,PSi=idx(RC),idx(ST),idx(EV),idx(OC),idx(PS)
names=collections.defaultdict(list)
for p in P.values(): names[p['name'].lower()].append(p['pid'])
for r in RC: names[r['name'].lower()].append(r['pid'])
def show(name,cls=None):
    pids=sorted(set(names.get(name.lower(),[])))
    if cls: pids=[x for x in pids if any(r['class_year']==cls for r in RCi[x])] or pids
    out=[]
    for pid in pids:
        p=P[pid]; s=[f"\n## {p['name']} [{pid}] identity: {p['identity_status']} {p['link_methods']} {p['flags']}"]
        for r in RCi[pid]: s.append(f"  recruit: {r['class_year']} {r['route']} {r['stars']}* {r['rating']} {r['position']} {r['city']}, {r['state']} -> {r['signed_with']}")
        for t in sorted(STi[pid],key=lambda t:t['first']): s.append(f"  stint: {t['school']} {t['first']}-{t['last']} ({','.join(map(str,t['seasons']))}) [{t['st']}]"+(f" HIDDEN: {t['hidden_reason']}" if t.get('hidden') else ''))
        for e in EVi[pid]: s.append(f"  event: {e['category']} | {e['sub']} | {e['origin']} -> {e.get('portal_destination')}|roster {e.get('roster_destination')} ({e.get('last_season_at_origin','')}->{e.get('first_season_at_destination',e.get('portal_season',''))}){' FLAG '+e['flag'] if e.get('flag') else ''}")
        for ps in sorted(PSi[pid],key=lambda x:x['season']): s.append(f"  season {ps['season']} {ps['school']} {ps['roster_position']}: any {ps['games_any']}, position {ps['games_position']}, ST-only {ps['games_special_only']}")
        for o in OCi[pid]: s.append(f"  outcome: {o['type']} {o.get('year','')} R{o.get('round','')} #{o.get('overall','')} {o.get('college_team','')} [{o.get('src','')}]")
        out.append('\n'.join(s))
    return '\n'.join(out) if out else f'\n## {name}: NOT FOUND'
if __name__=='__main__':
    for a in sys.argv[1:]:
        n,_,c=a.partition('@'); print(show(n,int(c) if c else None))
