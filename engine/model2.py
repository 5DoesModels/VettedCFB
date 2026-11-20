# Vetted CFB model v2: classes 2008-2026, expected-to-date for young classes, transfer portal links.
import json, collections, re, unicodedata
R=json.load(open('data/recruits.json')); D=json.load(open('data/draft.json')); L={int(k):v for k,v in json.load(open('data/links.json')).items()}
PO=json.load(open('data/portal.json')); LAST=max(d['year'] for d in D)  # last draft in the data (2026)
for i,r in enumerate(R): r['i']=i
POS={'PRO':'QB','DUAL':'QB','QB':'QB','RB':'RB','APB':'RB','FB':'RB','WR':'WR','TE':'TE','OT':'OL','OG':'OL','OC':'OL','IOL':'OL','DT':'DL','DL':'DL','SDE':'EDGE','WDE':'EDGE','EDGE':'EDGE',
     'ILB':'LB','OLB':'LB','LB':'LB','CB':'DB','S':'DB','ATH':'ATH','K':'ST','P':'ST','LS':'ST'}
def tier(d):
    if d is None: return 'Undrafted',0
    o=d['overall']
    if o<=10: return 'Top 10 pick',100
    if d['round']==1: return 'First round',60
    if d['round']==2: return 'Second round',35
    if d['round']==3: return 'Third round',20
    if d['round']<=5: return 'Rounds 4-5',10
    return 'Rounds 6-7',5
# Wrong draft-pick matches found in JC's review (linkfix.json): drop them
FIX=json.load(open('linkfix.json')); BAD={(u['name'],u['year'],u['school'],u['draftYear'],u['overall']) for u in FIX['unlink']}
nb=len(L); L={k:v for k,v in L.items() if (R[v]['name'],R[v]['year'],R[v]['committedTo'],D[k]['year'],D[k]['overall']) not in BAD}
print('unlinked',nb-len(L),'of',len(BAD))
# A recruit can pick up two draft picks with the same name (e.g. Robert Griffin III and guard Robert Griffin, both Baylor 2012).
# Keep the pick whose position fits the recruit's, then the one from his signing school, then the earlier pick.
DPOS={'Quarterback':'QB','Running Back':'RB','Fullback':'RB','Wide Receiver':'WR','Tight End':'TE','Offensive Tackle':'OL','Offensive Guard':'OL','Center':'OL','Offensive Line':'OL',
      'Defensive Tackle':'DL','Defensive End':'EDGE','Defensive Edge':'EDGE','Outside Linebacker':'LB','Inside Linebacker':'LB','Linebacker':'LB','Cornerback':'DB','Safety':'DB','Defensive Back':'DB',
      'Kicker':'ST','Punter':'ST','Long Snapper':'ST'}
NEAR={frozenset(x) for x in (('EDGE','LB'),('EDGE','DL'),('DB','LB'),('RB','WR'),('WR','TE'),('TE','OL'),('DL','OL'))}
def pfit(r,d):
    a=POS.get(r['position'],'ATH'); b=DPOS.get(d['position'])
    if a=='ATH' or b is None: return 1
    return 2 if a==b else 1 if frozenset((a,b)) in NEAR else 0
byrec=collections.defaultdict(list)
for k,v in L.items(): byrec[v].append(k)
for v,ks in byrec.items():
    if len(ks)>1:
        keep=max(ks,key=lambda k:(pfit(R[v],D[k]),D[k]['collegeTeam']==R[v]['committedTo'],-D[k]['year'],-D[k]['overall']))
        print('two picks for',R[v]['name'],R[v]['year'],'-> kept',D[keep]['year'],D[keep]['overall'],D[keep]['name'])
        for k in ks:
            if k!=keep: del L[k]
drafted={v:D[k] for k,v in L.items()}
SA={(x['name'],x['year'],x['school']) for x in json.load(open('setaside.json'))['players']}   # passed away / career ended by a legal case
pool=[r for r in R if 2002<=r['year']<=LAST and r['committedTo'] and r['recruitType'] in ('HighSchool','JUCO','PrepSchool') and (r['name'],r['year'],r['committedTo']) not in SA]
print('set aside',sum(1 for r in R if (r['name'],r['year'],r['committedTo']) in SA))
for r in pool:
    r['pg']=POS.get(r['position'],'ATH'); d=drafted.get(r['i'])
    if d and not (r['year']+1<=d['year']<=r['year']+8): d=None
    r['tier'],r['pts']=tier(d); r['d']=d
    r['k']=min(8,LAST-r['year'])          # draft years observed so far (0 = none yet)
    r['bucket']=(r['recruitType']!='HighSchool', r['stars'] or 0, min(9,int(((r['rating'] or 0.7)-0.70)*30)) if (r['stars'] or 0)<5 else 9)
