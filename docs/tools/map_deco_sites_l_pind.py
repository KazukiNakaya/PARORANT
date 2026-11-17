"""L_Pind の角の小物（Step 42b C）の置き場所を決めて検査する、オフラインの計算（Unreal は使わない。通常の Python で実行）。

入力：Saved/Scratch/pind_layout.json（L_Pind を開いて、壁・パネル・建物・遮蔽の外形、持ち場・経由点・スポーン、設置エリア・バリアの外形を書き出したもの。
      書き出しは docs/29_pind_tropical.md §4 の Step 42b に書いた Unreal の Python）
出力：Saved/Scratch/pind_sites.json と表示。表を map_art_l_pind.py の DECO_SITES に貼る。
決まり（docs/26 §10 と同じ）：壁から離さない（小物の中心から壁まで 0.6m 以内）、壁・遮蔽・建物に重ならない、持ち場・経由点から 1.5m、
設置エリアの縁から 2m、バリアから 2.5m、スポーン（攻撃 (-35.4, 0)、防衛 (35, 0)）から 6m 以内に置かない。
通路の残り幅は、どの場所も歩ける範囲の短い辺が 6m 以上（最も狭い防衛側ルートの奥でも 5m 残る）。
小物の上から新しく見える視線は Unreal 側（map_deco_check_l_pind.py）で確かめる。
"""
import json, math, random
L=json.load(open('Saved/Scratch/pind_layout.json'))
solid=[s for s in L['solid']]
WALK=[("AtkSpawn",-40,-28,-37,37),("ALane",-28,6,-37,-31),("AMain",6,12,-36,-32),("ASite",12,34,-38,-16),("AShort",4,14,-20,-12),("BLane",-28,6,31,37),("BMain",6,12,32,36),("BSite",12,34,16,38),("BShort",4,14,12,20),("MidLane",-28,-10,-3,3),("Mid",-10,10,-12,12),("MidTop",10,30,-4,4),("DefSpawn",30,40,-10,10),("DefA",24,40,-16,-10),("DefB",24,40,10,16)]
pts=L['pts']
holds={k:v for k,v in pts.items()}
zones={z[0]:z[1:] for z in L['zones']}
def rect_dist(x,y,r):
    dx=max(r[0]-x,0,x-r[1]); dy=max(r[2]-y,0,y-r[3]); return math.hypot(dx,dy)
def checks(x,y,r=0.38):
    iss=[]
    for s in solid:
        d=rect_dist(x,y,s[1:5])
        if d<r+0.03: iss.append('solid '+s[0]+' %.2f'%d)
    near=min(rect_dist(x,y,s[1:5]) for s in solid if s[0].startswith(('Wall_','Panel_','Bld_')) )
    if near>r+0.22: iss.append('notwall %.2f'%near)
    for k,v in holds.items():
        if k.startswith('PlayerStart'): d=math.hypot(x-v[0],y-v[1]); 
        else: d=math.hypot(x-v[0],y-v[1])
        lim=6.0 if k.startswith('PlayerStart') else 1.5+0.0
        if d<lim: iss.append('pt %s %.2f'%(k,d))
    for k,v in zones.items():
        d=rect_dist(x,y,v); lim=2.5 if k.startswith('Barrier') else 2.0
        if d<lim: iss.append('zone %s %.2f'%(k,d))
    if math.hypot(x-35,y-0)<6.0: iss.append('defspawn')
    return iss
def inwalk(x,y):
    return [w[0] for w in WALK if w[1]<=x<=w[2] and w[3]<=y<=w[4]]

# ---- 場所の決定（P09・P10＝防衛スポーンの隅は、小物の上から Hold_A3・Hold_B3 が新しく見えたので外した）
rng=random.Random(7)
SITES=[ # id, desc, corner point, wall dirs (du along x/y)
 ("P01","攻撃スポーンの南西の隅",(-39.25,-36.55),[(1,0),(0,1)]),
 ("P02","攻撃スポーンの北西の隅",(-39.25,36.55),[(1,0),(0,-1)]),
 ("P03","A サイトの奥の隅（北東）",(33.25,-37.25),[(-1,0),(0,1)]),
 ("P04","B サイトの奥の隅（北西）",(33.25,37.25),[(-1,0),(0,-1)]),
 ("P05","ミッドの南西の隅",(-9.55,-11.55),[(0,1),(1,0)]),
 ("P06","ミッドの北西の隅",(-9.55,11.55),[(0,-1),(1,0)]),
 ("P07","ミッドの南東の隅",(9.55,-11.95),[(0,1),(-1,0)]),
 ("P08","ミッドの北東の隅",(9.55,11.95),[(0,-1),(-1,0)]),
 ("P11","防衛側 A ルートの奥の隅",(39.55,-15.55),[(-1,0),(0,1)]),
 ("P12","防衛側 B ルートの奥の隅",(39.55,15.55),[(-1,0),(0,-1)]),
]
KINDS={ # id -> kinds per item
 "P01":["barrel","crate","barrel"],"P02":["barrel","pot"],"P03":["crate","sack","amphora"],"P04":["sack","barrel"],
 "P05":["pot","barrel"],"P06":["amphora","sack"],"P07":["barrel","crate"],"P08":["crate","amphora","barrel"],
 "P09":["barrel","sack"],"P11":["pot","barrel"],"P12":["barrel","pot","sack"]}
out=[]
for sid,desc,c,dirs in SITES:
    items=[]
    offs=[(0,0),dirs[0] and (0.72*dirs[0][0],0.72*dirs[0][1]),(0.72*dirs[1][0],0.72*dirs[1][1])]
    for k,kind in enumerate(KINDS[sid]):
        # corner point may need nudging: search small neighborhood
        bx,by=c[0]+offs[k][0],c[1]+offs[k][1]
        ok=None
        for i in range(0,10):
            for j in range(0,10):
                px=bx+i*0.03*(-dirs[1][0]*0+ (dirs[0][0]+dirs[1][0])); py=by+j*0.03*(dirs[0][1]+dirs[1][1])
                px=bx+i*0.03*(dirs[0][0]+dirs[1][0]); py=by+j*0.03*(dirs[0][1]+dirs[1][1])
                if not checks(px,py):
                    ok=(px,py);break
            if ok:break
        if not ok: 
            print('drop',sid,k); continue
        items.append((round(ok[0],3),round(ok[1],3),round(rng.uniform(0,360),1),round(rng.uniform(0.92,1.08),2),kind))
    out.append((sid,desc,items))
print(sum(len(i[2]) for i in out))
for o in out: print(o)
json.dump(out,open('Saved/Scratch/pind_sites.json','w'),ensure_ascii=False)
