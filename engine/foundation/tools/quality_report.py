import json,collections
B='build/FND-0.1/'
L=lambda n:json.load(open(B+n+'.json'))
P=L('players'); RC=L('recruitments'); EV=L('transfer_events'); OC=L('outcomes'); X=L('exceptions'); M=L('manifest'); PS=L('player_seasons')
PI={p['pid']:p for p in P}
# linkage coverage by class group (each recruitment)
grp=lambda y:'2002-08' if y<=2008 else '2009-14' if y<=2014 else '2015-18' if y<=2018 else '2019-21' if y<=2021 else '2022-26'
cov=collections.defaultdict(collections.Counter)
for r in RC:
    p=PI[r['pid']]; st=p['identity_status']
    k='id link' if st=='linked' else 'name+school link' if st=='linked_by_name_school' else 'identity unresolved' if st=='identity_unresolved' else 'no roster record'
    cov[grp(r['class_year'])][k]+=1
covp={g:{k:f"{100*v/sum(c.values()):.0f}%" for k,v in c.items()}|{'n':sum(c.values())} for g,c in sorted(cov.items())}
# transfers by category: events, distinct players
cat=collections.defaultdict(lambda:[0,set()])
for e in EV:
    c=cat[e['category']]; c[0]+=1
    if e['pid']: c[1].add(e['pid'])
tr={k:dict(events=v[0],players=len(v[1])) for k,v in cat.items()}
mov=sum(1 for e in EV if e.get('first_season_at_destination'))
ent=sum(1 for e in EV if e.get('portal_entry') is not None)
both=sum(1 for e in EV if e.get('first_season_at_destination') and e.get('portal_entry') is not None)
# participation availability
pa=collections.Counter()
for s in PS:
    pa[('games_any', 'not_available' if s['games_any']=='not_available' else 'measured')]+=1
    pa[('games_position', s['games_position'] if isinstance(s['games_position'],str) else 'measured')]+=1
rep=dict(build=M['build'],counts=M['counts'],record_types=M['record_types'],reference_tables=M['reference_tables'],
  identity=collections.Counter(p['identity_status'] for p in P),coverage_by_class=covp,
  exceptions={k:len(v) for k,v in X.items()},
  collision_verdicts=collections.Counter(v['verdict'] for v in X['identity_collisions'].values()),
  transfers=tr, transfer_units=dict(events=len(EV),with_roster_movement=mov,with_portal_entry=ent,with_both=both,portal_entries_total=18906,portal_entries_by_class=M['portal_entries_by_class']),
  transfer_subcategories=M['transfer_events_by_category'],
  outcomes=collections.Counter(o['type'] for o in OC), outcome_sources=collections.Counter(o.get('src','') for o in OC if o['type']=='drafted'),
  participation={' | '.join(k):v for k,v in pa.items()})
json.dump(rep,open('quality_report.json','w'),indent=1,default=list)
print(json.dumps(rep,indent=1,default=list)[:6000])
