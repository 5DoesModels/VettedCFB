import json, collections, sys
E=sys.argv[1]; O='/home/claude/concept/'
X=json.load(open(E+'/data/pool2.json')); P=X['players']; C=json.load(open(E+'/data/coaches.json')); PO=json.load(open(E+'/data/portal.json'))
HC={}; HG={}; FBS=set(); CAREER={}; CONF={}
for c in C:
    nm=f"{c['firstName']} {c['lastName']}"; ss=[]
    for s in c['seasons']:
        g=s['games'] or 0; key=(s['school'],s['year']); CONF[key]=s.get('conference')
        if g>=1 or s['year']==2026:
            if g>HG.get(key,-1): HC[key]=nm; HG[key]=g
            ss.append(s)
        if s['year'] in (2025,2026): FBS.add(s['school'])
    if ss: CAREER[nm]=ss
CUR={sch:HC[(sch,2026)] for (sch,y) in HC if y==2026}
def last(r):
    d=[m[1] for m in r['mv'] if m[1]]
    return d[-1] if d else r['committedTo']
def cred(r): return r['draftTeam'] if r['draftYear'] else last(r)
def coach(r):
    s=cred(r); y=r['year']+2
    arr=[m[0] for m in r['mv'] if m[1]==s]
    if arr: y=max(y,arr[-1])
    y=min(y,2026)
    return HC.get((s,y)) or HC.get((s,y-1))
SC=[r for r in P if r['exp'] is not None and not (not r['draftYear'] and any(m[1] and m[0]>=2025 for m in r['mv']))]
def agg(rs):
    return [len(rs),sum(1 for r in rs if r['draftYear']),sum(1 for r in rs if r['tier'] in('First round','Top 10 pick')),round(sum(r['pts'] for r in rs),1),round(sum(r['exp'] for r in rs),1)]
def path(r):
    return [[m[0],m[1]] for m in r['mv']]
def tag(r):
    return dict(n=r['name'],y=r['year'],s=r['stars'] or 0,rt=round(r['rating'] or 0,4),g=r['pg'],h=(r['city'] or '')+(', ' if r['city'] else '')+(r['stateProvince'] or ''),
      sg=r['committedTo'],dt=r['draftTeam'],dy=r['draftYear'],o=r['overall'],t=r['tier'],pts=r['pts'],e=None if r['exp'] is None else round(r['exp'],1),pae=None if r['pae'] is None else round(r['pae'],1),jc=r['recruitType']!='HighSchool',mv=path(r))
tags={}
def addtag(r): tags[r['i']]=tag(r); return r['i']
G=['QB','RB','WR','TE','OL','DL','EDGE','LB','DB']
# portal raw counts by program
pin=collections.defaultdict(list); pout=collections.defaultdict(list)
for p in PO:
    if p['destination']: pin[p['destination']].append(p)
    pout[p['origin']].append(p)
def pstats(lst):
    by=collections.Counter(p['season'] for p in lst); st=[p['stars'] for p in lst if p['stars']]
    return dict(n=len(lst),by=[by.get(y,0) for y in range(2021,2027)],st=round(sum(st)/len(st),2) if st else None,s4=sum(1 for x in st if x>=4))
byp=collections.defaultdict(list)
for r in SC: byp[cred(r)].append(r)
progs=[]
for k,rs in byp.items():
    if k not in FBS or len(rs)<150: continue
    full=[r for r in rs if r['year']<=2020]; ip=[r for r in rs if r['year']>2020]
    co=collections.defaultdict(list)
    for r in rs: co[coach(r) or 'Unknown'].append(r)
    cos=sorted([[c]+agg(v)+[min(r['year'] for r in v)+2,min(2026,max(r['year'] for r in v)+2)] for c,v in co.items() if len(v)>=20],key=lambda x:x[-2])
    dr=[r for r in rs if r['draftYear']]
    best=[addtag(r) for r in sorted(dr,key=lambda r:-r['pae'])[:6]]
    miss=[addtag(r) for r in sorted([r for r in full if not r['draftYear']],key=lambda r:r['pae'])[:4]]
    portalDrafted=[addtag(r) for r in sorted([r for r in dr if r['mv'] and r['mv'][-1][1]==k],key=lambda r:-r['pts'])[:6]]
    progs.append(dict(name=k,cur=CUR.get(k),a=agg(rs),full=agg(full),ip=agg(ip),stars={s:agg([r for r in rs if (r['stars'] or 0)==s]) for s in (0,2,3,4,5)},
      pos={g:agg([r for r in rs if r['pg']==g]) for g in G},coaches=cos,best=best,miss=miss,pin=pstats(pin[k]),pout=pstats(pout[k]),pdr=portalDrafted,
      pdrn=sum(1 for r in dr if r['mv'] and r['mv'][-1][1]==k)))
