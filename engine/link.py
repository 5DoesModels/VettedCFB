import json, re, collections, unicodedata
R=json.load(open('data/recruits.json')); D=json.load(open('data/draft.json'))
def nn(s):
    s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower()
    s=re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?','',s); return re.sub(r'[^a-z]','',s)
byath={}; byname=collections.defaultdict(list)
for i,r in enumerate(R):
    r['i']=i
    if r.get('athleteId'): byath.setdefault(str(r['athleteId']),[]).append(r)
    byname[nn(r['name'])].append(r)
NICK={('chris','beanie'),('olaivavega','vega'),('steve','esteban'),('jartavius','quan')}
def toks(s):
    s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower().replace('(player)','')
    s=re.sub(r'\b(jr|sr|ii|iii|iv|v)\b\.?','',s); return re.sub(r"[^a-z -]",'',s).replace('-',' ').split()
def same(a,b):
    a,b=toks(a),toks(b)
    if not a or not b: return True
    la,lb=''.join(a[1:]),''.join(b[1:])
    if not (la==lb or la.endswith(lb) or lb.endswith(la) or la.startswith(lb) or lb.startswith(la) or a[-1]==b[-1]): return False
    return a[0][0]==b[0][0] or (a[0],b[0]) in NICK or (b[0],a[0]) in NICK
def score(r,d):
    s=0
    if r['committedTo']==d['collegeTeam']: s+=3
    st=(d.get('hometownInfo') or {}).get('state')
    if st and st==r.get('stateProvince'): s+=2
    if r['recruitType']=='HighSchool': s+=0.5
    return s
links={}; how=collections.Counter()
for k,d in enumerate(D):
    # CFBD's athlete ids are sometimes attached to the wrong recruit (Rara Thomas carried Zavion Thomas's id).
    # Only trust an id match when the names agree (same last name, same first initial, or a known nickname).
    c=[r for r in byath.get(str(d.get('collegeAthleteId')),[]) if same(d['name'],r['name']) or (toks(d['name'])[-1:]==toks(r['name'])[-1:] and d.get('collegeTeam')==r.get('committedTo'))]
    if c:
        r=max(c,key=lambda r:(r['recruitType']=='HighSchool',r['year'])); links[k]=r['i']; how['id']+=1; continue
    c=[r for r in byname.get(nn(d['name']),[]) if 2<=d['year']-r['year']<=8]
    if not c: how['none']+=1; continue
    c.sort(key=lambda r:-score(r,d))
    best=c[0]; sc=score(best,d)
    if len(c)>1 and score(c[1],d)==sc: how['ambig']+=1; continue
    if sc>=2 or len(c)==1 and sc>=0.5: links[k]=best['i']; how['name']+=1
    else: how['weak']+=1
print(how)
for y0,y1 in ((2010,2014),(2015,2019),(2020,2026)):
    ks=[k for k,d in enumerate(D) if y0<=d['year']<=y1]; print(y0,y1,len(ks),round(sum(k in links for k in ks)/len(ks),3))
json.dump({str(k):v for k,v in links.items()},open('data/links.json','w'))
# unmatched sample
um=[d for k,d in enumerate(D) if k not in links]
print([ (d['year'],d['round'],d['name'],d['collegeTeam']) for d in um if d['round']==1][:25])
