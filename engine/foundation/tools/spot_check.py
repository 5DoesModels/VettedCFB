import json,collections,random,re
B='build/FND-0.1/'
R=json.load(open('/home/claude/vetted-cfb/engine/data/recruits.json')); RI={r['id']:r for r in R}
P=json.load(open(B+'players.json'))
ros={}
for y in range(2004,2027):
    for x in json.load(open(f'/root/cfbd_pull/ros_{y}.json')): x['season']=y; ros.setdefault(x['id'],[]).append(x)
cn=lambda s:re.sub(r'[^a-z]','',(s or '').lower())
GRP={'QB':'QB','PRO':'QB','DUAL':'QB','RB':'RB','APB':'RB','FB':'RB','WR':'WR','TE':'TE','OT':'OL','OG':'OL','OC':'OL','IOL':'OL','OL':'OL','C':'OL','G':'OL','T':'OL',
     'DT':'DL','DL':'DL','SDE':'DL','WDE':'DL','DE':'DL','NT':'DL','EDGE':'DL','ILB':'LB','OLB':'LB','LB':'LB','CB':'DB','S':'DB','DB':'DB','ATH':'ATH','K':'K','P':'K','PK':'K','LS':'OL'}
def ev(p):
    r=RI[p['recruitments'][0]]; rows=[x for a in p['athlete_ids'] for x in ros[a]]
    x=rows[0]; e={}
    hs,hc=(x.get('homeState') or '').upper(),cn(x.get('homeCity'))
    if not hs: e['home']='missing'
    elif hs!=(r['stateProvince'] or '').upper(): e['home']='state differs'
    elif hc and hc==cn(r['city']): e['home']='city+state match'
    else: e['home']='state match, city differs'
    rp,xp=GRP.get(r['position']),GRP.get(x.get('position'))
    e['pos']='na' if not rp or not xp or 'ATH' in (rp,xp) else 'match' if rp==xp else 'differs'
    e['ht']=None if not (r.get('height') and x.get('height')) else abs(r['height']-x['height'])
    return r,rows,e
def verdict(e):
    if e['home']=='city+state match': return 'correct'
    if e['home']=='state differs': return 'incorrect'
    if e['home']=='state match, city differs' and e['pos']!='differs': return 'correct'   # nearby town naming; position agrees
    return 'ambiguous'
ns=[p for p in P if p['identity_status']=='linked_by_name_school' or (p['link_methods']==['name_school_window'])]
print('players linked only by name+school',len(ns))
full=collections.Counter(); byc=collections.defaultdict(collections.Counter)
for p in ns:
    r,rows,e=ev(p); v=verdict(e); full[v]+=1; byc[('2009-14' if r['year']<=2014 else '2015-18' if r['year']<=2018 else '2019-26' if r['year']>=2019 else '2002-08')][v]+=1
print('ALL name+school links by automatic evidence:',dict(full)); [print('  ',k,dict(v)) for k,v in sorted(byc.items())]
# representative 100: 40 from 2015-18, 25 from 2009-14, 20 from 2019-26, 15 risky (common last names / position differs)
random.seed(20261120)
lastc=collections.Counter(RI[p['recruitments'][0]]['name'].split()[-1].lower() for p in ns)
def grp(p): y=RI[p['recruitments'][0]]['year']; return '2015-18' if 2015<=y<=2018 else '2009-14' if 2009<=y<=2014 else '2019-26' if y>=2019 else 'other'
risky=[p for p in ns if lastc[RI[p['recruitments'][0]]['name'].split()[-1].lower()]>=40 or ev(p)[2]['pos']=='differs']
S=random.sample([p for p in ns if grp(p)=='2015-18'],40)+random.sample([p for p in ns if grp(p)=='2009-14'],25)+random.sample([p for p in ns if grp(p)=='2019-26'],20)
S+=random.sample([p for p in risky if p not in S],15)
out=[]
for k,p in enumerate(S):
    r,rows,e=ev(p); x=rows[0]
    out.append(dict(n=k+1,pid=p['pid'],group=grp(p) if k<85 else 'risky ('+grp(p)+')',recruit=f"{r['name']} · {r['year']} {r['recruitType']} · {r['position']} · {r['city']}, {r['stateProvince']} · {r.get('height')}in · signed {r['committedTo']}",
      roster=f"{x['firstName']} {x['lastName']} · {x.get('position')} · {x.get('homeCity')}, {x.get('homeState')} · {x.get('height')}in · "+', '.join(sorted({z['team']+' '+str(z['season']) for z in rows})),
      evidence=e,auto=verdict(e)))
json.dump(out,open('spot100.json','w'),indent=1)
print('sample verdicts',collections.Counter(o['auto'] for o in out), collections.Counter((o['group'][:5],o['auto']) for o in out))
for o in out:
    if o['auto']!='correct': print(o['n'],o['group'],'|',o['recruit'],'||',o['roster'],o['evidence'])
