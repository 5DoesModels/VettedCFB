import json,collections,math,sys
src=open('/home/claude/concept/pred.py').read(); cut=src.index('# --- transfer: moved schools')
sys.argv=['x','/home/claude/vetted-cfb/engine']; exec(src[:cut])   # defines mat, pd, sf, SFd, sfp, fdp (official v1.28 code, read-only)
from scipy.stats import chi2
def ci(a,e,lvl=0.90):   # exact Poisson interval for actual/expected
    lo=0 if a==0 else chi2.ppf((1-lvl)/2,2*a)/2; hi=chi2.ppf(1-(1-lvl)/2,2*a+2)/2; return round(lo/e,2),round(hi/e,2)
C=json.load(open('/home/claude/vetted-cfb/engine/data/coaches.json'))
hc=collections.defaultdict(list)
for c in C:
    for s in c['seasons']: hc[(s['school'],s['year'])].append(f"{c['firstName']} {c['lastName']}")
now={k[0]:v[0] for k,v in hc.items() if k[1]==2026}
GP=['QB','RB','WR','TE','OL','DL','EDGE','LB','DB']
grp=collections.defaultdict(list)
for r in mat: grp[(r['committedTo'],r['pg'])].append(r)
rows=[]
for (s,g),L in grp.items():
    if g not in GP or s not in now: continue
    a=sum(isd(r) for r in L); e=sum(pd(r) for r in L); f=fdp(s,g)
    if e<=0: continue
    era={}
    for nm_,lo,hi in (('2002-09',2002,2009),('2010-18',2010,2018)):
        M_=[r for r in L if lo<=r['year']<=hi]; era[nm_]=[sum(isd(r) for r in M_),round(sum(pd(r) for r in M_),1)]
    picks=[r for r in L if isd(r)]
    by=collections.Counter((hc.get((s,r['year'])) or ['unknown'])[0] for r in picks)
    top=by.most_common(1)[0] if by else ('',0)
    rows.append(dict(school=s,pos=g,signees=len(L),drafted=a,expected=round(e,1),ratio=round(a/e,2),shrunk=round(f,2),ci90=ci(a,e),
        era=era,top_coach=top[0],top_coach_share=round(top[1]/a,2) if a else 0,current_coach=now[s],current_coach_picks=by.get(now[s],0),
        classes=[min(r['year'] for r in L),max(r['year'] for r in L)]))
B=lambda r,t=1.35,m=3,key='shrunk':r[key]>=t and r['expected']>=m
q=[r for r in rows if B(r)]
q.sort(key=lambda r:-r['shrunk'])
sens=dict(base=len(q),t125=sum(B(r,1.25) for r in rows),t150=sum(B(r,1.5) for r in rows),m2=sum(B(r,m=2) for r in rows),m5=sum(B(r,m=5) for r in rows),raw135=sum(B(r,key='ratio') for r in rows))
for r in q:
    r['stable']=dict(at_1_25=B(r,1.25),at_1_50=B(r,1.5),exp5=B(r,m=5),raw=B(r,key='ratio'))
    e1,e2=r['era']['2002-09'],r['era']['2010-18']
    r['era_ratio']=[round(e1[0]/e1[1],2) if e1[1] else None,round(e2[0]/e2[1],2) if e2[1] else None]
    r['ci_excludes_1']=r['ci90'][0]>1
# era-to-era correlation for all combos with 2+ expected in each era
import statistics as st
pairs=[(r['era']['2002-09'][0]/r['era']['2002-09'][1],r['era']['2010-18'][0]/r['era']['2010-18'][1]) for r in rows if r['era']['2002-09'][1]>=2 and r['era']['2010-18'][1]>=2]
corr=st.correlation([x for x,_ in pairs],[y for _,y in pairs])
out=dict(rule='shrunk school-position factor >= 1.35 AND expected picks >= 3; classes 2002-2018 (all eight draft years observed); current FBS schools',
         qualifying=q,sensitivity=sens,era_correlation=dict(r=round(corr,2),n=len(pairs)),total_combos=len(rows))
json.dump(out,open('great_fit_report.json','w'),indent=1,default=lambda o: bool(o) if hasattr(o,'dtype') or type(o).__name__=='bool_' else float(o))
print(len(rows),'combos;',len(q),'qualify. sensitivity',sens,'era corr',round(corr,2),len(pairs))
print(f"{'school':18}{'pos':5}{'sign':>5}{'dr':>4}{'exp':>6}{'ratio':>6}{'shr':>6}{'90% CI':>12}{'02-09':>7}{'10-18':>7}  top coach share | current HC picks | CI>1 | @1.5")
for r in q: print(f"{r['school']:18}{r['pos']:5}{r['signees']:>5}{r['drafted']:>4}{r['expected']:>6}{r['ratio']:>6}{r['shrunk']:>6}{str(r['ci90']):>12}{str(r['era_ratio'][0]):>7}{str(r['era_ratio'][1]):>7}  {r['top_coach'][:16]} {r['top_coach_share']} | {r['current_coach'][:14]} {r['current_coach_picks']} | {r['ci_excludes_1']} | {r['stable']['at_1_50']}")
