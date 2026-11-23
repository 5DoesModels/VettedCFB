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
# v1.37 (JC, Nov. 22): interim head coaches. In a season with a mid-season change, a coach who took over and did not stay
# (no season at that school the year before or the year after) gets no credit; the head coach who started that season does.
_byk=collections.defaultdict(list); _cy=collections.defaultdict(set)
for c in C:
    nm=f"{c['firstName']} {c['lastName']}"
    for s in c['seasons']:
        g=s['games'] or 0
        if g>=1 or s['year']==2026: _cy[(nm,s['school'])].add(s['year'])
        if g>=1: _byk[(s['school'],s['year'])].append(nm)
INTERIM={}
for k,v in _byk.items():
    top=HC.get(k); sch,y=k
    if len(v)<2 or not top or y-1 in _cy[(top,sch)] or y+1 in _cy[(top,sch)]: continue
    st=[n for n in v if n!=top and y-1 in _cy[(n,sch)]]
    if st: INTERIM[k]=[top,st[0]]; HC[k]=st[0]
print('INTERIM seasons reassigned',len(INTERIM))
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
SA_SCH={'Army','Navy','Air Force'}   # service academies: military commitment, so draft results don't measure development
SC=[r for r in P if r['exp'] is not None and not (not r['draftYear'] and any(m[1] and m[0]>=2025 for m in r['mv'])) and cred(r) not in SA_SCH]
_cnt=collections.Counter(r['year'] for r in P if r['recruitType'] in ('HighSchool','JUCO','PrepSchool') and r['committedTo'] in FBS)
COV={y:min(1.0,round(_cnt[y]/len(FBS)/24,2)) for y in _cnt}   # share of a typical class our data source lists
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
    best=[addtag(r) for r in sorted(dr,key=lambda r:-r['pae'])[:8]]
    miss=[addtag(r) for r in sorted([r for r in full if not r['draftYear']],key=lambda r:r['pae'])[:4]]
    portalDrafted=[addtag(r) for r in sorted([r for r in dr if r['mv'] and r['mv'][-1][1]==k],key=lambda r:-r['pts'])[:6]]
    progs.append(dict(name=k,cur=CUR.get(k),a=agg(rs),full=agg(full),ip=agg(ip),stars={s:agg([r for r in rs if (r['stars'] or 0)==s]) for s in (0,2,3,4,5)},
      pos={g:agg([r for r in rs if r['pg']==g]) for g in G},coaches=cos,best=best,miss=miss,pin=pstats(pin[k]),pout=pstats(pout[k]),pdr=portalDrafted,
      pdrn=sum(1 for r in dr if r['mv'] and r['mv'][-1][1]==k)))
NCL=len(range(2002,2024))
# eligible FBS signing seasons per program (seasons it played FBS football, 2002-2023)
FY=collections.defaultdict(set)
for _c in C:
    for _s in _c['seasons']:
        if 2002<=_s['year']<=2023 and (_s['games'] or 0)>0: FY[_s['school']].add(_s['year'])
def dpe(name,rs,yrs=None):
    E=FY.get(name,set()) if yrs is None else (FY.get(name,set())&set(yrs))
    if not E: return 0.0
    return sum(r['pts']-r['exp'] for r in rs if r['year'] in E)/len(E)
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
      pos={g:agg([r for r in rs if r['pg']==g]) for g in G},best=[addtag(r) for r in sorted(dr,key=lambda r:-r['pae'])[:6]],miss=[addtag(r) for r in sorted([r for r in rs if r['k']==8 and not r['draftYear']],key=lambda r:r['pae'])[:4]],
      w=sum(v[2] for v in stints.values()),l=sum(v[3] for v in stints.values()),cur=car[-1]['school'] if car else '',active=any(s['year']==2026 for s in car)))
coaches.sort(key=lambda c:-(c['a'][3]-c['a'][4]))
for c in coaches:
    _r=byc[c['name']]; c['cov']=round(sum(COV.get(r['year'],1) for r in _r)/max(1,len(_r)),2)
