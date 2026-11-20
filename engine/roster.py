import json, collections, sys
E=sys.argv[1]; O='/home/claude/concept/'
X=json.load(open(E+'/data/pool2.json')); P=X['players']
RAW=json.load(open(E+'/data/recruits.json'))
sys.path.insert(0,'/home/claude/concept')
rid={}
for x in RAW: rid[(x['name'],x['year'],x.get('committedTo'))]=str(x['id'])
# roster seasons: by athlete id and by recruit id
seasons_by_ath=collections.defaultdict(set); seasons_by_rec=collections.defaultdict(set)
for y in range(2009,2027):
    for r in json.load(open(f'/root/cfbd_pull/ros_{y}.json')):
        seasons_by_ath[str(r['id'])].add((y,r['team']))
        for q in r.get('recruitIds') or []: seasons_by_rec[str(q)].add((y,r['team']))
coaches=json.load(open(E+'/data/coaches.json')); CONF={}
for c in coaches:
    for s in c['seasons']: CONF[(s['school'],s['year'])]=s.get('conference')
P4={'SEC','Big Ten','Big 12','ACC','Pac-12'}
G=['QB','RB','WR','TE','OL','DL','EDGE','LB','DB']
rows=[]
for r in P:
    if not (2009<=r['year']<=2020) or r['recruitType']!='HighSchool': continue
    ss=seasons_by_ath.get(str(r.get('athleteId')),set())|seasons_by_rec.get(rid.get((r['name'],r['year'],r['committedTo'])),set())
    if not ss: continue
    at=len({y for y,t in ss if t==r['committedTo'] and r['year']<=y<=r['year']+5})
    p4=CONF.get((r['committedTo'],r['year'])) in P4
    rows.append((r['committedTo'],r['pg'],at,bool(r['draftYear']),p4,r['tier'] in ('First round','Top 10 pick')))
print('linked signees',len(rows),'of',sum(1 for r in P if 2009<=r['year']<=2020 and r['recruitType']=='HighSchool'))
print('seasons at school distribution',collections.Counter(min(at,5) for _,_,at,_,_,_ in rows))
agg=collections.defaultdict(lambda:[0,0,0,0,0])   # stayed3 n, drafted ; left<3 n, drafted ; total seasons
for s,g,at,d,p4,r1 in rows:
    for key in [(s,g),(s,'ALL')]+([('P4',g),('P4','ALL')] if p4 else [])+[('ALL',g),('ALL','ALL')]:
        x=agg[key]
        if at>=3: x[0]+=1; x[1]+=d
        else: x[2]+=1; x[3]+=d
        x[4]+=at
out=[[a,b]+v for (a,b),v in agg.items()]
json.dump(out,open(O+'stay3.json','w'),separators=(',',':'))
def show(k):
    v=agg[k]; print(k,'stayed3',v[0],v[1],f"{100*v[1]/max(1,v[0]):.1f}%",'left',v[2],v[3],f"{100*v[3]/max(1,v[2]):.1f}%")
for k in [('ALL','ALL'),('P4','ALL'),('P4','WR'),('LSU','WR'),('Alabama','WR'),('Ohio State','WR'),('LSU','ALL')]: show(k)
