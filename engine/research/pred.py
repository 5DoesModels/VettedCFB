import json, collections, sys
E=sys.argv[1]; O='/home/claude/concept/'
X=json.load(open(E+'/data/pool2.json')); P=X['players']
C=json.load(open(E+'/data/coaches.json')); FBS=set()
for c in C:
    for s in c['seasons']:
        if s['year'] in (2025,2026): FBS.add(s['school'])
def moved(r): return any(m[1] and m[1]!=r['committedTo'] for m in r['mv'])
def last(r):
    d=[m[1] for m in r['mv'] if m[1]]; return d[-1] if d else r['committedTo']
def slc(r): return min(9,int(((r['rating'] or 0.7)-0.70)*30)) if (r['stars'] or 0)<5 else 9
import os
HOLD=os.environ.get('HOLD')
mat=[r for r in P if r['k']==8 and (not HOLD or r['year']<=2015)]   # classes with all 8 draft years observed
# --- draft and first-round base rates by (hs, stars, slice), smoothed to star level
def rates(pool,f,K):
    by=collections.defaultdict(lambda:[0,0]); bs=collections.defaultdict(lambda:[0,0])
    for r in pool:
        b=(r['recruitType']!='HighSchool',r['stars'] or 0,slc(r)); y=f(r)
        by[b][0]+=y; by[b][1]+=1; bs[b[:2]][0]+=y; bs[b[:2]][1]+=1
    def p(r):
        b=(r['recruitType']!='HighSchool',r['stars'] or 0,slc(r)); s=bs.get(b[:2],[0,1]); m=s[0]/max(1,s[1]); a=by.get(b,[0,0])
        return (a[0]+K*m)/(a[1]+K)
    return p
isd=lambda r:1 if r['draftYear'] else 0
isr1=lambda r:1 if r['tier'] in('First round','Top 10 pick') else 0
pd0=rates(mat,isd,150); pr0=rates(mat,isr1,300)
def posf(pool,f,p0,K):
    a=collections.defaultdict(lambda:[0,0])
    for r in pool: x=a[(r['pg'],r['stars'] or 0)]; x[0]+=f(r); x[1]+=p0(r)
    return {k:(v[0]+K)/(v[1]+K) for k,v in a.items()}
PFd=posf(mat,isd,pd0,15); PFr=posf(mat,isr1,pr0,4)
def pd(r): return pd0(r)*PFd.get((r['pg'],r['stars'] or 0),1)
def pr(r): return pr0(r)*PFr.get((r['pg'],r['stars'] or 0),1)
# --- signing-school factor: do players who SIGN here get drafted more than expected? (complete classes)
sf=collections.defaultdict(lambda:[0,0])
for r in mat: x=sf[r['committedTo']]; x[0]+=isd(r); x[1]+=pd(r)
SFd={k:(a+8)/(b+8) for k,(a,b) in sf.items()}
# school x position draft factor, shrunk toward the school's overall factor (weight = 4 expected picks)
sfp=collections.defaultdict(lambda:[0,0])
for r in mat: x=sfp[(r['committedTo'],r['pg'])]; x[0]+=isd(r); x[1]+=pd(r)
def fdp(s_,g): a,b=sfp.get((s_,g),(0,0)); return (a+8*SFd.get(s_,1))/(b+8)
# --- transfer: moved schools at least once, classes 2020-2022 (portal era), by stars and position, then school factor
T=[r for r in P if 2020<=r['year']<=2022]
tb=collections.defaultdict(lambda:[0,0]); ts=collections.defaultdict(lambda:[0,0])
for r in T:
    s=r['stars'] or 0; x=tb[(s,r['pg'])]; x[0]+=moved(r); x[1]+=1; y=ts[s]; y[0]+=moved(r); y[1]+=1
def pt0(s,g):
    a=tb.get((s,g),[0,0]); m=ts[s][0]/ts[s][1]; return (a[0]+40*m)/(a[1]+40)
