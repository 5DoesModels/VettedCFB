import json,collections
PS=json.load(open('build/FND-0.2/player_seasons.json'))
c=collections.Counter();bad=0
for s in PS:
    if s.get('hidden'): c['rows hidden (padded roster listing)']+=1; continue
    if s['games_any']=='not_available': c['rows: no game data for that season/school']+=1; continue
    c['rows measured']+=1
    a=s['games_any'];c['appearances: games with any stat']+=a
    if a==0: c['rows: on roster, no stat in any game']+=1
    sp,fu,ot=s['games_special_only'],s['games_fumble_only'],s['games_other_only']
    gp=s['games_position']
    if isinstance(gp,int):
        c['position-specific games']+=gp; c['special-teams-only games']+=sp; c['fumble-only games']+=fu; c['other-stat-only games']+=ot
        if gp+sp+fu+ot!=a: bad+=1
    else:
        c[f'games not classified ({gp})']+=a
    c['qualifies: position stat in 6+ games']+= isinstance(gp,int) and gp>=6
print(json.dumps(c,indent=1));print('rows where the parts do not add up:',bad)
json.dump(dict(c,parts_mismatch=bad),open('participation_reconcile.json','w'),indent=1)
