# Cache CFBD game-level player stats (/games/players) by year, season type and week. Raw responses saved unchanged.
import json,os,sys,time,urllib.request
K=open('/root/cfbd_key.txt').read().strip() if os.path.exists('/root/cfbd_key.txt') else open(os.path.expanduser('~/cfbd_key.txt')).read().strip()
D='/home/claude/foundation/raw_box'; LOG=D+'/pull_log.jsonl'
def get(y,st,w):
    f=f'{D}/gp_{y}_{st}_{w}.json'
    if os.path.exists(f): return 'cached',None
    url=f'https://api.collegefootballdata.com/games/players?year={y}&week={w}&seasonType={st}'
    for a in range(3):
        try:
            r=urllib.request.urlopen(urllib.request.Request(url,headers={'Authorization':'Bearer '+K,'Accept':'application/json'}),timeout=120)
            b=r.read(); rem=r.headers.get('x-calllimit-remaining'); json.loads(b); open(f,'wb').write(b)
            return 'ok',rem
        except Exception as e:
            err=str(e); time.sleep(5*(a+1))
    return 'failed:'+err,None
jobs=[tuple(x.split(':')) for x in sys.argv[1:]] if len(sys.argv)>1 else [(str(y),'regular',str(w)) for y in range(2009,2026) for w in range(1,17)]+[(str(y),'postseason',str(w)) for y in range(2009,2026) for w in (1,2)]
for y,st,w in jobs:
    s,rem=get(y,st,w)
    open(LOG,'a').write(json.dumps(dict(y=int(y),st=st,w=int(w),status=s,remaining=rem,t=time.strftime('%H:%M:%S')))+'\n')
    if s!='cached': print(y,st,w,s,rem,flush=True); time.sleep(0.4)