NCL=len(range(2008,2024))
progs.sort(key=lambda p:-(p['a'][3]-p['a'][4]))
# coaches
byc=collections.defaultdict(list)
for r in SC:
    c=coach(r)
    if c: byc[c].append(r)
coaches=[]
for c,rs in byc.items():
    if len(rs)<40: continue
    car=CAREER.get(c,[]); stints=collections.OrderedDict()
    for s in sorted(car,key=lambda s:s['year']):
        x=stints.setdefault(s['school'],[s['year'],s['year'],0,0]); x[1]=s['year']; x[2]+=s['wins'] or 0; x[3]+=s['losses'] or 0
    sch=collections.defaultdict(list)
    for r in rs: sch[cred(r)].append(r)
    dr=[r for r in rs if r['draftYear']]
    coaches.append(dict(name=c,a=agg(rs),st=[[k]+v for k,v in stints.items()],sch=sorted([[k]+agg(v) for k,v in sch.items()],key=lambda x:-x[1]),
      pos={g:agg([r for r in rs if r['pg']==g]) for g in G},best=[addtag(r) for r in sorted(dr,key=lambda r:-r['pae'])[:4]],
      w=sum(v[2] for v in stints.values()),l=sum(v[3] for v in stints.values()),cur=car[-1]['school'] if car else '',active=any(s['year']==2026 for s in car)))
coaches.sort(key=lambda c:-(c['a'][3]-c['a'][4]))
for c in coaches: c['now']=next((s['school'] for s in CAREER.get(c['name'],[]) if s['year']==2026),None)
# leaderboards: program x position x stars (graded classes)
LB=collections.defaultdict(lambda:collections.defaultdict(list))
for r in SC:
    k=cred(r)
    if k in FBS: LB[k][(r['pg'],r['stars'] or 0)].append(r)
lb=[[k,g,st]+agg(v) for k,d in LB.items() for (g,st),v in d.items()]
# transfer study: classes 2020-2022 (careers inside the portal data window)
P4={'SEC','Big Ten','Big 12','ACC','Pac-12'}
TS=[r for r in P if 2020<=r['year']<=2022]
def p4(r): return CONF.get((r['committedTo'],r['year'])) in P4 or CONF.get((r['committedTo'],r['year']+1)) in P4
stay=collections.defaultdict(lambda:[0,0,0,0])
for r in TS:
    tr=any(m[1] and m[1]!=r['committedTo'] for m in r['mv']); keys=[('ALL',r['pg'])]+([('P4',r['pg'])] if p4(r) else [])+[(r['committedTo'],r['pg'])]
    for k in keys:
        for kk in (k,(k[0],'ALL')):
            x=stay[kk]; x[2 if tr else 0]+=1; x[3 if tr else 1]+=bool(r['draftYear'])
stayd=[[a,b]+v for (a,b),v in stay.items() if a in FBS or a in ('ALL','P4')]
# who develops transfers best: players who finished at a school they transferred into
tx=collections.defaultdict(list)
for r in SC:
    if r['mv'] and cred(r)==last(r) and cred(r)!=r['committedTo']: tx[cred(r)].append(r)
txd=[]
for k,v in tx.items():
    if k not in FBS or len(v)<10: continue
    txd.append([k]+agg(v)+[[addtag(r) for r in sorted([r for r in v if r['draftYear']],key=lambda r:-r['pae'])[:3]]])