# attribution transparency + data coverage on report cards
_D=json.load(open(E+'/data/draft.json'))
_picks=collections.Counter(d['collegeTeam'] for d in _D if 2003<=d['year']<=2026)
_link=collections.Counter(r['draftTeam'] for r in P if r['draftYear'])
for c in coaches:
    _r=byc[c['name']]; first={}
    for x in c['st']: first.setdefault(x[0],x[1])
    inh=sum(1 for r in _r if r['year']<first.get(cred(r),r['year']) and cred(r)==r['committedTo'])
    tin=sum(1 for r in _r if cred(r)!=r['committedTo'])
    ys=sorted({r['year'] for r in _r})
    c['attr']=[len(_r),inh,tin,ys[0] if ys else None,ys[-1] if ys else None,len(ys)]
for p in progs:
    _r=byp[p['name']]; ys=sorted({r['year'] for r in _r})
    p['attr']=[len(_r),ys[0] if ys else None,ys[-1] if ys else None,_picks.get(p['name'],0),_link.get(p['name'],0)]
for p in progs:
    _r=byp[p['name']]; p['cov']=round(sum(COV.get(r['year'],1) for r in _r)/max(1,len(_r)),2)
for c in coaches: c['now']=next((s['school'] for s in CAREER.get(c['name'],[]) if s['year']==2026),None)
# v1.36 (JC, Nov. 22): context only, not graded. Last season coached (games played) and recent form (last 3 finished seasons, 2023-2025).
for c in coaches:
    car=sorted([s for s in CAREER.get(c['name'],[]) if (s['games'] or 0)>=1],key=lambda s:s['year'])
    c['last']=[car[-1]['school'],car[-1]['year']] if car else None
    r=[s for s in car if 2023<=s['year']<=2025]
    c['rf']=[sum(s['wins'] for s in r),sum(s['losses'] for s in r),[[s['year'],s['wins'],s['losses'],s['school']] for s in r]] if r else None
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
# ---- transfer finder rows (tr.json): players who transferred in and finished at that school
def lvl(sch,y):
    cf=CONF.get((sch,y)) or CONF.get((sch,y-1))
    if sch not in FBS and not cf: return 2
    if sch=='Notre Dame' or cf in ('SEC','Big Ten','Big 12','ACC') or (cf=='Pac-12' and y<=2023): return 0
    return 1 if (sch in FBS or cf) else 2
TRS=[r for r in SC if r['mv'] and cred(r)==last(r) and cred(r)!=r['committedTo']]
TS=sorted({cred(r) for r in TRS}|{r['committedTo'] for r in TRS}); TCn=sorted({(HC.get((cred(r),[m for m in r['mv'] if m[1]==cred(r)][-1][0])) or '') for r in TRS})
trows=[]
for r in TRS:
    arr=[m for m in r['mv'] if m[1]==cred(r)][-1][0]; prev=[m[1] for m in r['mv'] if m[1] and m[0]<arr]; frm=prev[-1] if prev else r['committedTo']
    c_=HC.get((cred(r),arr)) or ''
    trows.append([arr,TS.index(cred(r)),TCn.index(c_),r['pg'],r['pts'],round(r['exp'],2),1 if r['draftYear'] else 0,1 if r['tier'] in ('First round','Top 10 pick') else 0,addtag(r) if r['draftYear'] else -1,lvl(frm,arr-1),r['stars'] or 0,TS.index(frm) if frm in TS else -1,1 if cred(r) in FBS else 0,lvl(cred(r),arr)])
