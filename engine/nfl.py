import csv, json, collections, math, itertools
E='/home/claude/vetted-cfb/engine/data/'
R=list(csv.DictReader(open('/home/claude/nfl/draft_picks.csv')))
D=json.load(open(E+'draft.json')); idx={(d['year'],d['overall']):d for d in D}
L={int(k):v for k,v in json.load(open(E+'links.json')).items()}; REC=json.load(open(E+'recruits.json'))
dkey={(d['year'],d['overall']):i for i,d in enumerate(D)}
f=lambda x:float(x) if x not in ('',None) else 0.0
rows=[]
for r in R:
    y=int(r['season'])
    if y<2010: continue
    d=idx.get((y,int(r['pick'])))
    if not d: continue
    to=int(r['to']) if r['to'] else None
    seasons=(to-y+1) if to else 0
    i=dkey[(y,int(r['pick']))]; rec=REC[L[i]] if i in L else None
    pts_=0
    rows.append(dict(n=r['pfr_player_name'],y=y,o=int(r['pick']),rd=int(r['round']),pos=r['position'],sch=d['collegeTeam'],nfl=r['team'],sea=seasons,act=to==2026,g=int(f(r['games'])),st=int(f(r['seasons_started'])),pb=int(f(r['probowls'])),ap=int(f(r['allpro'])),av=f(r['w_av']),np=seasons+int(f(r['seasons_started']))+3*int(f(r['probowls']))+6*int(f(r['allpro'])),stars=(rec or {}).get('stars')))
# expected value for the slot: same draft year, picks within +/-16
by=collections.defaultdict(list)
for x in rows: by[x['y']].append(x)
for y,g in by.items():
    for x in g:
        nb=[z['np'] for z in g if abs(z['o']-x['o'])<=16]
        x['ex']=sum(nb)/len(nb); x['ov']=x['np']-x['ex']
# national: career length by round, drafts 2010-2016
old=[x for x in rows if x['y']<=2016]
rnd={k:[round(sum(x['sea'] for x in v)/len(v),1),round(100*sum(1 for x in v if x['sea']>=5)/len(v)),round(100*sum(1 for x in v if x['pb']>0)/len(v),1),len(v)] for k,v in itertools.groupby(sorted(old,key=lambda x:x['rd']),key=lambda x:x['rd']) for v in [list(v)]}
# schools
S=collections.defaultdict(list)
for x in rows: S[x['sch']].append(x)
sch=[]
for k,v in S.items():
    o=[x for x in v if x['y']<=2016]; vv=[x for x in v if x['y']<=2023]
    if len(v)<12: continue
    sch.append(dict(k=k,n=len(v),no=len(o),sea=round(sum(x['sea'] for x in o)/len(o),1) if o else None,s5=round(100*sum(1 for x in o if x['sea']>=5)/len(o)) if o else None,
      ov=round(sum(x['ov'] for x in vv)/len(vv),1) if vv else 0,nv=len(vv),pb=sum(x['pb'] for x in v),ap=sum(x['ap'] for x in v),act=sum(1 for x in v if x['act']),
      st=round(sum(x['st'] for x in vv)/len(vv),1) if vv else 0,
      top=[[x['n'],x['y'],x['o'],x['pos'],x['sea'],x['g'],x['pb'],round(x['ov'],1),x['ap'],x['np']] for x in sorted(v,key=lambda x:-x['np'])[:5]],
      steal=[[x['n'],x['y'],x['o'],x['pos'],round(x['ov'],1),x['np'],round(x['ex'],1)] for x in sorted(vv,key=lambda x:-x['ov'])[:3]],
      bust=[[x['n'],x['y'],x['o'],x['pos'],round(x['ov'],1),x['np'],round(x['ex'],1)] for x in sorted(vv,key=lambda x:x['ov'])[:3]]))
sch.sort(key=lambda s:-s['ov'])
lng=sorted([x for x in rows],key=lambda x:(-x['sea'],-x['g']))[:12]
best=sorted(rows,key=lambda x:-x['np'])[:12]
SI={k:i for i,k in enumerate(sorted({x['sch'] for x in rows}))}
picks=[[SI[x['sch']],x['y'],round(x['ov'],1),x['sea'],x['pb'],x['ap'],1 if x['act'] else 0,x['np'],x['st']] for x in rows]
steals=sorted([x for x in rows if x['y']<=2023],key=lambda x:-x['ov'])[:10]
# relation: college development vs NFL value over slot
dd=json.load(open('/home/claude/concept/data.json'))
dev={p['name']:p['a'][3]/p['a'][4] for p in dd['progs']}
pairs=[(dev[s['k']],s['ov']) for s in sch if s['k'] in dev and s['nv']>=20]
def corr(a,b):
    n=len(a);ma=sum(a)/n;mb=sum(b)/n;return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
r=corr([p[0] for p in pairs],[p[1] for p in pairs])
out=dict(best=[[x['n'],x['y'],x['o'],x['sch'],x['pos'],x['sea'],x['st'],x['pb'],x['ap'],x['np']] for x in best],schools=sorted(SI,key=SI.get),picks=picks,rnd=rnd,sch=sch,lng=[[x['n'],x['y'],x['o'],x['sch'],x['pos'],x['sea'],x['g'],x['pb']] for x in lng],steals=[[x['n'],x['y'],x['o'],x['sch'],x['pos'],round(x['ov'],1),x['pb'],x['ap'],x['np'],round(x['ex'],1)] for x in steals],
  r=round(r,2),n=len(rows),avgsea=round(sum(x['sea'] for x in old)/len(old),1),pb=round(100*sum(1 for x in old if x['pb'])/len(old),1))
open('/home/claude/concept/nfl.json','w').write(json.dumps(out,separators=(',',':')))
print('rounds',rnd);print('r dev vs nfl value',out['r'],len(pairs));print('top',[(s['k'],s['ov'],s['sea'],s['nv']) for s in sch[:6]]);print('bottom',[(s['k'],s['ov'],s['sea'],s['nv']) for s in sch[-6:]])
lsu=[s for s in sch if s['k']=='LSU'][0];print('LSU',lsu['sea'],lsu['s5'],lsu['ov'],lsu['pb'],lsu['top'][:2])