txd.sort(key=lambda x:-(x[4]-x[5]))
for r in sorted([r for r in SC if r['draftYear']],key=lambda r:-r['pae'])[:60]: addtag(r)
for nm in ['Shazz Preston','Aaron Anderson','Jack Bech']:
    for r in P:
        if r['name']==nm and r['year']>=2020: addtag(r)
for r in sorted([r for r in SC if r['draftYear'] and r['year']>2020],key=lambda r:-r['pae'])[:25]: addtag(r)
for nm in ["Ja'Marr Chase","Joe Burrow","Justin Jefferson","DeVonta Smith","Kyle Pitts","Brock Purdy","Aaron Donald","Malik Nabers","Caleb Williams","Jayden Daniels","Travis Hunter","Khalil Mack"]:
    for r in SC:
        if r['name']==nm and r['draftYear']: addtag(r)
# finder files: HS signees, every class, by position group
fin=collections.defaultdict(list); states=collections.Counter()
for r in P:
    if r['recruitType']!='HighSchool': continue
    fin[r['pg']].append([r['name'],r['year'],r['stars'] or 0,round(r['rating'] or 0,4),r['stateProvince'] or '',r['city'] or '',r['committedTo'],cred(r) if r['exp'] is not None else r['committedTo'],r['pts'],None if r['exp'] is None else round(r['exp'],2),r['overall'],r['draftYear'],r['round'],path(r)])
    states[r['stateProvince']]+=1
for g,rows in fin.items():
    if g in G: open(O+f'f/{g}.json','w').write(json.dumps(rows,separators=(',',':')))
yrs=sorted({p['year'] for p in P})
meta=dict(classes=[yrs[0],yrs[-1]],scored=[2008,2023],complete=[2008,2020],draft=[2010,X['last']],portal=[2021,2026],n=len(P),nsc=len(SC),dr=sum(1 for r in SC if r['draftYear']),ncl=NCL,
   pl=sum(1 for r in P if r['mv']),pn=len(PO))
HSF=[r for r in SC if r['recruitType']=='HighSchool' and r['year']<=2020]
meta['sr']={st:[len(v),round(100*sum(1 for r in v if r['draftYear'])/len(v),1),round(100*sum(1 for r in v if r['tier'] in('First round','Top 10 pick'))/len(v),2),round(sum(r['pts'] for r in v)/len(v),2)] for st in (2,3,4,5) for v in [[r for r in HSF if r['stars']==st]]}
yc=[r for r in P if 2021<=r['year']<=2023]; meta['psh']=round(100*sum(1 for r in yc if r['mv'])/len(yc),1); meta['pmv']=round(100*sum(1 for r in yc if any(m[1] and m[1]!=r['committedTo'] for m in r['mv']))/len(yc),1)
# states: HS signees, graded classes
stx=collections.defaultdict(list)
for r in SC:
    if r['recruitType']=='HighSchool' and r['stateProvince']: stx[r['stateProvince']].append(r)
states={}
for k,v in stx.items():
    pr=collections.defaultdict(list)
    for r in v: pr[cred(r)].append(r)
    top=sorted([[pk]+agg(pv) for pk,pv in pr.items() if len(pv)>=5],key=lambda x:-(x[4]-x[5]))[:3]
    states[k]=agg(v)+[top]
