import subprocess,json,collections,sys
sys.argv=['x'];exec(open('pathway_records.py').read().split("if __name__")[0])
V=[("Joe Burrow@2015","Correct","Ohio State 2015-17 to LSU 2018-19, 2020 #1. The padded 2014 Ohio State listing is now hidden."),
("Jordan Addison@2020","Correct","Pitt 2020-21, USC 2022, Confirmed transfer, 2023 #23."),
("Jalen Hurts@2016","Correct","Alabama 2016-18, Oklahoma 2019, 2020 #53; the move is Inferred (2019 is before our portal data). Padded 2015 listing hidden."),
("Justin Fields@2018","Unresolved (recommended link pending)","Two Georgia ids share his name, so he stays unresolved. The identity file recommends linking id 4362887 (Kennesaw hometown, drafted 2021 #11); pending your approval."),
("Baker Mayfield","Partly correct","Roster record is right (Texas Tech 2013, Oklahoma 2014-17, 2018 #1). His walk-on recruiting record (no school) is not joined; a link is recommended, pending."),
("Cam Ward","Partly correct","Washington State to Miami Confirmed and 2025 #1 correct. UIW 2020 missing (no roster file for that FCS season); the UIW move stays Inferred (portal lists him as Cameron Ward)."),
("Caleb Williams@2021","Correct","Oklahoma 2021, USC 2022-23, Confirmed, 2024 #1."),
("Bo Nix@2019","Correct","Auburn 2019-21, Oregon 2022-23 (new id at Oregon joined through his portal entry), 2024 #12."),
("Michael Penix Jr.@2018","Correct","Indiana 2018-21, Washington 2022-23, Confirmed, 2024 #8."),
("Jayden Daniels@2019","Correct","Arizona State 2019-21, LSU 2022-23, Confirmed, 2024 #2."),
("Nolan Smith@2019","Unresolved (recommended link pending)","Roster id held back because a second same-name recruit shares it. Draft 2023 #30 kept from the official link. The identity file recommends id 4426331 (drafted with that id), pending."),
("Khalil Herbert@2016","Correct","Kansas 2016-19, Virginia Tech 2020, 2021 #217. The roster's 2021 Kansas listing (after the draft) is now hidden."),
("Jameson Williams@2019","Unresolved (recommended link pending)","Held back (same-name recruit). The identity file recommends id 4426388 (St. Louis, Ohio State 2019-20, Alabama 2021, drafted 2022 #12), pending."),
("Zavion Thomas@2022","Correct","Mississippi State 2022-23, LSU 2024-25, Confirmed, 2026 #89."),
("Chris Hilton Jr.@2021","Correct","LSU 2021-25; no draft record through 2026 (undrafted)."),
("Eric Goins","Unresolved (correctly flagged)","One id: The Citadel 2013-15, then Notre Dame 2024. The 9-season gap fails the identity check; the move is Unknown/unresolved."),
("Keisean Nixon@2017","Correct","JUCO signee, South Carolina 2017-18; not drafted. The 2015-16 South Carolina listings (his junior college years) are now hidden."),
("Nathan Rourke@2017","Correct","JUCO signee, Ohio 2017-19; not drafted. The 2016 Ohio listing is now hidden."),
("Quinn Ewers@2021","Partly correct","Texas 2022-24 and 2025 #231 correct. Ohio State 2021 is missing from the roster file, so the move is now Reported (movement not established) instead of Confirmed."),
("Dillon Gabriel@2019","Correct","UCF 2019-21, Oklahoma 2022-23, Oregon 2024, two Confirmed transfers, 2025 #94."),
("Jaxson Dart@2021","Correct","USC 2021, Ole Miss 2022-24, Confirmed, 2025 #25."),
("Shedeur Sanders@2021","Correct","Jackson State 2021-22, Colorado 2023-24, Confirmed, 2025 #144."),
("Travis Hunter@2022","Correct","Jackson State 2022, Colorado 2023-24, Confirmed, 2025 #2."),
("Avery Peterson@2012","Partly correct","High school and prep records merged; LSU 2013-14 correct. Cincinnati 2015 missing (his Cincinnati roster row is not joined)."),
("Joshua Singh@2021","Correct","BYU 2022-24, Vanderbilt 2025, Confirmed (2021 BYU season not on the roster file; web-checked).")]
out=[]
for a,v,why in V:
    n,_,c=a.partition('@'); rec=show(n,int(c) if c else None)
    out.append(rec+f"\n  >> HAND CHECK (FND-0.2): {v}. {why}")
open('hand_checked_25_FND02.txt','w').write('\n'.join(out))
print(collections.Counter(v.split(' (')[0] for _,v,_ in V))