tf=collections.defaultdict(lambda:[0,0])
for r in T: x=tf[r['committedTo']]; x[0]+=moved(r); x[1]+=pt0(r['stars'] or 0,r['pg'])
SFt={k:(a+10)/(b+10) for k,(a,b) in tf.items()}
tft=collections.defaultdict(lambda:[0,0])
for r in T: x=tft[(r['committedTo'],'hi' if (r['stars'] or 0)>=4 else 'lo')]; x[0]+=moved(r); x[1]+=pt0(r['stars'] or 0,r['pg'])
def ftt(s_,t): a,b=tft.get((s_,t),(0,0)); return (a+8*SFt.get(s_,1))/(b+8)
cap=lambda x:max(0.001,min(0.9,x))
# --- backtest on 2016-2018 classes (known outcomes): calibration by predicted decile
bt=[r for r in P if 2016<=r['year']<=2018]
pairs=sorted([(cap(pd(r)*SFd.get(r['committedTo'],1)),isd(r)) for r in bt])
dec=[];n=len(pairs)
for i in range(5):
    ch=pairs[i*n//5:(i+1)*n//5]; dec.append([round(100*sum(p for p,_ in ch)/len(ch),1),round(100*sum(y for _,y in ch)/len(ch),1)])
top=pairs[-len(pairs)//10:]; print('backtest quintiles pred vs actual %',dec,'top decile',round(100*sum(p for p,_ in top)/len(top),1),round(100*sum(y for _,y in top)/len(top),1))
# --- transfer effect: drafted vs expected for players who moved vs stayed (classes 2019-2022, expectation scaled to draft years seen)
M=X['M']
te=collections.defaultdict(lambda:[0,0])
for r in [r for r in P if 2019<=r['year']<=2022]:
    key=('moved' if moved(r) else 'stayed', 'hi' if (r['stars'] or 0)>=4 else 'lo')
    e=pd(r)*SFd.get(r['committedTo'],1)*M[r['k']]
    te[key][0]+=isd(r); te[key][1]+=e
TE={k[0]+'_'+k[1]:round(a/b,3) for k,(a,b) in te.items()}
print('transfer effect actual/expected',TE,{k:[v[0],round(v[1],1)] for k,v in te.items()})
# --- current players still in college: classes 2022-2026, not yet drafted
# who is still in college: on a 2026 roster (by athlete id or name). Signees from 2025 or earlier who aren't are done
# (they went undrafted in the 2026 draft or left football), so they drop out of predictions.
import re as _re
_ros=json.load(open('/root/cfbd_pull/ros_2026.json'))
_nm=lambda s:_re.sub(r'[^a-z]','',_re.sub(r'\b(jr|sr|ii|iii|iv|v)\b','',(s or '').lower()))
ONID={str(x['id']) for x in _ros}; ONNM={_nm((x.get('firstName') or '')+' '+(x.get('lastName') or '')) for x in _ros}
def oncampus(r): return r['year']>=2026 or str(r.get('athleteId')) in ONID or _nm(r['name']) in ONNM
cur0=[r for r in P if r['year']>=2022 and not r['draftYear'] and r['recruitType'] in ('HighSchool','JUCO','PrepSchool')]
cur=[r for r in cur0 if oncampus(r)]
print('still in college',len(cur),'of',len(cur0),'| done (no 2026 roster):',len(cur0)-len(cur),[r['name'] for r in cur0 if r['name'] in ('Aaron Anderson','Garrett Nussmeier','Arch Manning')])
# ---- transfer odds proof: model built on 2020-22 signees; test on 2023 signees (never seen by the model)
OOS=[r for r in P if r['year']==2023 and r['recruitType'] in ('HighSchool','JUCO','PrepSchool')]
tp=sorted([(cap(pt0(r['stars'] or 0,r['pg'])*ftt(r['committedTo'],'hi' if (r['stars'] or 0)>=4 else 'lo')),moved(r)) for r in OOS])
tq=[];n_=len(tp)
for i in range(5):
    ch=tp[i*n_//5:(i+1)*n_//5]; tq.append([round(100*sum(p for p,_ in ch)/len(ch),1),round(100*sum(y for _,y in ch)/len(ch),1),len(ch)])
TCUT=tp[int(n_*0.9)][0]; topd=[y for p,y in tp if p>=TCUT]
TPROOF=dict(q=tq,cut=round(TCUT,3),top=[sum(topd),len(topd)],base=round(100*sum(y for _,y in tp)/n_,1),n=n_)
print('TRANSFER PROOF',TPROOF)
GL=['QB','RB','WR','TE','OL','DL','EDGE','LB','DB','ATH','ST']
SUBP={'CB':'CB','S':'S','OT':'OT','OG':'IOL','OC':'IOL','IOL':'IOL'}
rows=[]
def rem(p,k): return p*(1-M[k])/(1-p*M[k])
for r in cur:
    k=r['k']; f=fdp(last(r),r['pg']); full=cap(pd(r)*f); d=rem(full,k)
    nxt=full*(M[min(8,k+1)]-M[k])/(1-full*M[k])
    mv=moved(r); t0=pt0(r['stars'] or 0,r['pg']); ft=ftt(r['committedTo'],'hi' if (r['stars'] or 0)>=4 else 'lo')
    t=1.0 if mv else cap(t0*ft)
    rows.append([r['name'],r['year'],GL.index(r['pg']),r['stars'] or 0,round(r['rating'] or 0,4),r['stateProvince'] or '',r['city'] or '',r['committedTo'],last(r),round(d,4),round(pd(r),4),round(t,3),1 if mv else 0,[[m[0],m[1]] for m in r['mv']],k,round(nxt,4),round(t0,3),round(ft,3),SUBP.get(r.get('position'),''),round(full,4),round(f,3),r['recruitType']])
# --- 2027 committed recruits (not signed yet)
POS={'PRO':'QB','DUAL':'QB','QB':'QB','RB':'RB','APB':'RB','FB':'RB','WR':'WR','TE':'TE','OT':'OL','OG':'OL','OC':'OL','IOL':'OL','DT':'DL','DL':'DL','SDE':'EDGE','WDE':'EDGE','EDGE':'EDGE','ILB':'LB','OLB':'LB','LB':'LB','CB':'DB','S':'DB','ATH':'ATH','K':'ST','P':'ST','LS':'ST'}
import os as _os
R27p='/root/cfbd_pull/r2027.json'
n27=0
if _os.path.exists(R27p):
    FL={f['name']:f for f in json.load(open(E+'/flips_2027.json'))['flips']}
    for x in json.load(open(R27p)):
        if not x.get('committedTo'): continue
        f=FL.get(x['name'])
        if f and x['committedTo']==f['from']: x['committedTo']=f['to']
        r=dict(name=x['name'],year=2027,recruitType='HighSchool',stars=x.get('stars'),rating=x.get('rating'),position=x.get('position'),committedTo=x['committedTo'],stateProvince=x.get('stateProvince'),city=x.get('city'),mv=[])
        r['pg']=POS.get(r['position'],'ATH')
        st=r['stars'] or 0; f=fdp(r['committedTo'],r['pg']); full=cap(pd(r)*f)
        t0=pt0(st,r['pg']); ft=ftt(r['committedTo'],'hi' if st>=4 else 'lo')
        rows.append([r['name'],2027,GL.index(r['pg']) if r['pg'] in GL else 9,st,round(r['rating'] or 0,4),r['stateProvince'] or '',r['city'] or '',r['committedTo'],r['committedTo'],round(full,4),round(pd(r),4),round(cap(t0*ft),3),0,[],0,0.0,round(t0,3),round(ft,3),SUBP.get(r['position'],''),round(full,4),round(f,3),'HighSchool']); n27+=1
print('2027 commits scored',n27)
# calculator tables: by stars x position, average base rates for HS signees in mature classes (rating varies within stars)
calc={}
for s in (0,2,3,4,5):
    for g in GL[:9]:
        grp=[r for r in mat if (r['stars'] or 0)==s and r['pg']==g and r['recruitType']=='HighSchool']
        if len(grp)<20: continue
        calc[f'{s}{g}']=[round(sum(pd(r) for r in grp)/len(grp),4),round(sum(pr(r) for r in grp)/len(grp),5),round(pt0(s,g),3),len(grp)]
GP=['QB','RB','WR','TE','OL','DL','EDGE','LB','DB']
fac={k:[round(SFd.get(k,1),3),round(SFt.get(k,1),3),sf[k][0],round(sf[k][1],1),tf[k][0] if k in tf else 0,round(tf[k][1],1) if k in tf else 0,
   {g:[round(fdp(k,g),3),sfp[(k,g)][0],round(sfp[(k,g)][1],1)] for g in GP},round(ftt(k,'hi'),3),round(ftt(k,'lo'),3)] for k in FBS if k in sf and sf[k][1]>=3}
BT=json.load(open(O+'bt.json')) if os.path.exists(O+'bt.json') else dec
if HOLD: json.dump(dec,open(O+'bt.json','w'))
# ---- badges. Thresholds from the full (whole-career) draft odds, by position group
import statistics as _st
_f=collections.defaultdict(list)
for x in rows:
    if x[3]==4: _f[(x[1],x[2])].append(x[9])
F4={k:_st.median(v) for k,v in _f.items() if len(v)>=8}
_g=collections.defaultdict(list)
for x in rows: _g[(x[1],x[2],x[3])].append(x[9])
S2={k:_st.median(v) for k,v in _g.items() if len(v)>=20}
TT=sorted(x[11] for x in rows if not x[12]); TTOP=TT[int(len(TT)*0.9)] if TT else 1
def badges(x):
    b=[]; m4=F4.get((x[1],x[2]))
    if x[3]<=3 and m4 and x[9]>=m4: b.append('dia')                     # beats the typical 4-star at his position in his class
    if x[9]>=0.6: b.append('lock')                                      # 60%+ career draft odds
    if x[3]<=3 and 'dia' not in b and x[9]>=2*S2.get((x[1],x[2],x[3]),9): b.append('sleeper')      # 2x the typical odds for his stars and position
    if x[20]>=1.35: b.append('fit')                                      # school develops his position 35%+ above normal
    if x[15]>=0.2: b.append('next')                                      # 20%+ to go in the next draft
    if not x[12] and x[11]>=TTOP: b.append('watch')                      # top 10% transfer odds
    if x[12]: b.append('moved')
    if x[21]=='JUCO': b.append('juco')
    return b
for x in rows: x.append(badges(x))
BC=collections.Counter(b for x in rows for b in x[22]); print('BADGES',dict(BC),len(F4))
# ---- v1.29: individual draft and transfer probabilities are NOT published (failed validation, JC decision D1).
# The public file carries player facts plus raw historical cohort counts only. Full model rows kept for research, off-site.
json.dump(dict(rows=rows,calc=calc,fac=fac,te=TE,tproof=TPROOF),open('/home/claude/foundation/pred_internal_v128.json','w'))
RT=lambda r:'H' if r['recruitType']=='HighSchool' else ('J' if r['recruitType']=='JUCO' else None)
dco=collections.defaultdict(lambda:[0,0])            # drafted / total, classes 2002-2018 (all 8 draft years observed)
for r in mat:
    t=RT(r)
    if t: x=dco[f"{t}{r['stars'] or 0}{r['pg']}"]; x[0]+=isd(r); x[1]+=1
tco=collections.defaultdict(lambda:[0,0])            # portal record with a new school / total, classes 2020-2022
for r in T:
    t=RT(r)
    if t: x=tco[f"{t}{r['stars'] or 0}{r['pg']}"]; x[0]+=moved(r); x[1]+=1
# v1.34 (JC, Nov. 21): school groups for every current player: signees of his signing school with his route, stars and position.
# Draft: classes in mat (all draft years observed). Transfers: classes in T. Shown at 5+ players; under 20 labeled a small group.
_need={f"{x[7]}|{'H' if x[21]=='HighSchool' else 'J'}{x[3] or 0}{x[2] if isinstance(x[2],str) else GL[x[2]]}" for x in rows if x[21] in ('HighSchool','JUCO')}
sco=collections.defaultdict(lambda:[0,0,0,0])
for r in mat:
    t=RT(r)
    if t:
        k=f"{r['committedTo']}|{t}{r['stars'] or 0}{r['pg']}"
        if k in _need: x=sco[k]; x[0]+=isd(r); x[1]+=1
for r in T:
    t=RT(r)
    if t:
        k=f"{r['committedTo']}|{t}{r['stars'] or 0}{r['pg']}"
        if k in _need: x=sco[k]; x[2]+=moved(r); x[3]+=1
sco={k:v for k,v in sco.items() if v[1]>=5 or v[3]>=5}
spn=collections.Counter((r['committedTo'],r['pg']) for r in mat)
sp={k:{g:[spn[(k,g)],sfp[(k,g)][0],round(sfp[(k,g)][1],1)] for g in GP if spn[(k,g)]} for k in FBS if k in sf and sf[k][1]>=3}
DY=[min(r['year'] for r in mat),max(r['year'] for r in mat)]; TY=[min(r['year'] for r in T),max(r['year'] for r in T)]
pub=[[x[0],x[1],x[2],x[3],x[4],x[5],x[6],x[7],x[8],x[12],x[13],x[18],x[21],[b for b in x[22] if b in ('moved','juco')]] for x in rows]
out=dict(v=2,done=len(cur0)-len(cur),rows=pub,g=GL,dco=dco,tco=tco,sco=sco,sp=sp,dy=DY,ty=TY)
s=json.dumps(out,separators=(',',':')); open(O+'pred.json','w').write(s)
print(len(rows),len(s)//1024,'KB','dy',DY,'ty',TY,'H4WR',dco.get('H4WR'),tco.get('H4WR'),'LSU DB',sp.get('LSU',{}).get('DB'))
print('4WR',calc.get('4WR'),'3WR',calc.get('3WR'),'5QB',calc.get('5QB'))
for g,st in (('WR',4),('OL',3),('QB',4)):
    t='hi' if st>=4 else 'lo'
    print(g,st,'draft top',[k for k,_ in sorted(fac.items(),key=lambda kv:-kv[1][6][g][0])[:4]],'stay top',[k for k,_ in sorted(fac.items(),key=lambda kv:kv[1][7 if t=='hi' else 8])[:4]]); print([r for r in rows if r[0] in ('Jabari Mack','Kylan Billiot')])