# search index: every signee
SCH=sorted({r['committedTo'] for r in P}|{cred(r) for r in P if r['exp'] is not None}|{last(r) for r in P}); SI={k:i for i,k in enumerate(SCH)}
GL=G+['ATH','ST']
idx=[[r['name'],r['year'],GL.index(r['pg']) if r['pg'] in GL else 9,SI[r['committedTo']],SI[cred(r) if r['exp'] is not None else last(r)],r['overall'] or 0,r['stars'] or 0,r['stateProvince'] or '',1 if any(m[1] and m[1]!=r['committedTo'] for m in r['mv']) else 0,r['round'] or 0] for r in P]
open(O+'search.json','w').write(json.dumps(dict(s=SCH,g=GL,p=idx),separators=(',',':')))
s=json.dumps(dict(states=states,meta=meta,progs=progs,coaches=coaches,tags=tags,lb=lb,stay=stayd,tx=txd),separators=(',',':'))
open(O+'data.json','w').write(s)
import os
print(len(progs),len(coaches),len(tags),len(s)//1024,'KB',{g:os.path.getsize(O+f'f/{g}.json')//1024 for g in G},meta)
print([(p['name'],round((p['a'][3]-p['a'][4])/NCL)) for p in progs[:6]],[(p['name'],round((p['a'][3]-p['a'][4])/NCL)) for p in progs[-4:]])
print([(c['name'],c['a'][0],round(c['a'][3]/c['a'][4],2)) for c in coaches[:8]])
# ================= v4 additions =================
import math
EARLY=range(2008,2016); RECENT=range(2016,2024)
tr={}
for p in progs:
    rs=byp[p['name']]
    e=[r for r in rs if r['year'] in EARLY]; l=[r for r in rs if r['year'] in RECENT]
    pe=(sum(r['pts'] for r in e)-sum(r['exp'] for r in e))/8; pl=(sum(r['pts'] for r in l)-sum(r['exp'] for r in l))/8
    p['early']=round(pe,1); p['recent']=round(pl,1); p['conf']=CONF.get((p['name'],2026)) or CONF.get((p['name'],2025))
# wins: seasons 2012-2025 per school
W=collections.defaultdict(lambda:[0,0,[],[]])
for c in C:
    for s_ in c['seasons']:
        if 2012<=s_['year']<=2025 and (s_['games'] or 0)>0:
            w=W[s_['school']]; w[0]+=s_['wins'] or 0; w[1]+=s_['losses'] or 0
            if s_.get('srs') is not None: w[2].append(s_['srs'])
            if s_.get('spOverall') is not None: w[3].append(s_['spOverall'])
ana=[]
for p in progs:
    w=W.get(p['name'])
    if not w or w[0]+w[1]<60: continue
    ana.append([p['name'],round((p['a'][3]-p['a'][4])/NCL,1),round(p['a'][4]/NCL,1),round(w[0]/(w[0]+w[1]),3),round(sum(w[2])/len(w[2]),1) if w[2] else None,p['conf']])
def corr(x,y):
    n=len(x);mx=sum(x)/n;my=sum(y)/n;sx=math.sqrt(sum((a-mx)**2 for a in x));sy=math.sqrt(sum((b-my)**2 for b in y))
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/(sx*sy)
def r2(X,y):
    # least squares with intercept, X list of columns
    import itertools
    n=len(y);cols=[[1]*n]+X;k=len(cols)
    A=[[sum(cols[i][t]*cols[j][t] for t in range(n)) for j in range(k)] for i in range(k)];b=[sum(cols[i][t]*y[t] for t in range(n)) for i in range(k)]
    for i in range(k):
        piv=A[i][i]
        for j in range(i,k): A[i][j]/=piv
        b[i]/=piv
        for r_ in range(k):
            if r_!=i:
                f=A[r_][i]
                for j in range(i,k): A[r_][j]-=f*A[i][j]
                b[r_]-=f*b[i]
    pred=[sum(b[i]*cols[i][t] for i in range(k)) for t in range(n)];my=sum(y)/n
    return 1-sum((y[t]-pred[t])**2 for t in range(n))/sum((v-my)**2 for v in y), b
dev=[a[1] for a in ana]; tal=[a[2] for a in ana]; wp=[a[3] for a in ana]
srsr=[a for a in ana if a[4] is not None]
R2t,_=r2([tal],wp); R2td,bb=r2([tal,dev],wp)
stats=dict(n=len(ana),r_dev_win=round(corr(dev,wp),2),r_tal_win=round(corr(tal,wp),2),r_dev_srs=round(corr([a[1] for a in srsr],[a[4] for a in srsr]),2),r_tal_srs=round(corr([a[2] for a in srsr],[a[4] for a in srsr]),2),
   r2_tal=round(R2t,3),r2_both=round(R2td,3),b_dev=round(bb[2],4),b_tal=round(bb[1],4),avg_dev=0,avg_draft=round(sum(p['a'][1] for p in progs)/len(progs)/NCL,2))
# conferences (2026 membership)
cf=collections.defaultdict(list)
for p in progs:
    if p['conf']: cf[p['conf']].append(p)
confs=[[k,len(v),round(sum((p['a'][3]-p['a'][4])/NCL for p in v)/len(v),1),round(sum(p['a'][3] for p in v)/sum(p['a'][4] for p in v),2),round(sum(p['recent'] for p in v)/len(v),1),round(sum(p['early'] for p in v)/len(v),1),
        round(sum(W[p['name']][0] for p in v)/max(1,sum(W[p['name']][0]+W[p['name']][1] for p in v)),3),[p['name'] for p in sorted(v,key=lambda p:-(p['a'][3]-p['a'][4]))]] for k,v in cf.items() if len(v)>=6]
confs.sort(key=lambda x:-x[2])
# coach portal lean (seasons 2021-2026)
for c in coaches:
    car=CAREER.get(c['name'],[]); ten=[(s_['school'],s_['year']) for s_ in car if s_['year']>=2021]
    tin=sum(1 for p_ in PO if p_['destination'] and (p_['destination'],p_['season']) in set(ten))
    sg=sum(1 for r in P if (r['committedTo'],r['year']-1) in set(ten) and r['recruitType']=='HighSchool')
    mine=[r for r in byc.get(c['name'],[])]
    vp=[r for r in mine if r['mv'] and cred(r)!=r['committedTo']]; vs=[r for r in mine if not (r['mv'] and cred(r)!=r['committedTo'])]
    c['pl']=[tin,sg,len(vp),round(sum(r['pts'] for r in vp),1),round(sum(r['exp'] for r in vp),1),len(vs),round(sum(r['pts'] for r in vs),1),round(sum(r['exp'] for r in vs),1),len(set(ten))]
open(O+'data.json','w').write(json.dumps(dict(states=states,meta=meta,progs=progs,coaches=coaches,tags=tags,lb=lb,stay=stayd,tx=txd,ana=ana,stats=stats,confs=confs),separators=(',',':')))
print('STATS',stats)
pr=sorted(progs,key=lambda p:-p['recent']);print('HOT',[(p['name'],p['recent']) for p in pr[:5]],'COLD',[(p['name'],p['recent']) for p in pr[-5:]])
d=sorted(progs,key=lambda p:-(p['recent']-p['early']));print('RISE',[(p['name'],p['early'],p['recent']) for p in d[:6]],'SINK',[(p['name'],p['early'],p['recent']) for p in d[-5:]])
print('CONF',[(c[0],c[1],c[2],c[3]) for c in confs])
ac=[c for c in coaches if c['now'] and c['pl'][8]>=2]
print('LEAN',[(c['name'],c['pl'][0],c['pl'][1],round(c['pl'][0]/max(1,c['pl'][0]+c['pl'][1]),2)) for c in sorted(ac,key=lambda c:-c['pl'][0]/max(1,c['pl'][0]+c['pl'][1]))[:6]])
# ================= v5 additions =================
import sys as _s; _s.path.insert(0,'/home/claude/concept'); from schoolstate import SS
# last five graded classes
R5=range(2019,2024); PRIOR=range(2008,2019)
for p in progs:
    rs=byp[p['name']]; a=[r for r in rs if r['year'] in R5]; b=[r for r in rs if r['year'] in PRIOR]
    p['r5']=round((sum(r['pts'] for r in a)-sum(r['exp'] for r in a))/5,1); p['p11']=round((sum(r['pts'] for r in b)-sum(r['exp'] for r in b))/11,1); p['r5a']=agg(a)
# coaches: last five, per season, school-adjusted
schoolC=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]))
for c_,rs in byc.items():
    for r in rs: x=schoolC[cred(r)][c_]; x[0]+=r['pts']; x[1]+=r['exp']