# Fit expected points on MATURE classes only (all 8 draft years observed: 2008-2018)
mat=[r for r in pool if r['k']==8]
def mean(xs): return sum(xs)/len(xs) if xs else 0
by=collections.defaultdict(list); bys=collections.defaultdict(list)
for r in mat: by[r['bucket']].append(r['pts']); bys[r['bucket'][:2]].append(r['pts'])
K=150; allmean=mean([r['pts'] for r in mat])
def e0(b):
    n=len(by[b]); sm=mean(bys[b[:2]]) if bys[b[:2]] else allmean
    return (sum(by[b])+K*sm)/(n+K)
bpos=collections.defaultdict(lambda:[0,0])
for r in mat: x=bpos[(r['pg'],r['bucket'][1])]; x[0]+=r['pts']; x[1]+=e0(r['bucket'])
PF={k:(a+50)/(b+50) for k,(a,b) in bpos.items()}
# Maturity: share of a class's draft points earned by draft-year offset (from mature classes)
off=collections.Counter()
for r in mat:
    if r['d']: off[r['d']['year']-r['year']]+=r['pts']
tot=sum(off.values()); M=[sum(off[j] for j in range(1,k+1))/tot for k in range(9)]
for r in pool:
    r['full']=e0(r['bucket'])*PF.get((r['pg'],r['bucket'][1]),1); r['exp']=r['full']*M[r['k']]; r['pae']=r['pts']-r['exp']
print('maturity by years observed',[round(m,3) for m in M])
# Transfer portal -> recruit links (name + origin school, transfer after signing)
def nn(s):
    s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower()
    s=re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?','',s); return re.sub(r'[^a-z]','',s)
byname=collections.defaultdict(list)
for r in pool: byname[nn(r['name'])].append(r)
moves=collections.defaultdict(list); hit=collections.Counter()
for p in sorted(PO,key=lambda p:p['season']):
    c=[r for r in byname.get(nn(f"{p['firstName']} {p['lastName']}"),[]) if r['year']<p['season']<=r['year']+7]
    if not c: hit['none']+=1; continue
    def sc(r): return 3*(r['committedTo']==p['origin'] or any(m[1]==p['origin'] for m in moves[r['i']]))+(r['stars']==p['stars'])+ (POS.get(r['position'])==POS.get(p['position']))
    c.sort(key=lambda r:-sc(r))
    if sc(c[0])<3 or (len(c)>1 and sc(c[1])==sc(c[0])): hit['weak']+=1; continue
    moves[c[0]['i']].append([p['season'],p['destination'] or '',p['origin']]); hit['ok']+=1
print('portal links',hit)
for r in pool: r['mv']=[[m[0],m[1]] for m in moves.get(r['i'],[])]
json.dump(dict(M=M,last=LAST,players=[{k:r[k] for k in ('i','name','year','recruitType','stars','rating','position','pg','committedTo','stateProvince','city','tier','pts','exp','full','pae','k','mv','athleteId')}|{'draftTeam':r['d']['collegeTeam'] if r['d'] else None,'draftYear':r['d']['year'] if r['d'] else None,'overall':r['d']['overall'] if r['d'] else None,'round':r['d']['round'] if r['d'] else None} for r in pool]),open('data/pool2.json','w'))
print('pool',len(pool),'by class',sorted(collections.Counter(r['year'] for r in pool).items())[:3],'...')
for y in (2002,2005,2008,2018,2020,2021,2022,2023,2024,2025,2026):
    g=[r for r in pool if r['year']==y]; print(y,len(g),'drafted',sum(1 for r in g if r['d']),'pts',sum(r['pts'] for r in g),'exp-to-date',round(sum(r['exp'] for r in g)))
# --- v2.1: compare each class to its own peers (handles COVID-era draft timing); 2024+ too early to score
X=json.load(open('data/pool2.json')); SC=range(2002,2024)
cls=collections.defaultdict(lambda:[0,0])
for p in X['players']:
    if p['year'] in SC: cls[p['year']][0]+=p['pts']; cls[p['year']][1]+=p['exp']
F={y:(a/b if b else 1) for y,(a,b) in cls.items()}
for p in X['players']:
    if p['year'] in SC: p['exp']=p['exp']*F[p['year']]; p['pae']=p['pts']-p['exp']
    else: p['exp']=None; p['pae']=None
X['classFactor']={y:round(f,3) for y,f in F.items()}
json.dump(X,open('data/pool2.json','w')); print('class factors',X['classFactor'])
