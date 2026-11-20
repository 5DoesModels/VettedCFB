import json,collections
B='build/FND-0.2/'
P={p['pid']:p for p in json.load(open(B+'players.json'))}
RC=collections.defaultdict(list)
for r in json.load(open(B+'recruitments.json')): RC[r['pid']].append(r)
O=[o for o in json.load(open(B+'outcomes.json')) if o['type']=='drafted' and o['src'].startswith('official')]
seen=set();rows=[];changed=[]
for o in O:
    if o['pid'] in seen: continue
    seen.add(o['pid']); rs=RC[o['pid']]
    hs=[r for r in rs if r['route']=='HighSchool']
    base=(hs or sorted(rs,key=lambda r:r['class_year']))[0]
    st=base['stars'] or 0
    if len(rs)>1 and len({(r['stars'] or 0) for r in rs})>1: changed.append((P[o['pid']]['name'],[(r['route'],r['stars']) for r in rs]))
    rows.append(dict(name=P[o['pid']]['name'],stars=st,cls=base['class_year'],route=base['route'],rnd=o['round'],pick=o['overall'],dy=o['year']))
D=[r for r in rows if r['stars'] in (2,3)]
era=lambda y:'2002-2009' if y<=2009 else '2010-2014' if y<=2014 else '2015-2018' if y<=2018 else '2019-2022'
out=dict(total=len(D),by_stars=collections.Counter(r['stars'] for r in D),by_class=collections.Counter(era(r['cls']) for r in D),
 by_round=dict(sorted(collections.Counter(r['rnd'] for r in D).items())),by_route=collections.Counter(r['route'] for r in D),
 stars_x_round={s:dict(sorted(collections.Counter(r['rnd'] for r in D if r['stars']==s).items())) for s in (2,3)},
 stars_x_class={s:dict(sorted(collections.Counter(era(r['cls']) for r in D if r['stars']==s).items())) for s in (2,3)},
 excluded_unranked=sum(1 for r in rows if r['stars']==0),multi_record_players_with_different_stars=len(changed),changed_examples=changed[:6],
 first_rounders=sorted([f"{r['name']} ({r['stars']}★ {r['cls']}, {r['dy']} #{r['pick']})" for r in D if r['rnd']==1])[:12])
json.dump(out,open('diamond_breakdown.json','w'),indent=1,default=dict);print(json.dumps(out,indent=1,default=dict))