for c in coaches:
    rs=byc[c['name']]; a=[r for r in rs if r['year'] in R5]; c['r5']=agg(a)
    seas=[s_ for s_ in CAREER.get(c['name'],[]) if 2010<=s_['year']<=2025 and (s_['games'] or 0)>0]; c['ns']=len(seas)
    adj=0
    for sname,v in collections.Counter(cred(r) for r in rs).items():
        op=sum(x[0] for cc,x in schoolC[sname].items() if cc!=c['name']); oe=sum(x[1] for cc,x in schoolC[sname].items() if cc!=c['name'])
        norm=min(1.5,max(0.7,(op+200)/(oe+200)))
        mine=[r for r in rs if cred(r)==sname]; adj+=sum(r['pts'] for r in mine)-norm*sum(r['exp'] for r in mine)
    c['adj']=round(adj,1); c['ps']=round((c['a'][3]-c['a'][4])/max(1,c['ns']),1); c['adjps']=round(adj/max(1,c['ns']),1)
# in-state study
HSall=[r for r in P if r['recruitType']=='HighSchool' and r['stateProvince'] and SS.get(r['committedTo'])]
home=collections.defaultdict(lambda:[0,0])
for r in HSall: x=home[r['stateProvince']]; x[0]+=SS[r['committedTo']]==r['stateProvince']; x[1]+=1
T4=[r for r in HSall if 2020<=r['year']<=2023]
def mvd(r): return [m[1] for m in r['mv'] if m[1] and m[1]!=r['committedTo']]
ins=[r for r in T4 if SS[r['committedTo']]==r['stateProvince']]; outs=[r for r in T4 if SS[r['committedTo']]!=r['stateProvince']]
outs_tr=[r for r in outs if mvd(r)]; ins_tr=[r for r in ins if mvd(r)]
comehome=sum(1 for r in outs_tr if SS.get(mvd(r)[-1])==r['stateProvince'])
leavehome=sum(1 for r in ins_tr if SS.get(mvd(r)[-1]) and SS.get(mvd(r)[-1])!=r['stateProvince'])
G8=[r for r in HSall if r['exp'] is not None and r['year']<=2020]
gi=[r for r in G8 if SS[r['committedTo']]==r['stateProvince']]; go=[r for r in G8 if SS[r['committedTo']]!=r['stateProvince']]
instate=dict(home={k:v for k,v in home.items() if v[1]>=30},all=[sum(v[0] for v in home.values()),sum(v[1] for v in home.values())],
  ins=len(ins),ins_tr=len(ins_tr),leave=leavehome,outs=len(outs),outs_tr=len(outs_tr),come=comehome,
  dr_in=[len(gi),sum(1 for r in gi if r['draftYear']),round(sum(r['pts'] for r in gi)/sum(r['exp'] for r in gi),2)],dr_out=[len(go),sum(1 for r in go if r['draftYear']),round(sum(r['pts'] for r in go)/sum(r['exp'] for r in go),2)])
