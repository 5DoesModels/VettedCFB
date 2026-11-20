import json,glob,os,collections
D='/home/claude/foundation/raw_box/'; C='/root/cfbd_pull/'
cg=collections.defaultdict(int)   # coach-season games (official team game count)
for c in json.load(open('/home/claude/vetted-cfb/engine/data/coaches.json')):
    for s in c['seasons']: cg[(s['school'],s['year'])]+=s['games']
seen=collections.defaultdict(set); ath=collections.defaultdict(lambda:collections.defaultdict(set))
for f in sorted(glob.glob(D+'gp_*.json')):
    y=int(os.path.basename(f).split('_')[1])
    for g in json.load(open(f)):
        for t in g['teams']:
            seen[(t['team'],y)].add(g['id'])
            for c in t['categories']:
                for ty in c['types']:
                    for x in ty['athletes']: ath[(x['id'],t['team'],y)][g['id']].add(c['name'])
# 1. coverage: FBS team-seasons, games found vs team's official game count
cov=collections.defaultdict(lambda:[0,0,0]); miss=[]
for (t,y),n in cg.items():
    if not 2009<=y<=2025: continue
    k=len(seen.get((t,y),()));c=cov[y];c[0]+=1;c[1]+=n;c[2]+=min(k,n)
    if k<n: miss.append((t,y,k,n))
print('season: FBS teams, official games, games found (capped)')
for y in sorted(cov): print(y,cov[y],f"{100*cov[y][2]/cov[y][1]:.1f}%")
print('team-seasons missing games',len(miss),miss[:15])
# 2. old (season aggregate) vs new (game level) games with any stat
diff=collections.Counter(); ex=[]
for y in range(2009,2026):
    old=json.load(open(f'{C}box_{y}.json'))
    for k,v in old.items():
        a,t=k.split('|',1); n_new=len(ath.get((a,t,y),{})); n_old=v[2]
        d=n_new-n_old; diff[(y>=2019,'same' if d==0 else 'new higher' if d>0 else 'new lower')]+=1
        if d<0 and len(ex)<6: ex.append((y,v[0],t,n_old,n_new))
print('old vs new games-with-any-stat per athlete-season:',dict(diff)); print('examples new lower',ex)
# 3. separation: athlete-games with only special-teams categories
SPEC={'kickReturns','puntReturns','kicking','punting'}
st=collections.Counter()
for k,G in ath.items():
    for cats in G.values():
        st['special-teams only' if cats<=SPEC else 'fumbles only' if cats=={'fumbles'} else 'other']+=1
print('athlete-games by category type',dict(st))
json.dump(dict(cov={y:v for y,v in cov.items()},miss=miss),open('participation_coverage.json','w'))
