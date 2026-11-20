# Builds/refreshes engine/foundation/identity_resolution.json. Keeps any existing approval status and reviewer notes.
import json,collections,re,os
F='/home/claude/vettedcfb/engine/foundation/identity_resolution.json'
old={c['case_id']:c for c in json.load(open(F))['cases']} if os.path.exists(F) else {}
nm=lambda s:re.sub(r'[^a-z]','',re.sub(r'\b(jr|sr|ii|iii|iv|v)\b','',(s or '').lower()))
cn=lambda s:re.sub(r'[^a-z]','',(s or '').lower())
R=json.load(open('/home/claude/vetted-cfb/engine/data/recruits.json'));RI={str(r['id']):r for r in R}
D=json.load(open('/home/claude/vetted-cfb/engine/data/draft.json'));DA={str(d['collegeAthleteId']):d for d in D if d.get('collegeAthleteId')}
ath=collections.defaultdict(list)
for y in range(2004,2027):
    for x in json.load(open(f'/root/cfbd_pull/ros_{y}.json')): x['season']=y; ath[x['id']].append(x)
X=json.load(open('build/FND-0.2/exceptions.json'))
def ev(a):
    rows=sorted(ath[a],key=lambda x:x['season']);x=rows[-1]
    d=DA.get(a)
    return dict(athlete_id=a,roster=', '.join(f"{z['team']} {z['season']}" for z in rows),position=x.get('position'),hometown=f"{x.get('homeCity')}, {x.get('homeState')}",
                draft_pick_with_this_id=f"{d['year']} #{d['overall']} {d['collegeTeam']} ({d['name']})" if d else None)
cases=[]
def add(cid,recruit_id,cands,rec,reason,kind):
    r=RI[str(recruit_id)]
    c=dict(case_id=cid,kind=kind,recruit_id=str(recruit_id),recruit=f"{r['name']} · {r['year']} {r['recruitType']} · {r['position']} · {r['city']}, {r['stateProvince']} · signed {r['committedTo']}",
           candidates=[ev(a) for a in cands],decision='link' if rec else 'leave_unresolved',athlete_id=rec,recommendation_reason=reason,status='pending',reviewer_note='')
    if cid in old and old[cid].get('status')!='pending': c.update({k:old[cid][k] for k in ('status','decision','athlete_id','reviewer_note') if k in old[cid]})
    cases.append(c)
add('named-fields','126271',['4362887','232454'],'4362887','Hometown (Kennesaw, GA) and position match; this id was drafted 2021 #11 from Ohio State. The other id is a Georgia fullback from Savannah listed 2009-2018.','judgment')
add('named-jwilliams','122359',['4426388'],'4426388','Hometown (St. Louis) and position match; Ohio State 2019-20, Alabama 2021; this id was drafted 2022 #12. CFBD\'s recruit record points to a different athlete id.','judgment')
add('named-nsmith','122278',['4426331'],'4426331','This id was drafted 2023 #30 from Georgia; position group and seasons fit. Hometown differs (Savannah vs Bradenton) because he played at IMG Academy in Bradenton.','judgment')
add('named-rthomas','116504',['4697844'],'4697844','Hometown (Eufaula, AL) and position match; Mississippi State 2021-22, Georgia 2023-24, Troy 2025. CFBD\'s recruit-id link had pointed at Zavion Thomas.','judgment')
add('named-mayfield','146616',['550373'],'550373','Walk-on recruiting record (no school). Hometown (Austin, TX) and position match; this id was drafted 2018 #1 from Oklahoma.','judgment')
for k,a in enumerate(X['ambiguous_name_school']):
    r=[x for x in R if x['name']==a['recruit'] and x['year']==a['year'] and x['committedTo']==a['school']]
    if not r: continue
    r=r[0];cands=a['athlete_ids']
    good=[c for c in cands if (DA.get(c) and nm(DA[c]['name'])==nm(r['name'])) or (r['recruitType']=='HighSchool' and cn(ath[c][-1].get('homeCity'))==cn(r['city']) and (ath[c][-1].get('homeState') or '').upper()==(r['stateProvince'] or '').upper())]
    rec=good[0] if len(good)==1 else None
    add(f'ambig-{r["id"]}',r['id'],cands,rec,('One candidate matches on hometown and/or a draft record with this id.' if rec else 'No candidate is clearly distinguished by hometown or draft record; leave unresolved.'),'ambiguous name + school')
key={(r['name'],r['year'],r['committedTo']):r for r in R}
for h in X['held_name_mismatch']:
    if not h['reason'].startswith('recruit name'): continue
    r=key.get((h['recruit'],h['year'],h['school']))
    if not r: continue
    x=ath[h['athlete_id']][-1];toks=set(cn(t) for t in re.split(r'[\s\-]+',h['recruit']))
    if cn(x['firstName']) in toks: why='Same first name; last name spelled differently or suffix written differently.'
    elif r['recruitType']=='HighSchool' and x.get('homeState') and cn(x.get('homeCity'))==cn(r['city']) and x['homeState'].upper()==(r['stateProvince'] or '').upper(): why=f"Different first name ({x['firstName']}) but the same hometown ({r['city']}, {r['stateProvince']}): likely a nickname or alias."
    else: continue
    add(f"fname-{r['id']}",r['id'],[h['athlete_id']],h['athlete_id'],why,'first-name conflict (likely alias)')
json.dump(dict(about='Maintained identity decisions. Only status "approved" is applied by build_foundation.py; "pending" and "rejected" change nothing. decision: link (recruit_id to athlete_id), separate, or leave_unresolved.',cases=cases),open(F,'w'),indent=1)
import collections as C;print(len(cases),C.Counter((c['kind'],c['decision']) for c in cases))