# finder rows: add head coach credited (index into coach list)
CN=sorted({c for c in (coach(r) for r in SC) if c}); CI={c:i for i,c in enumerate(CN)}
for g,rows in fin.items():
    pass
fin2=collections.defaultdict(list)
for r in P:
    if r['recruitType']!='HighSchool': continue
    c_=coach(r) if r['exp'] is not None else None
    fin2[r['pg']].append([r['name'],r['year'],r['stars'] or 0,round(r['rating'] or 0,4),r['stateProvince'] or '',r['city'] or '',r['committedTo'],cred(r) if r['exp'] is not None else last(r),r['pts'],None if r['exp'] is None else round(r['exp'],2),r['overall'],r['draftYear'],r['round'],path(r),CI.get(c_,-1)])
for g,rows in fin2.items():
    if g in G: open(O+f'f/{g}.json','w').write(json.dumps(rows,separators=(',',':')))
open(O+'data.json','w').write(json.dumps(dict(states=states,meta=meta,progs=progs,coaches=coaches,tags=tags,lb=lb,stay=stayd,tx=txd,ana=ana,stats=stats,confs=confs,instate=instate,cn=CN),separators=(',',':')))
print('INSTATE',{k:v for k,v in instate.items() if k!='home'})
print('top home',sorted([(k,round(v[0]/v[1],2),v[1]) for k,v in instate['home'].items() if v[1]>=300],key=lambda x:-x[1])[:6])
print('HOT5',[(p['name'],p['r5']) for p in sorted(progs,key=lambda p:-p['r5'])[:5]])
print('ADJ',[(c['name'],c['adjps'],c['ns']) for c in sorted(coaches,key=lambda c:-c['adjps'])[:8]])
print('PS',[(c['name'],c['ps']) for c in sorted(coaches,key=lambda c:-c['ps'])[:6]])