open(O+'tr.json','w').write(json.dumps(dict(S=TS,C=TCn,rows=trows),separators=(',',':')))
print('TR rows',len(trows),'drafted',sum(t[6] for t in trows),'by arrival',sorted(collections.Counter(t[0] for t in trows).items()))
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
meta=dict(classes=[yrs[0],yrs[-1]],scored=[2002,2023],complete=[2002,2020],draft=[2003,X['last']],portal=[2021,2026],n=len(P),nsc=len(SC),dr=sum(1 for r in SC if r['draftYear']),ncl=NCL,
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
idx=[[r['name'],r['year'],GL.index(r['pg']) if r['pg'] in GL else 9,SI[r['committedTo']],SI[cred(r) if r['exp'] is not None else last(r)],r['overall'] or 0,r['stars'] or 0,r['stateProvince'] or '',1 if any(m[1] and m[1]!=r['committedTo'] for m in r['mv']) else 0,r['round'] or 0,round(r['pae'],1) if r['exp'] is not None and r['k']>=3 else None] for r in P]
open(O+'search.json','w').write(json.dumps(dict(s=SCH,g=GL,p=idx),separators=(',',':')))
s=json.dumps(dict(states=states,meta=meta,progs=progs,coaches=coaches,tags=tags,lb=lb,stay=stayd,tx=txd),separators=(',',':'))
open(O+'data.json','w').write(s)
import os
print(len(progs),len(coaches),len(tags),len(s)//1024,'KB',{g:os.path.getsize(O+f'f/{g}.json')//1024 for g in G},meta)
print([(p['name'],round((p['a'][3]-p['a'][4])/NCL)) for p in progs[:6]],[(p['name'],round((p['a'][3]-p['a'][4])/NCL)) for p in progs[-4:]])
print([(c['name'],c['a'][0],round(c['a'][3]/c['a'][4],2)) for c in coaches[:8]])
# ================= v4 additions =================
import math
EARLY=range(2002,2016); RECENT=range(2016,2024)
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
    ana.append([p['name'],round(dpe(p['name'],byp[p['name']]),1),round(p['a'][4]/NCL,1),round(w[0]/(w[0]+w[1]),3),round(sum(w[2])/len(w[2]),1) if w[2] else None,p['conf']])
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
confs=[[k,len(v),round(sum(dpe(p['name'],byp[p['name']]) for p in v)/len(v),1),round(sum(p['a'][3] for p in v)/sum(p['a'][4] for p in v),2),round(sum(p['recent'] for p in v)/len(v),1),round(sum(p['early'] for p in v)/len(v),1),
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
R5=range(2019,2024); PRIOR=range(2002,2019)
for p in progs:
    rs=byp[p['name']]; a=[r for r in rs if r['year'] in R5]; b=[r for r in rs if r['year'] in PRIOR]
    p['r5']=round(dpe(p['name'],rs,R5),1); p['p11']=round(dpe(p['name'],rs,PRIOR),1); p['r5a']=agg(a)
# coaches: last five, per season, school-adjusted
schoolC=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]))
for c_,rs in byc.items():
    for r in rs: x=schoolC[cred(r)][c_]; x[0]+=r['pts']; x[1]+=r['exp']
for c in coaches:
    rs=byc[c['name']]; a=[r for r in rs if r['year'] in R5]; c['r5']=agg(a)
    seas=[s_ for s_ in CAREER.get(c['name'],[]) if 2004<=s_['year']<=2025 and (s_['games'] or 0)>0]; c['ns']=len(seas)
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
# ================= v6: per-year aggregates for custom year ranges =================
YRS=list(range(2002,2024))
def peryear(rs):
    d=collections.defaultdict(list)
    for r in rs: d[r['year']].append(r)
    return [agg(d[y]) if d.get(y) else [0,0,0,0,0] for y in YRS]
for p in progs: p['py']=peryear(byp[p['name']])
for c in coaches: c['py']=peryear(byc[c['name']])
lby=collections.defaultdict(lambda:[0,0,0,0,0])
for r in SC:
    k=cred(r)
    if k in FBS:
        x=lby[(k,r['pg'],r['stars'] or 0,r['year'])]; a=agg([r])
        for i in range(5): x[i]+=a[i]
PN={p:i for i,p in enumerate(sorted({k[0] for k in lby}))}
lbY=dict(p=sorted(PN,key=PN.get),rows=[[PN[k[0]],G.index(k[1]) if k[1] in G else -1,k[2],k[3]-2002]+[round(v,1) if isinstance(v,float) else v for v in a] for k,a in lby.items() if k[1] in G])
open(O+'lb.json','w').write(json.dumps(lbY,separators=(',',':')))
open(O+'data.json','w').write(json.dumps(dict(states=states,meta=meta,progs=progs,coaches=coaches,tags=tags,lb=[],stay=stayd,tx=txd,ana=ana,stats=stats,confs=confs,instate=instate,cn=CN,yrs=YRS),separators=(',',':')))
import os; print('lb.json',os.path.getsize(O+'lb.json')//1024,'KB data.json',os.path.getsize(O+'data.json')//1024,'KB')
# ================= v7: distance, letter grades, class grades =================
from schoolstate import LL
import math as _m
RAW=json.load(open(E+'/data/recruits.json'))
HT={}
for x in RAW:
    h=x.get('hometownInfo') or {}
    if h.get('latitude') is not None: HT[(x['name'],x['year'],x.get('committedTo'))]=(h['latitude'],h['longitude'])
def miles(a,b):
    la1,lo1,la2,lo2=map(_m.radians,(a[0],a[1],b[0],b[1]));d=_m.sin((la2-la1)/2)**2+_m.cos(la1)*_m.cos(la2)*_m.sin((lo2-lo1)/2)**2
    return 3958.8*2*_m.asin(_m.sqrt(d))
for r in P:
    h=HT.get((r['name'],r['year'],r['committedTo'])); s=LL.get(r['committedTo'])
    r['mi']=round(miles(h,s)) if h and s and r['recruitType']=='HighSchool' else None
BANDS=[(0,100,'Under 100 miles'),(100,250,'100–250 miles'),(250,500,'250–500 miles'),(500,1000,'500–1,000 miles'),(1000,99999,'1,000+ miles')]
def band(m): return next(i for i,b in enumerate(BANDS) if b[0]<=m<b[1])
gd=[r for r in SC if r.get('mi') is not None and r['year']<=2020]
bandDraft=[[b[2],len(v),sum(1 for r in v if r['draftYear']),round(sum(r['pts'] for r in v)/max(.1,sum(r['exp'] for r in v)),2)] for i,b in enumerate(BANDS) for v in [[r for r in gd if band(r['mi'])==i]]]
td=[r for r in P if r.get('mi') is not None and 2020<=r['year']<=2023]
mvd_=lambda r:any(m[1] and m[1]!=r['committedTo'] for m in r['mv'])
bandMove=[[b[2],len(v),round(100*sum(1 for r in v if mvd_(r))/max(1,len(v)),1)] for i,b in enumerate(BANDS) for v in [[r for r in td if band(r['mi'])==i]]]
# per program radius (high school signees, all years)
rad={}
for p in progs:
    v=sorted(r['mi'] for r in P if r['committedTo']==p['name'] and r.get('mi') is not None)
    if len(v)<50: continue
    med=v[len(v)//2]; rad[p['name']]=[len(v),med,round(sum(v)/len(v)),round(100*sum(1 for x in v if x<200)/len(v)),round(100*sum(1 for x in v if x>=500)/len(v))]
    p['rad']=rad[p['name']]
dist=dict(bandDraft=bandDraft,bandMove=bandMove,n=len(gd),med=sorted(r['mi'] for r in P if r.get('mi') is not None)[len([r for r in P if r.get('mi') is not None])//2])
# ---- letter grades ----
def pctile(vals,v,hi=True):
    if v is None or not vals: return None
    below=sum(1 for x in vals if (x<v if hi else x>v)); eq=sum(1 for x in vals if x==v)
    return 100*(below+0.5*eq)/len(vals)
CUT=[(99,'S'),(96,'A+'),(90,'A'),(85,'A-'),(80,'B+'),(72,'B'),(65,'B-'),(58,'C+'),(45,'C'),(35,'C-'),(27,'D+'),(18,'D'),(10,'D-'),(0,'F')]
def letter(p): return None if p is None else next(l for c,l in CUT if p>=c)
# class talent: sum of full expected points of each school's signing class, ranked nationally per year
ct=collections.defaultdict(float); cn=collections.defaultdict(int)
for r in P:
    if r['committedTo'] in FBS: ct[(r['committedTo'],r['year'])]+=r['full']; cn[(r['committedTo'],r['year'])]+=1
byyear=collections.defaultdict(list)
for (s_,y),v in ct.items(): byyear[y].append(v)
def tpct(s_,y): return pctile(byyear[y],ct.get((s_,y),0))
# class development (signees anywhere, graded years)
cd=collections.defaultdict(lambda:[0,0,0,0,0])
for r in P:
    if r['committedTo'] in FBS:
        x=cd[(r['committedTo'],r['year'])]; x[0]+=1; x[1]+=bool(r['draftYear']); x[2]+=mvd_(r)
        if r['exp'] is not None and cred(r) not in SA_SCH and not (not r['draftYear'] and any(m[1] and m[0]>=2025 for m in r['mv'])): x[3]+=r['pts']; x[4]+=r['exp']
devy=collections.defaultdict(list)
for (s_,y),x in cd.items():
    if y<=2023 and x[4]>0: devy[y].append(x[3]-x[4])
# school talent norm for "vs school norm"
schoolT=collections.defaultdict(list)
for (s_,y),v in ct.items(): schoolT[s_].append(tpct(s_,y))
for c in coaches:
    car=CAREER.get(c['name'],[]); cls=[]
    for s_ in car:
        y=s_['year']+1   # class signed during this season
        if (s_['school'],y) in ct and HC.get((s_['school'],s_['year']))==c['name'] and 2002<=y<=2026:
            x=cd[(s_['school'],y)]; tp=tpct(s_['school'],y)
            dv=(x[3]-x[4]) if (y<=2023 and x[4]>0) else None
            cls.append([y,s_['school'],x[0],round(tp),x[1],x[2],None if dv is None else round(dv,1),letter(tp),None if dv is None else letter(pctile(devy[y],dv))])
    c['cls']=sorted({(k[0],k[1]):k for k in cls}.values())
POOL=lambda f:[f(c) for c in coaches if f(c) is not None]
def devv(c): return c['ps'] if c['ns']>=4 else None
def recv(c): return sum(k[3] for k in c['cls'])/len(c['cls']) if len(c['cls'])>=2 else None
def liftv(c):
    if len(c['cls'])<2: return None
    d=[]
    for k in c['cls']:
        others=[tpct(k[1],y) for (s_,y) in ct if s_==k[1] and not any(kk[0]==y and kk[1]==k[1] for kk in c['cls'])]
        if len(others)>=3: d.append(k[3]-sum(others)/len(others))
    return sum(d)/len(d) if d else None
# v1.39 (JC, Nov. 23): winning is graded on schedule-adjusted strength (CFBD SRS, games-weighted over his 2002-2025 seasons),
# so winning big in a weaker conference counts less than winning big in a strong one. His win-loss record is still shown.
def winv(c):
    g=s_=0
    for x in CAREER.get(c['name'],[]):
        if 2002<=x['year']<=2025 and x['games'] and x.get('srs') is not None: g+=x['games']; s_+=x['srs']*x['games']
    return s_/g if g>=24 else None
def mysg(c): return [r for r in P if 2020<=r['year']<=2024 and any(k[0]==r['year'] and k[1]==r['committedTo'] for k in c['cls'])]
def retv(c):
    # players who left: did they beat expectations elsewhere? (lower = his calls look right)
    mine={x['school'] for x in CAREER.get(c['name'],[])}
    gone=[r for r in mysg(c) if mvd_(r) and r['exp'] is not None and r['year']<=2023 and not any(m[1] in mine for m in r['mv'] if m[1]!=r['committedTo'])]
    return (sum(r['pts'] for r in gone)+5)/(sum(r['exp'] for r in gone)+5) if len(gone)>=8 else None
def portv(c): return c['pl'][3]/c['pl'][4] if c.get('pl') and c['pl'][2]>=10 and c['pl'][4]>=8 else None
# v1.39 (JC, Nov. 22-23): honors and penalties (engine/awards/build_coach_honors.py -> data/coach_honors.json).
# Team results count most, player awards a little; penalties for being replaced mid-season, a job ending after a losing season,
# starting 10+ points below the program's previous 3 seasons, and losing seasons from his third year at a school.
# Net points P become a bonus of +/-6 at most: 6*(1-exp(-P/10)) (or the mirror for negative P), added to the overall score.
import math as _m
HON=json.load(open(E+'/data/coach_honors.json'))['coaches']
def honb(nm):
    p=sum(x[4] for x in HON.get(nm,[])); return (6*(1-_m.exp(-p/10)) if p>=0 else -6*(1-_m.exp(p/10))),p
# v1.35 (JC, Nov. 22): 'Players who left' no longer counts toward the overall grade (shown as information only); its weight goes to Development and Developing transfers.
CATS=[('dev','Development',devv,.40),('rec','Recruiting',recv,.15),('lift','Recruits above his school\'s norm',liftv,.1),('win','Winning',winv,.25),('ret','Players who left',retv,0),('port','Developing transfers',portv,.10)]
LOWBETTER={'ret'}
vals={k:POOL(f) for k,_,f,_ in CATS}
for c in coaches:
    g={};ps=[];ws=0
    for k,lab,f,w in CATS:
        v=f(c); p=pctile(vals[k],v,hi=k not in LOWBETTER)
        g[k]=None if p is None else [letter(p),round(p),round(v,3) if isinstance(v,float) else v]
        if p is not None and w>0: ps.append(p*w); ws+=w
    _hb,_hp=honb(c['name'])
    g['all']=[letter(max(0,min(100,sum(ps)/ws+_hb))),round(max(0,min(100,sum(ps)/ws+_hb)))] if ws>=.5 else None
    c['hon']=[round(_hb,2),round(_hp,2),HON.get(c['name'],[])]; c['base']=round(sum(ps)/ws,1) if ws>=.5 else None
    c['g']=g; sg_=mysg(c); c['turn']=[sum(1 for r in sg_ if mvd_(r)),len(sg_)]
# v1.37 (JC, Nov. 22): grade at each school (program cards). Same blend as the overall grade (development 40, winning 25,
# recruiting 15, recruits above the school's norm 10; developing transfers isn't split by school), using only his seasons
# at that school, compared with every head coach stint since 2002. His career grade is unchanged.
STW={'dev':.40,'win':.25,'rec':.15,'lift':.10}; STINT=[]
for c in coaches:
    for s_ in c['st']:
        sch=s_[0]; a=next((x for x in c['sch'] if x[0]==sch),None)
        ns=max(0,min(s_[2],2025)-max(s_[1],2004)+1); cl=[k for k in c['cls'] if k[1]==sch]
        STINT.append(dict(c=c,sch=sch,dev=(a[4]-a[5])/ns if a and ns>=3 and a[1]>=10 else None,
            win=s_[3]/(s_[3]+s_[4]) if s_[3]+s_[4]>=24 else None,
            rec=sum(k[3] for k in cl)/len(cl) if len(cl)>=2 else None,
            lift=liftv(dict(cls=cl)) if len(cl)>=2 else None))
_sv={k:[x[k] for x in STINT if x[k] is not None] for k in STW}
for x in STINT:
    parts={};ps=0;ws=0
    for k,w in STW.items():
        p=pctile(_sv[k],x[k])
        if p is not None: parts[k]=[letter(p),round(p),round(x[k],3)]; ps+=p*w; ws+=w
    x['c'].setdefault('stg',{})[x['sch']]=[letter(ps/ws),round(ps/ws),parts] if ws>=.5 else [None,None,parts]
print('STINT grades',len(STINT),sum(1 for x in STINT if x['c']['stg'][x['sch']][0]))
# programs: development grade from per-year score
for p in progs: p['dpe']=round(dpe(p['name'],byp[p['name']]),2); p['fy']=sorted(FY.get(p['name'],()))
pv=[p['dpe'] for p in progs]
for p in progs:
    v=p['dpe']; p['g']=letter(pctile(pv,v)); p['g5']=letter(pctile([q['r5'] for q in progs],p['r5']))
# ---- player grade cutoffs (development = actual - expected draft points, all graded players)
pv_=sorted(r['pae'] for r in SC)
meta['pcut']=[[c_,round(pv_[min(len(pv_)-1,int(len(pv_)*c_/100))],2)] for c_,_ in CUT if c_>0]
meta['cov']=COV
# ---- JUCO development
JU=[r for r in SC if r['recruitType']=='JUCO']
jp=collections.defaultdict(list); jc=collections.defaultdict(list); jpg=collections.defaultdict(list)
for r in JU:
    k=cred(r)
    if k in FBS: jp[k].append(r); jpg[(k,r['pg'])].append(r)
    c_=coach(r)
    if c_: jc[c_].append(r)
cnow={c['name']:c['now'] for c in coaches}
JS=sorted({cred(r) for r in JU}); JCn=sorted({coach(r) or '' for r in JU})
jrows=[[r['year'],JS.index(cred(r)),JCn.index(coach(r) or ''),r['pg'],r['pts'],round(r['exp'],2),1 if r['draftYear'] else 0,1 if r['tier'] in ('First round','Top 10 pick') else 0,addtag(r) if r['draftYear'] else -1,1 if cred(r) in FBS else 0,1 if cred(r)==r['committedTo'] else 0] for r in JU]
jcs={}  # schools each coach led (FBS seasons)
for c in coaches: jcs[c['name']]=[[x[0],x[1],x[2]] for x in c['st']]
open(O+'juco.json','w').write(json.dumps(dict(S=JS,C=JCn,rows=jrows,cnow={k:cnow.get(k) for k in JCn if cnow.get(k)},cst={k:jcs.get(k,[]) for k in JCn},fbs=sorted(FBS)),separators=(',',':')))
juco=dict(n=len(JU),dr=sum(1 for r in JU if r['draftYear']),
  progs=[[k]+agg(v)+[[addtag(r) for r in sorted([r for r in v if r['draftYear']],key=lambda r:-r['pae'])[:3]]] for k,v in jp.items() if len(v)>=8],
  pos=[[k[0],k[1]]+agg(v) for k,v in jpg.items() if len(v)>=3],
  coaches=[[c_,cnow.get(c_)]+agg(v)+[[addtag(r) for r in sorted([r for r in v if r['draftYear']],key=lambda r:-r['pae'])[:2]]] for c_,v in jc.items() if len(v)>=6],
  best=[addtag(r) for r in sorted([r for r in JU if r['draftYear']],key=lambda r:-r['pae'])[:8]])
print('JUCO',juco['n'],'signees',juco['dr'],'drafted',len(juco['progs']),'programs',len(juco['coaches']),'coaches')
print('JUCO top progs',[(p[0],p[1],p[2],round(p[4]-p[5])) for p in sorted(juco['progs'],key=lambda p:-(p[4]-p[5]))[:6]])
print('JUCO top coaches',[(c[0],c[2],c[3],round(c[5]-c[6])) for c in sorted(juco['coaches'],key=lambda c:-(c[5]-c[6]))[:6]])
print('pcut',meta['pcut'])
open(O+'data.json','w').write(json.dumps(dict(states=states,meta=meta,progs=progs,coaches=coaches,tags=tags,lb=[],stay=stayd,tx=txd,ana=ana,stats=stats,confs=confs,instate=instate,cn=CN,yrs=YRS,dist=dist,catn=[[k,l] for k,l,_,_ in CATS],juco=juco),separators=(',',':')))
print('DIST',dist['bandDraft'],dist['bandMove'],dist['med'])
print('RAD',sorted([(k,v[1]) for k,v in rad.items()],key=lambda x:x[1])[:4],sorted([(k,v[1]) for k,v in rad.items()],key=lambda x:-x[1])[:4])
cc=[c for c in coaches if c['g'].get('all')]
print('GRADES',[(c['name'],c['g']['all'][0],{k:(v[0] if v else None) for k,v in c['g'].items() if k!='all'}) for c in sorted(cc,key=lambda c:-c['g']['all'][1])[:5]])
print('KIRBY',[c['g'] for c in coaches if c['name']=='Kirby Smart'][0],[c['cls'][:3] for c in coaches if c['name']=='Kirby Smart'][0])
print('PROG',[(p['name'],p['g'],p['g5']) for p in progs[:5]])

# ---- recruiting heat map + portal adaptation (an2.json)
heat={}
for k in sorted(FBS):
    h=collections.Counter(r['stateProvince'] for r in P if r['committedTo']==k and r['recruitType']=='HighSchool' and r['stateProvince'])
    h5=collections.Counter(r['stateProvince'] for r in P if r['committedTo']==k and r['recruitType']=='HighSchool' and r['stateProvince'] and r['year']>=2022)
    t=collections.Counter(SS.get(p['origin']) or '?' for p in PO if p['destination']==k)
    t5=collections.Counter(SS.get(p['origin']) or '?' for p in PO if p['destination']==k and p['season']>=2024)
    heat[k]=dict(st=SS.get(k),h=dict(h),h5=dict(h5),t=dict(t),t5=dict(t5))
ad=collections.defaultdict(dict); nat={}
for Y in range(2021,2027):
    tin=collections.Counter(p['destination'] for p in PO if p['season']==Y and p['destination'])
    hs=collections.Counter(r['committedTo'] for r in P if r['year']==Y and r['recruitType']=='HighSchool')
    a_=b_=0
    for k in FBS:
        ti,hi=tin.get(k,0),hs.get(k,0)
        if ti+hi==0: continue
        a_+=ti; b_+=hi
        c_=HC.get((k,Y))
        if c_: ad[c_][Y]=[k,ti,hi]
    nat[Y]=round(a_/(a_+b_),3)
adapt=[[c_,[[y]+v for y,v in sorted(d.items())]] for c_,d in ad.items() if len(d)>=3]
cheat={}
HSk=collections.defaultdict(list)
for r in P:
    if r['recruitType']=='HighSchool' and r['stateProvince']: HSk[(r['committedTo'],r['year'])].append(r['stateProvince'])
POk=collections.defaultdict(list)
for p in PO:
    if p['destination']: POk[(p['destination'],p['season'])].append(SS.get(p['origin']) or '?')
for c in coaches:
    h=collections.Counter(); t=collections.Counter()
    for k in c.get('cls',[]): h.update(HSk.get((k[1],k[0]),[]))
    for x in c['st']:
        for y in range(max(2021,x[1]),x[2]+1): t.update(POk.get((x[0],y),[]))
    if sum(h.values())>=20: cheat[c['name']]=dict(st=SS.get(c['now'] or c['st'][-1][0]),sch=c['now'] or c['st'][-1][0],h=dict(h),t=dict(t),n=[x[0] for x in c['st']])
open(O+'an2.json','w').write(json.dumps(dict(heat=heat,adapt=adapt,nat=nat,cheat=cheat),separators=(',',':')))
print('AN2',len(heat),len(adapt),nat)

