import json, collections, math
R=json.load(open('data/recruits.json')); D=json.load(open('data/draft.json')); L={int(k):v for k,v in json.load(open('data/links.json')).items()}
C=json.load(open('data/coaches.json'))
for i,r in enumerate(R): r['i']=i
POS={'PRO':'QB','DUAL':'QB','QB':'QB','RB':'RB','APB':'RB','FB':'RB','WR':'WR','TE':'TE','OT':'OL','OG':'OL','OC':'OL','IOL':'OL','DT':'DL','DL':'DL','SDE':'EDGE','WDE':'EDGE','EDGE':'EDGE',
     'ILB':'LB','OLB':'LB','LB':'LB','CB':'DB','S':'DB','ATH':'ATH','K':'ST','P':'ST','LS':'ST'}
# Tier points (owner, Nov 19 2026: a draft pick is substantial, a top pick is huge; credit depends on expectations)
def tier(d):
    if d is None: return 'Undrafted',0
    o=d['overall']
    if o<=10: return 'Top 10 pick',100
    if d['round']==1: return 'First round',60
    if d['round']==2: return 'Second round',35
    if d['round']==3: return 'Third round',20
    if d['round']<=5: return 'Rounds 4-5',10
    return 'Rounds 6-7',5
drafted={v:D[k] for k,v in L.items()}
CLS=range(2009,2021)   # classes with a full draft window through the 2026 draft
pool=[r for r in R if r['year'] in CLS and r['committedTo'] and r['recruitType'] in ('HighSchool','JUCO','PrepSchool')]
for r in pool:
    r['pg']=POS.get(r['position'],'ATH'); d=drafted.get(r['i'])
    if d and not (r['year']+1<=d['year']<=r['year']+8): d=None
    r['tier'],r['pts']=tier(d); r['d']=d
    r['bucket']=(r['recruitType']!='HighSchool', r['stars'] or 0, min(9,int(((r['rating'] or 0.7)-0.70)*30)) if (r['stars'] or 0)<5 else 9)
# Expected points: by type / stars / rating slice, smoothed toward the star-level mean; position adjustment as a ratio
def mean(xs): return sum(xs)/len(xs) if xs else 0
by=collections.defaultdict(list); bys=collections.defaultdict(list); bpos=collections.defaultdict(list)
for r in pool: by[r['bucket']].append(r['pts']); bys[r['bucket'][:2]].append(r['pts'])
K=150
E0={}
for r in pool:
    b=r['bucket']; n=len(by[b]); E0[r['i']]=(sum(by[b])+K*mean(bys[b[:2]]))/(n+K)
for r in pool: bpos[(r['pg'],r['bucket'][1])].append((r['pts'],E0[r['i']]))
PF={k:(sum(a for a,_ in v)+50)/(sum(b for _,b in v)+50) for k,v in bpos.items()}
for r in pool: r['exp']=E0[r['i']]*PF[(r['pg'],r['bucket'][1])]; r['pae']=r['pts']-r['exp']
print('pool',len(pool),'drafted',sum(1 for r in pool if r['d']), 'sum pts',sum(r['pts'] for r in pool),'sum exp',round(sum(r['exp'] for r in pool)))
st=collections.defaultdict(list)
for r in pool: st[(r['recruitType'],r['stars'])].append(r)
print('Type stars n  drafted%  R1%  top10%  avg pts')
for k in sorted(st,key=lambda k:(k[0],k[1] or 0)):
    v=st[k]; n=len(v)
    print(k,n,f"{100*sum(1 for r in v if r['d'])/n:.1f}% {100*sum(1 for r in v if r['d'] and r['d']['round']==1)/n:.2f}% {100*sum(1 for r in v if r['d'] and r['d']['overall']<=10)/n:.2f}% {mean([r['pts'] for r in v]):.2f}")
json.dump([{k:r[k] for k in ('i','name','year','recruitType','stars','rating','position','pg','committedTo','stateProvince','city','tier','pts','exp','pae','athleteId')}|{'draftTeam':r['d']['collegeTeam'] if r['d'] else None,'draftYear':r['d']['year'] if r['d'] else None,'overall':r['d']['overall'] if r['d'] else None,'nfl':r['d']['nflTeam'] if r['d'] else None} for r in pool],open('data/pool.json','w'))
