import json, os, subprocess, time
K=(os.environ.get('CFBD_KEY') or open(os.path.expanduser('~/cfbd_key.txt')).read()).strip()  # key lives outside the repo; never commit it
def get(ep):
    for i in range(4):
        r=subprocess.run(['curl','-s','-H',f'Authorization: Bearer {K}',f'https://api.collegefootballdata.com/{ep}'],capture_output=True,text=True)
        try: return json.loads(r.stdout)
        except Exception: time.sleep(2)
    raise SystemExit('fail '+ep)
def save(name,obj): json.dump(obj,open(f'data/{name}.json','w'))
rec=[]
for y in range(2008,2027):
    for c in ('HighSchool','JUCO','PrepSchool'):
        d=get(f'recruiting/players?year={y}&classification={c}'); rec+=d
    print(y,len(rec),flush=True)
save('recruits',rec)
dr=[]
for y in range(2010,2027): dr+=get(f'draft/picks?year={y}')
save('draft',dr); print('draft',len(dr))
save('coaches',get('coaches?minYear=2005&maxYear=2026')); 
po=[]
for y in range(2021,2027): po+=get(f'player/portal?year={y}')
save('portal',po); print('portal',len(po))
