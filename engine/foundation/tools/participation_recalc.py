import json,glob,os,collections
D='/home/claude/foundation/raw_box/'; C='/root/cfbd_pull/'
FBS={(s['school'],s['year']) for c in json.load(open('/home/claude/vetted-cfb/engine/data/coaches.json')) for s in c['seasons']}
ath=collections.defaultdict(lambda:collections.defaultdict(set))
for f in sorted(glob.glob(D+'gp_*.json')):
    y=int(os.path.basename(f).split('_')[1])
    for g in json.load(open(f)):
        for t in g['teams']:
            for c in t['categories']:
                for ty in c['types']:
                    for x in ty['athletes']: ath[(x['id'],t['team'],y)][g['id']].add(c['name'])
GRP={'QB':'QB','RB':'RB','FB':'RB','WR':'WR','TE':'TE','OL':'OL','OT':'OL','OG':'OL','C':'OL','G':'OL','T':'OL','DL':'DL','DE':'DL','DT':'DL','NT':'DL','LB':'LB','OLB':'LB','ILB':'LB','DB':'DB','CB':'DB','S':'DB'}
POSCAT={'QB':{'passing'},'RB':{'rushing','receiving'},'WR':{'receiving'},'TE':{'receiving'},'DL':{'defensive','interceptions'},'LB':{'defensive','interceptions'},'DB':{'defensive','interceptions'}}
SPEC={'kickReturns','puntReturns','kicking','punting'}
res=collections.defaultdict(lambda:collections.Counter())
for y in range(2009,2026):
    for x in json.load(open(f'{C}ros_{y}.json')):
        g=GRP.get(x.get('position'));t=x['team']
        if not g or (t,y) not in FBS or x['id'].startswith('-'): continue
        era='2019-2025' if y>=2019 else '2014-2018' if y>=2014 else '2009-2013'
        G=ath.get((x['id'],t,y),{})
        anyg=len(G); posg=sum(1 for c in G.values() if c&POSCAT.get(g,set())); sto=sum(1 for c in G.values() if c<=SPEC)
        r=res[(g,era)]; r['n']+=1; r['any6']+=anyg>=6; r['pos6']+=posg>=6; r['any1']+=anyg>=1; r['pos1']+=posg>=1
        r['st_only_season']+= anyg>0 and posg==0 and g!='OL'
        r['lost6']+= anyg>=6 and posg<6
out={}
print(f"{'pos':4}{'era':11}{'roster rows':>12}{'any stat 6+':>13}{'position stat 6+':>18}{'dropped':>9}{'ST-only seasons':>16}")
for (g,era),r in sorted(res.items()):
    n=r['n']; out[f'{g}|{era}']=dict(r)
    note='' if not (g in('DL','LB','DB') and era!='2019-2025') else '  (defense not measured before 2019)'
    print(f"{g:4}{era:11}{n:>12}{100*r['any6']/n:>12.1f}%{100*r['pos6']/n:>17.1f}%{r['lost6']:>9}{r['st_only_season']:>16}{note}")
json.dump(out,open('participation_recalc.json','w'))
