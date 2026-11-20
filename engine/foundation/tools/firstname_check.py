import json,collections,re,random
cn=lambda s:re.sub(r'[^a-z]','',(s or '').lower())
R=json.load(open('/home/claude/vetted-cfb/engine/data/recruits.json'))
key={(r['name'],r['year'],r['committedTo']):r for r in R}
ath=collections.defaultdict(list)
for y in range(2004,2027):
    for x in json.load(open(f'/root/cfbd_pull/ros_{y}.json')): x['season']=y; ath[x['id']].append(x)
X=json.load(open('build/FND-0.2/exceptions.json'))
H=[h for h in X['held_name_mismatch'] if h['reason'].startswith('recruit name')]
out=collections.Counter();ex=collections.defaultdict(list)
for h in H:
    r=key.get((h['recruit'],h['year'],h['school']));x=ath[h['athlete_id']][-1]
    toks=set(cn(t) for t in re.split(r'[\s\-]+',h['recruit']))
    rf=cn(x['firstName'])
    home=(r and r['recruitType']=='HighSchool' and x.get('homeState'))
    if rf in toks: v='alias: roster first name is another part of his recruiting name'
    elif home and cn(x.get('homeCity'))==cn(r['city']) and x['homeState'].upper()==(r['stateProvince'] or '').upper(): v='likely alias: same hometown (city and state)'
    elif home and x['homeState'].upper()!=(r['stateProvince'] or '').upper(): v='likely different person: hometown in another state'
    elif home: v='unclear: same state, different city'
    else: v='unclear: no hometown to compare (JUCO/prep record or missing)'
    out[v]+=1;ex[v].append(f"{h['recruit']} ({h['year']}, {h['school']}) vs roster {h['roster_names'][0]}")
print(len(H));[print(v,c) for v,c in out.most_common()]
random.seed(4)
for v in ex: print('--',v);[print('   ',e) for e in random.sample(ex[v],min(4,len(ex[v])))]
json.dump(dict(total=len(H),counts=out,examples={k:v[:15] for k,v in ex.items()}),open('firstname_check.json','w'),indent=1)
