"""PARORANT L_Pind 見た目の追加スクリプト（Step 42a、docs/29_pind_tropical.md §2.3）。南国の海辺。

L_Pind を開いて Unreal の Python で実行する（L_Pind 以外では止まる）。何度実行しても同じ結果になる。
手本は map_art_l_canal.py。大原則は同じ（docs/26 §1）：
  - 足す見た目はすべて当たり判定なし（NoCollision）・ナビメッシュに影響しない・タグ PindArt。小さな部品はアクタ ArtHost の
    InstancedStaticMeshComponent（ISM_<key>）に入れる。ISM は Python から足せないので、足りなければ一覧を出して止まる
    （Unreal MCP の control_actor edit_component で、componentType = InstancedStaticMeshComponent、meshPath = Cube／Cylinder を足す）
  - 壁・遮蔽・外周・Fab のパネルと建物の形・位置・当たり判定は変えない（素材と、表面の薄い飾りだけ）。
    歩ける範囲へ出る飾りは表面から 3cm 以内（頭上 3m より上は自由。笠石、庇、日よけ、屋根）
  - Fab のパネル（Panel_*、15cm 厚、高さ 2.4m。当たり判定あり）は壁から 30cm 歩ける範囲へ出ている。表面の飾りはパネルの前の面に付ける
  - 作り直しは「タグ PindArt のアクタを消す」「ISM の中身を空にする」だけ。ゲーム用の配置（持ち場、設置エリア、MapInfo など）には触らない
  - MI_Canal_* は読み込むだけで書き換えない（L_Canal の見た目を変えないため）。MI_Pind_* だけ作る・色を決める
座標は m（+X が北、+Y が東、床の上面が Z=0）。
"""
import math
import random

try:
    import unreal
except ImportError:
    unreal = None

# ------------------------------------------------------------------ 素材（M_NatureFlat のインスタンス。リニア値。昼の強い日差しで白飛びしないよう、少し落とした色）
PIND_COLORS = {
    "MI_Pind_Plaster_White": (0.66, 0.65, 0.58),   # 白い漆喰（露出固定のまま白飛びしない明るい白）
    "MI_Pind_Plaster_Cream": (0.60, 0.52, 0.36),   # クリームの漆喰
    "MI_Pind_Sandstone":     (0.64, 0.51, 0.33),   # 明るい暖色の砂岩（古い砦の壁、腰の帯）。白い漆喰（0.66,0.65,0.58）と見分けがつく暖色
    "MI_Pind_StoneLt":       (0.78, 0.66, 0.46),   # 砂岩の明るい石（笠石、帯、縁石、色むら）
    "MI_Pind_StoneDk":       (0.30, 0.22, 0.13),   # 目地・床の継ぎ目の線（細い線だけに使う）
    "MI_Pind_Teal":          (0.02, 0.36, 0.34),   # 青緑（窓枠、鎧戸、扉、手すり、一部の壁の腰）
    "MI_Pind_Coral":         (0.52, 0.10, 0.07),   # 珊瑚色（日よけ、屋根）
    "MI_Pind_Wood":          (0.30, 0.17, 0.08),   # 木箱
    "MI_Pind_WoodDark":      (0.13, 0.07, 0.035),  # 木の縁取り・筋交い
    "MI_Pind_Burlap":        (0.30, 0.22, 0.11),   # 麻袋
    "MI_Pind_StoneBlock":    (0.40, 0.37, 0.32),   # 石の台
    "MI_Pind_Sand":          (0.58, 0.52, 0.38),   # 白っぽい明るい砂
    "MI_Pind_Cobble":        (0.46, 0.36, 0.25),   # 明るい暖色の石畳
    "MI_Pind_CobbleDark":    (0.32, 0.25, 0.17),   # 狭い通路の石畳
    "MI_Pind_Plaza":         (0.50, 0.42, 0.31),   # 石畳の広場（A）
    "MI_Pind_Terracotta":    (0.30, 0.16, 0.10),   # ミッドの床（赤土）
    "MI_Pind_Deck":          (0.15, 0.08, 0.04) , # 木の甲板・桟橋（砂と見分けがつく濃い木の色）
    "MI_Pind_Sea":           (0.0, 0.07, 0.24),    # 沖の海（濃い青）
    "MI_Pind_SeaShallow":    (0.03, 0.42, 0.40),   # 岸に近い浅い水色
    "MI_Pind_Foam":          (0.45, 0.50, 0.50),   # 波打ち際
}
CANAL_READONLY = {"glass": "MI_Canal_Glass", "iron": "MI_Canal_Iron"}
# key: (素材名、影を落とすか)
ISM_KEYS = {
    "pl_white": ("MI_Pind_Plaster_White", False), "pl_cream": ("MI_Pind_Plaster_Cream", False),
    "sandstone": ("MI_Pind_Sandstone", False),
    "stone_lt": ("MI_Pind_StoneLt", False), "stone_dk": ("MI_Pind_StoneDk", False),
    "teal": ("MI_Pind_Teal", False), "coral": ("MI_Pind_Coral", False),
    "roof": ("MI_Pind_Coral", True),                      # 壁の上の屋根（紹介画面の間は隠す。タグ IntroHide）
    "wood_dark": ("MI_Pind_WoodDark", False),
    "glass": ("MI_Canal_Glass", False), "iron": ("MI_Canal_Iron", False),
    "sand": ("MI_Pind_Sand", False), "sea": ("MI_Pind_Sea", False), "foam": ("MI_Pind_Foam", False),
    "deck": ("MI_Pind_Deck", False),
    "wood_cyl": ("MI_Pind_WoodDark", False),
}
CYL_KEYS = {"wood_cyl"}

# 床の舗装（WALK の名前 → 素材）。歩ける範囲の板（高さ 0〜1cm、当たり判定なし）
FLOOR_OVERLAY = {
    "ALane": "MI_Pind_Cobble", "BLane": "MI_Pind_Cobble", "MidLane": "MI_Pind_Cobble",
    "AMain": "MI_Pind_CobbleDark", "BMain": "MI_Pind_CobbleDark", "AShort": "MI_Pind_CobbleDark", "BShort": "MI_Pind_CobbleDark",
    "ASite": "MI_Pind_Plaza", "BSite": "MI_Pind_Deck",
    "Mid": "MI_Pind_Terracotta", "MidTop": "MI_Pind_Terracotta",
    "DefSpawn": "MI_Pind_Plaza", "DefA": "MI_Pind_Sand", "DefB": "MI_Pind_Sand",
}
PIERS = [(-40, -28, -7, 7), (-40, -28, 29, 37), (-40, -28, -37, -29)]   # 攻撃スポーンの木の桟橋（x0, x1, y0, y1）
WALL_TOP = 4.0
FORT = {"Wall_00", "Wall_01", "Wall_14", "Wall_15", "Wall_20", "Wall_21"}   # 古い砦（砂色の石積み）の壁
PANEL_TOP = 2.4     # Fab のパネルの高さ
N = 40
W = 2 * N
WALK = [
    ("AtkSpawn", -40, -28, -37, 37), ("ALane", -28, 6, -37, -31), ("AMain", 6, 12, -36, -32), ("ASite", 12, 34, -38, -16),
    ("AShort", 4, 14, -20, -12), ("BLane", -28, 6, 31, 37), ("BMain", 6, 12, 32, 36), ("BSite", 12, 34, 16, 38),
    ("BShort", 4, 14, 12, 20), ("MidLane", -28, -10, -3, 3), ("Mid", -10, 10, -12, 12), ("MidTop", 10, 30, -4, 4),
    ("DefSpawn", 30, 40, -10, 10), ("DefA", 24, 40, -16, -10), ("DefB", 24, 40, 10, 16),
]
# 遮蔽の種類（A＝木箱、B＝石の台、ミッド＝麻袋の箱、通路＝木箱）
COVER_KIND = {"CoverA": "crate", "CoverB": "stone", "CoverMid": "sack", "CoverALane": "crate", "CoverBLane": "crate"}
COVER_MAT = {"crate": "MI_Pind_Wood", "stone": "MI_Pind_StoneBlock", "sack": "MI_Pind_Burlap"}
ZONE_LABEL_COLOR = (150, 15, 15)   # 設置エリアの文字（明るい石畳・砂の上で読める濃い赤）


def ci(v):
    return int(round(v + N))


if unreal is not None:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    ea = unreal.EditorAssetLibrary
    MAT_DIR = "/Game/PARORANT/Materials"
    _world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
    if not _world.startswith("/Game/PARORANT/Maps/L_Pind"):
        raise RuntimeError("L_Pind を開いてから実行してください（今のレベル: %s）" % _world)

    ART_TAG = [unreal.Name("PindArt")]
    CUBE = ea.load_asset("/Engine/BasicShapes/Cube")
    CYLMESH = ea.load_asset("/Engine/BasicShapes/Cylinder")

    def mi_pind(name):
        """MI_Pind_*（無ければ作る）。色は PIND_COLORS の値にそろえる（再実行しても同じ）。"""
        path = f"{MAT_DIR}/{name}"
        if ea.does_asset_exist(path):
            m = ea.load_asset(path)
        else:
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            m = tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
            m.set_editor_property("parent", ea.load_asset(f"{MAT_DIR}/M_NatureFlat"))
        c = PIND_COLORS[name]
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(m, "Color", unreal.LinearColor(c[0], c[1], c[2], 1.0))
        unreal.MaterialEditingLibrary.update_material_instance(m)
        ea.save_loaded_asset(m)
        return m

    MATS = {n: mi_pind(n) for n in PIND_COLORS}
    for _n in CANAL_READONLY.values():
        MATS[_n] = ea.load_asset(f"{MAT_DIR}/{_n}")   # 読み込むだけ（書き換えない）

    # ---------------------------------------------------------------- 前回の見た目を消す
    all_actors = list(eas.get_all_level_actors())
    host = None
    for a in all_actors:
        if a.get_actor_label() == "ArtHost":
            host = a
            continue
        if unreal.Name("PindArt") in a.tags or unreal.Name("PindDeco") in a.tags:
            a.destroy_actor()
    if host is None:
        host = eas.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0))
        host.set_actor_label("ArtHost")
        host.set_folder_path("Art")
        host.set_editor_property("tags", [unreal.Name("PindArtHost")])
    # BP_PR_GameMode.SetIntroHide はタグ CanalArtHost のアクタの、タグ IntroHide のコンポーネントを紹介画面の間だけ隠す（CANAL と共通の仕組みなのでこのタグも付ける）
    host.set_editor_property("tags", [unreal.Name("PindArtHost"), unreal.Name("CanalArtHost")])
    comps = {c.get_name(): c for c in host.get_components_by_class(unreal.InstancedStaticMeshComponent)}
    missing = [k for k in ISM_KEYS if "ISM_" + k not in comps]
    if missing:
        raise RuntimeError("ArtHost に足りない ISM（edit_component の componentName。cylinder は meshPath=/Engine/BasicShapes/Cylinder、他は Cube）: "
                           + ", ".join("ISM_" + k for k in missing))
    ism = {}
    for k, (mat, shadow) in ISM_KEYS.items():
        c = comps["ISM_" + k]
        c.clear_instances()
        c.set_static_mesh(CYLMESH if k in CYL_KEYS else CUBE)
        c.set_material(0, MATS[mat])
        c.set_collision_profile_name("NoCollision")
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_editor_property("can_ever_affect_navigation", False)
        c.set_cast_shadow(shadow)
        ism[k] = c
    pending = {k: [] for k in ISM_KEYS}

    def cm(v):
        return v * 100.0

    def inst(key, cx, cy, cz, sx, sy, sz, rot=(0.0, 0.0, 0.0)):
        """ISM の 1 個。rot = (pitch, yaw, roll) 度。サイズ・中心は m。"""
        pending[key].append(unreal.Transform(unreal.Vector(cm(cx), cm(cy), cm(cz)), unreal.Rotator(rot[2], rot[0], rot[1]),
                                              unreal.Vector(sx, sy, sz)))

    def ibox(key, x0, x1, y0, y1, z0, z1):
        inst(key, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, x1 - x0, y1 - y0, z1 - z0)

    ML = unreal.MathLibrary

    def inst_dir(key, cx, cy, cz, length, wy, wz, d):
        """X 軸を方向 d=(dx, dy, dz) に向けた箱。scale = (length, wy, wz)"""
        rot = ML.find_look_at_rotation(unreal.Vector(0, 0, 0), unreal.Vector(d[0], d[1], d[2]))
        pending[key].append(unreal.Transform(unreal.Vector(cm(cx), cm(cy), cm(cz)), rot, unreal.Vector(length, wy, wz)))

    def spawn_slab(label, x0, x1, y0, y1, z0, z1, mat, folder="Art/Pind"):
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(cm((x0 + x1) / 2), cm((y0 + y1) / 2), cm((z0 + z1) / 2)))
        a.set_actor_label(label)
        a.set_folder_path(folder)
        c = a.static_mesh_component
        c.set_mobility(unreal.ComponentMobility.STATIC)
        c.set_static_mesh(CUBE)
        a.set_actor_scale3d(unreal.Vector(x1 - x0, y1 - y0, z1 - z0))
        c.set_material(0, mat)
        c.set_collision_profile_name("NoCollision")
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_editor_property("can_ever_affect_navigation", False)
        c.set_cast_shadow(False)
        a.set_editor_property("tags", ART_TAG)
        return a

    byname = {a.get_actor_label(): a for a in all_actors}

    def set_all_mats(actor, mat):
        c = actor.static_mesh_component
        for i in range(len(c.get_materials())):
            c.set_material(i, mat)

    # ---------------------------------------------------------------- 1. 壁の箱・外周・パネル・建物・床の素材（形は変えない）
    wall_rects = []
    for a in all_actors:
        lb = a.get_actor_label()
        if lb.startswith("Wall_") and lb[5:].isdigit():
            l, sc = a.get_actor_location(), a.get_actor_scale3d()
            wall_rects.append((lb, (l.x / 100 - sc.x / 2, l.x / 100 + sc.x / 2, l.y / 100 - sc.y / 2, l.y / 100 + sc.y / 2)))
    wall_rects.sort()

    def touching(r1, r2):
        ax0, ax1, ay0, ay1 = r1
        bx0, bx1, by0, by1 = r2
        if (abs(ax1 - bx0) < 1e-6 or abs(bx1 - ax0) < 1e-6) and min(ay1, by1) - max(ay0, by0) > 1e-6:
            return True
        if (abs(ay1 - by0) < 1e-6 or abs(by1 - ay0) < 1e-6) and min(ax1, bx1) - max(ax0, bx0) > 1e-6:
            return True
        return False

    wall_mat = {}
    cycle = ["MI_Pind_Plaster_White", "MI_Pind_Plaster_White", "MI_Pind_Plaster_Cream"]   # 大半が白い漆喰、ときどきクリーム
    for i, (lb, r) in enumerate(wall_rects):
        if lb in FORT:
            wall_mat[lb] = "MI_Pind_Sandstone"
            continue
        used = {wall_mat[l2] for (l2, r2) in wall_rects if l2 in wall_mat and touching(r, r2)}
        free = [m for m in cycle if m not in used or m == "MI_Pind_Plaster_White"]
        wall_mat[lb] = "MI_Pind_Plaster_Cream" if (i % 5 == 3 and "MI_Pind_Plaster_Cream" not in used) else free[0]
        byname[lb].static_mesh_component.set_material(0, MATS[wall_mat[lb]])
    for lb in wall_mat:
        byname[lb].static_mesh_component.set_material(0, MATS[wall_mat[lb]])
    for n in ("Wall_N", "Wall_S", "Wall_E", "Wall_W"):
        byname[n].static_mesh_component.set_material(0, MATS["MI_Pind_Sandstone"])
    byname["Floor"].static_mesh_component.set_material(0, MATS["MI_Pind_Sand"])
    panels = []
    for a in all_actors:
        lb = a.get_actor_label()
        if lb.startswith("Panel_"):
            set_all_mats(a, MATS["MI_Pind_Plaster_White"])
            o, e = a.get_actor_bounds(False)
            panels.append((o.x / 100 - e.x / 100, o.x / 100 + e.x / 100, o.y / 100 - e.y / 100, o.y / 100 + e.y / 100))
        elif lb.startswith("Bld_"):
            set_all_mats(a, MATS["MI_Pind_Plaster_White"])
    n_overlay = 0
    for nm, x0, x1, y0, y1 in WALK:
        if nm in FLOOR_OVERLAY:
            spawn_slab("Paving_" + nm, x0, x1, y0, y1, 0.0, 0.01, MATS[FLOOR_OVERLAY[nm]])
            n_overlay += 1
    for i, (x0, x1, y0, y1) in enumerate(PIERS):
        spawn_slab("Pier_%d" % i, x0, x1, y0, y1, 0.0, 0.015, MATS["MI_Pind_Deck"])
        n_overlay += 1
    # 設置エリアの文字（色だけ。枠 FloorMark の素材 M_PR_ZoneFrame は CANAL と共通なので触らない）
    for zn in ("PlantZone_A", "PlantZone_B"):
        z = byname.get(zn)
        if z:
            for t in z.get_components_by_class(unreal.TextRenderComponent):
                t.set_editor_property("text_render_color", unreal.Color(r=ZONE_LABEL_COLOR[0], g=ZONE_LABEL_COLOR[1], b=ZONE_LABEL_COLOR[2], a=255))

    # ---------------------------------------------------------------- 2. 壁の面（歩ける範囲に向いた面）の飾り
    walk = [[False] * W for _ in range(W)]
    for _, x0, x1, y0, y1 in WALK:
        for x in range(x0, x1):
            for y in range(y0, y1):
                walk[x + N][y + N] = True
    owner = [[-1] * W for _ in range(W)]
    for i, (lb, (x0, x1, y0, y1)) in enumerate(wall_rects):
        for ix in range(ci(x0), ci(x1)):
            for iy in range(ci(y0), ci(y1)):
                owner[ix][iy] = i

    def is_solid(ix, iy):
        return not (0 <= ix < W and 0 <= iy < W) or not walk[ix][iy]

    runs_raw = {}
    for ix in range(W):
        for iy in range(W):
            if not walk[ix][iy]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                jx, jy = ix + dx, iy + dy
                if not is_solid(jx, jy):
                    continue
                own = owner[jx][jy] if (0 <= jx < W and 0 <= jy < W) else -2
                if dx:
                    fixed, pos = max(ix, jx) / 1.0 - N, iy
                else:
                    fixed, pos = max(iy, jy) / 1.0 - N, ix
                runs_raw.setdefault((dx, dy, round(fixed, 4), own), []).append(pos)
    runs = []   # (nx, ny, fixed, owner, a, b)
    for (dx, dy, fixed, own), lst in runs_raw.items():
        lst.sort()
        s = p = lst[0]
        for v in lst[1:] + [None]:
            if v is not None and v == p + 1:
                p = v
                continue
            runs.append((-dx, -dy, fixed, own, float(s - N), float(p + 1 - N)))
            if v is not None:
                s = p = v
    runs.sort(key=lambda r: (r[2], r[0], r[1], r[4]))

    def panel_segments(run):
        """面をパネルがある所とない所に分ける。[(t0, t1, 深さ m)]。深さ 0 = パネル無し"""
        nx, ny, fixed, own, a, b = run
        cuts = {a, b}
        info = []
        for (px0, px1, py0, py1) in panels:
            if nx:
                near = (px0 if nx > 0 else px1)
                depth = (px1 - px0)
                t0, t1 = py0, py1
            else:
                near = (py0 if ny > 0 else py1)
                depth = (py1 - py0)
                t0, t1 = px0, px1
            if abs(near - fixed) > 0.05 or depth > 0.5 or min(t1, b) - max(t0, a) < 0.05:
                continue
            info.append((max(t0, a), min(t1, b), depth))
            cuts.add(max(t0, a))
            cuts.add(min(t1, b))
        cuts = sorted(cuts)
        segs = []
        for u0, u1 in zip(cuts[:-1], cuts[1:]):
            if u1 - u0 < 1e-6:
                continue
            d = 0.0
            for (t0, t1, dp) in info:
                if t0 <= u0 + 1e-6 and t1 >= u1 - 1e-6:
                    d = max(d, dp)
            segs.append((u0, u1, d))
        return segs

    def face_box(run, key, t0, t1, thick, z0, z1, off=0.0):
        nx, ny, fixed = run[0], run[1], run[2]
        if nx > 0 or ny > 0:
            n0, n1 = fixed + off, fixed + off + thick
        else:
            n0, n1 = fixed - off - thick, fixed - off
        if nx:
            ibox(key, n0, n1, t0, t1, z0, z1)
        else:
            ibox(key, t0, t1, n0, n1, z0, z1)

    def awning(run, t0, t1, z, proj=0.9):
        """日よけ：壁から出る傾いた縞の布（下端が頭上 3m 以上。珊瑚色と白）。壁側が z+0.45、外の端が z"""
        nx, ny, fixed = run[0], run[1], run[2]
        n = max(2, int((t1 - t0) / 0.4))
        ln = math.hypot(proj, 0.45)
        for k in range(n):
            u0, u1 = t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n
            tm = (u0 + u1) / 2
            key = "coral" if k % 2 == 0 else "pl_white"
            if nx:
                cx, cy = fixed + nx * proj / 2, tm
            else:
                cx, cy = tm, fixed + ny * proj / 2
            inst_dir(key, cx, cy, z + 0.225, ln, u1 - u0, 0.03, (nx * proj, ny * proj, -0.45))

    rs_stone = random.Random(777)

    def stone_face(run, u0, u1, zlo, zhi, off):
        """砦の石積み：段（約 45cm）ごとに目地の線（1.8cm）と、ブロックの色むら（明るい石・クリーム、1.2cm）。面から 2cm 以内"""
        nrow = max(1, int(round((zhi - zlo) / 0.45)))
        hh = (zhi - zlo) / nrow
        for r in range(nrow):
            za, zb = zlo + r * hh, zlo + (r + 1) * hh
            shift = 0.45 * (r % 2)
            pts = [u0]
            j = u0 + shift if shift > 0.05 else u0 + 0.9
            while j < u1 - 0.05:
                pts.append(j)
                j += 0.9
            pts.append(u1)
            for pa, pb in zip(pts[:-1], pts[1:]):
                if pb - pa < 0.08:
                    continue
                q = rs_stone.random()
                key = "stone_lt" if q < 0.30 else ("pl_cream" if q < 0.50 else None)
                if key:
                    face_box(run, key, pa + 0.015, pb - 0.015, 0.012, za + 0.015, zb - 0.015, off=off)
            for jp in pts[1:-1]:
                face_box(run, "stone_dk", jp - 0.009, jp + 0.009, 0.018, za, zb, off=off)
            if r >= 1:
                face_box(run, "stone_dk", u0, u1, 0.018, za - 0.009, za + 0.009, off=off)

    banners = []   # 旗・布の注文。(run, t, 色の番号)
    bcount = 0     # 旗の通し番号（色は通し番号で珊瑚色・青緑・白と回す。区間ごとに 0 から数えると壁一面が同じ色になる）

    n_win = n_door = n_run = n_awn = 0
    for ri, run in enumerate(runs):
        nx, ny, fixed, own, a, b = run
        if b - a < 1.0:
            continue
        n_run += 1
        fort = own == -2 or (own >= 0 and wall_rects[own][0] in FORT)
        for (u0, u1, depth) in panel_segments(run):
            L = u1 - u0
            lo_off = depth                       # パネルの前の面（2.4m まで）。パネルが無ければ 0
            occ = []                             # 窓・扉の位置（旗を避ける）
            if L >= 0.6:
                if fort and depth == 0:
                    face_box(run, "stone_lt", u0, u1, 0.03, 0.0, 0.5)                       # 砦の土台（明るい石）
                    stone_face(run, u0, u1, 0.5, WALL_TOP - 0.32, 0.0)
                else:
                    if fort:
                        stone_face(run, u0, u1, PANEL_TOP, WALL_TOP - 0.32, 0.0)           # パネルの上の石積み
                    # 腰の石積みの帯（青緑は 7 面に 1 面だけ、低く。残りは砂岩）と上端の縁（3cm 以内）
                    teal_band = (ri % 7 == 0) and not fort
                    bh = 0.55 if teal_band else 0.95
                    face_box(run, "teal" if teal_band else "sandstone", u0, u1, 0.025, 0.0, bh, off=lo_off)
                    face_box(run, "stone_lt", u0, u1, 0.03, bh, bh + 0.08, off=lo_off)
            # 上の縁（笠石の下の帯と軒。頭上 3.6m 以上、パネルより上）。砦は明るい石
            face_box(run, "stone_lt" if fort else "pl_white", u0, u1, 0.12, WALL_TOP - 0.30, WALL_TOP)
            if L >= 3.0:
                kk = 0
                tb = u0 + 1.2
                while tb < u1 - 1.2:
                    banners.append((run, tb, (bcount + ri) % 3, depth))
                    bcount += 1
                    tb += 4.4
                    kk += 1
            if depth > 0:
                continue                         # パネルの前には窓・扉は付けない
            usable = L - 1.4
            nwin = min(3, int(usable // 3.0)) if usable >= 2.0 else 0
            shut = "teal"
            wins = []
            dt = None                                # 扉の位置（窓と重ならないよう、窓より先に決める）
            if usable >= 3.2:
                dt = u0 + 0.7 + usable * (0.35 if ri % 2 == 0 else 0.65)
            for k in range(nwin):
                t = u0 + 0.7 + usable * (k + 0.5) / nwin
                if dt is not None and abs(t - dt) < 1.9:
                    continue                         # 扉の上に窓が重なって鍵穴のような形になるのを避ける（鎧戸まで含めて 1.9m 離す）
                wins.append(t)
                face_box(run, "teal", t - 0.55, t + 0.55, 0.02, 1.55, 2.95)             # 枠（2cm）
                face_box(run, "glass", t - 0.42, t + 0.42, 0.03, 1.68, 2.82)            # ガラス（枠より 1cm 出る。面から 3cm）
                face_box(run, shut, t - 0.98, t - 0.56, 0.03, 1.60, 2.90)               # 鎧戸
                face_box(run, shut, t + 0.56, t + 0.98, 0.03, 1.60, 2.90)
                n_win += 1
                if (ri + k) % 2 == 0:
                    awning(run, t - 1.0, t + 1.0, 3.15)
                    n_awn += 1
            if dt is not None:
                t = dt
                face_box(run, "stone_lt", t - 0.80, t + 0.80, 0.02, 0.0, 2.45)
                face_box(run, "teal", t - 0.62, t + 0.62, 0.03, 0.0, 2.25)
                face_box(run, "wood_dark", t - 0.58, t - 0.54, 0.03, 0.2, 2.1)
                n_door += 1
            if fort:
                # 腰より上の細い帯（扉の所は切る）
                spans = [(u0, u1)]
                if dt is not None:
                    spans = [(u0, dt - 0.85), (dt + 0.85, u1)]
                for (sa, sb) in spans:
                    if sb - sa > 0.2:
                        face_box(run, "stone_lt", sa, sb, 0.03, 1.36, 1.50)
            # 旗の位置の記録（窓・扉・日よけの近くは避ける）
            for bi in range(len(banners) - 1, -1, -1):
                if banners[bi][0] is not run:
                    break
                tb = banners[bi][1]
                if u0 - 1e-6 <= tb <= u1 and (any(abs(tb - w) < 1.5 for w in wins) or (dt is not None and abs(tb - dt) < 1.6)):
                    banners.pop(bi)
    # 旗・布（壁から 14cm 離して吊るす。下端 3.0m より上＝歩ける範囲の頭上。竿、布、帯）
    BCOL = ["coral", "teal", "pl_white"]
    BSTR = ["pl_white", "pl_white", "coral"]
    for (run, tb, ci_, depth) in banners:
        face_box(run, "wood_dark", tb - 0.50, tb + 0.50, 0.05, 3.86, 3.91, off=0.14)
        face_box(run, BCOL[ci_], tb - 0.38, tb + 0.38, 0.03, 3.00, 3.86, off=0.16)
        face_box(run, BSTR[ci_], tb - 0.38, tb + 0.38, 0.035, 3.40, 3.52, off=0.16)
        face_box(run, BCOL[ci_], tb - 0.20, tb + 0.20, 0.03, 3.00, 3.16, off=0.19)
    n_banner = len(banners)

    # ---------------------------------------------------------------- 2b. 床の飾り（当たり判定なし、舗装の上 0.4cm 以内の薄い線・帯・縁）
    # 舗装板の上面は 1cm（桟橋 1.5cm）。帯・縁は 1.0〜1.2cm、継ぎ目の線は 1.0〜1.4cm（高さを変えて Z ファイトを避ける）
    def fl_box(key, x0, x1, y0, y1, zt, z0=0.010):
        ibox(key, x0, x1, y0, y1, z0, zt)

    def joints(x0, x1, y0, y1, step, key, w=0.035, z0=0.010, zt=0.014):
        k = 1
        while x0 + k * step < x1 - 0.1:
            fl_box(key, x0 + k * step - w / 2, x0 + k * step + w / 2, y0, y1, zt, z0)
            k += 1
        k = 1
        while y0 + k * step < y1 - 0.1:
            fl_box(key, x0, x1, y0 + k * step - w / 2, y0 + k * step + w / 2, zt, z0)
            k += 1

    n_fl = len(pending["stone_lt"]) + len(pending["stone_dk"])
    # 壁ぎわの縁石（幅 30cm、明るい石）
    for (nx, ny, fixed, own, a, b) in runs:
        if b - a < 0.5:
            continue
        w_ = 0.30
        if nx:
            x_a, x_b = sorted((fixed, fixed + nx * w_))
            fl_box("stone_lt", x_a, x_b, a, b, 0.012)
        else:
            y_a, y_b = sorted((fixed, fixed + ny * w_))
            fl_box("stone_lt", a, b, y_a, y_b, 0.012)
    WALKD = {nm: (x0, x1, y0, y1) for nm, x0, x1, y0, y1 in WALK}
    # 通路：石畳の継ぎ目（2m の格子）と、6m ごとの明るい色の帯（進行方向に直角、幅 0.5m）
    for nm in ("ALane", "BLane", "MidLane"):
        x0, x1, y0, y1 = WALKD[nm]
        joints(x0, x1, y0, y1, 2.0, "stone_dk")
        xx = x0 + 3.0
        while xx < x1 - 0.5:
            fl_box("stone_lt", xx - 0.25, xx + 0.25, y0, y1, 0.012)
            xx += 6.0
    # 狭い通路（暗い石畳）：明るい線の継ぎ目（1.5m）
    for nm in ("AMain", "BMain", "AShort", "BShort"):
        x0, x1, y0, y1 = WALKD[nm]
        joints(x0, x1, y0, y1, 1.5, "stone_lt", w=0.03)
    # A サイト（石畳の広場）：継ぎ目（2m）と、4m ごとの明るい帯（南北に走る。幅 0.6m）
    x0, x1, y0, y1 = WALKD["ASite"]
    joints(x0, x1, y0, y1, 2.0, "stone_dk", w=0.04)
    xx = x0 + 4.0
    while xx < x1 - 1.0:
        fl_box("stone_lt", xx - 0.3, xx + 0.3, y0, y1, 0.012)
        xx += 6.0
    # 設置エリアのまわりの縁取り（ゾーン枠の外 0.8m に、幅 0.35m の明るい石）
    for zn in ("PlantZone_A", "PlantZone_B"):
        z = byname.get(zn)
        if z:
            zo, ze = z.get_actor_bounds(False)
            zx0, zx1 = zo.x / 100 - ze.x / 100, zo.x / 100 + ze.x / 100
            zy0, zy1 = zo.y / 100 - ze.y / 100, zo.y / 100 + ze.y / 100
            g = 0.8
            t_ = 0.35
            ox0, ox1, oy0, oy1 = zx0 - g - t_, zx1 + g + t_, zy0 - g - t_, zy1 + g + t_
            for (a0, a1, b0, b1) in ((ox0, ox1, oy0, oy0 + t_), (ox0, ox1, oy1 - t_, oy1), (ox0, ox0 + t_, oy0 + t_, oy1 - t_), (ox1 - t_, ox1, oy0 + t_, oy1 - t_)):
                fl_box("stone_lt", a0, a1, b0, b1, 0.013, z0=0.010)
            n_fl += 1
    # B サイト（甲板）：板（幅 0.45m）の向き = 南北（X 方向）の継ぎ目の線と、板ごとにずらした短い継ぎ目
    x0, x1, y0, y1 = WALKD["BSite"]
    pw = 0.45
    k = 1
    while y0 + k * pw < y1 - 0.1:
        yy = y0 + k * pw
        fl_box("stone_dk", x0, x1, yy - 0.012, yy + 0.012, 0.013)
        xb = x0 + ((k * 0.37) % 1.0) * 2.4 + 0.4
        while xb < x1 - 0.1:
            fl_box("stone_dk", xb - 0.012, xb + 0.012, yy - pw, yy, 0.013)
            xb += 2.4
        k += 1
    # 桟橋（攻撃スポーン）：板の継ぎ目（X 方向）
    for (px0, px1, py0, py1) in PIERS:
        k = 1
        while py0 + k * pw < py1 - 0.1:
            yy = py0 + k * pw
            fl_box("stone_dk", px0, px1, yy - 0.012, yy + 0.012, 0.0185, z0=0.0155)
            k += 1
    # ミッド（赤土の広場）：内側 2m の明るい縁取り（幅 0.4m）と、明るい線の継ぎ目（2m）
    x0, x1, y0, y1 = WALKD["Mid"]
    joints(x0, x1, y0, y1, 2.0, "stone_lt", w=0.03)
    ix0, ix1, iy0, iy1 = x0 + 2.0, x1 - 2.0, y0 + 2.0, y1 - 2.0
    for (a0, a1, b0, b1) in ((ix0, ix1, iy0, iy0 + 0.4), (ix0, ix1, iy1 - 0.4, iy1), (ix0, ix0 + 0.4, iy0 + 0.4, iy1 - 0.4), (ix1 - 0.4, ix1, iy0 + 0.4, iy1 - 0.4)):
        fl_box("stone_lt", a0, a1, b0, b1, 0.0125, z0=0.010)
    # 防衛スポーンの広場：継ぎ目（2m）
    x0, x1, y0, y1 = WALKD["DefSpawn"]
    joints(x0, x1, y0, y1, 2.0, "stone_dk", w=0.04)
    n_fl = len(pending["stone_lt"]) + len(pending["stone_dk"]) - n_fl
    # ---- 小物（Meshy。場外の飾り。当たり判定なし）の注文表。最後にアクタにする
    PROP_DIR = "/Game/PARORANT/Art/Props/"
    PROP_REQ = []   # (メッシュ名, x m, y m, z m, yaw 度, 縮尺)
    rng = random.Random(4242)

    def prop(name, x, y, z, yaw=None, sc=None):
        PROP_REQ.append((name, x, y, z, rng.uniform(0, 360) if yaw is None else yaw, rng.uniform(0.85, 1.15) if sc is None else sc))

    def terrace(lb, x0, x1, y0, y1):
        """大きな壁の箱の上（歩ける範囲の外、高さ 4m より上）：白い縁（パラペット）、青緑の笠、明るいテラス、縞の日よけ、ヤシ・低木・植木鉢"""
        ibox("pl_cream", x0, x1, y0, y1, WALL_TOP + 0.18, WALL_TOP + 0.20)
        t = 0.28
        for (a0, a1, b0, b1) in ((x0, x1, y0, y0 + t), (x0, x1, y1 - t, y1), (x0, x0 + t, y0 + t, y1 - t), (x1 - t, x1, y0 + t, y1 - t)):
            ibox("pl_white", a0, a1, b0, b1, WALL_TOP + 0.20, WALL_TOP + 0.70)
            ibox("teal", a0 - 0.02, a1 + 0.02, b0 - 0.02, b1 + 0.02, WALL_TOP + 0.70, WALL_TOP + 0.76)
        lx, ly = x1 - x0, y1 - y0
        # 縞の日よけ 2 つ（4 本の柱、高さ 2.4m。布は帯ごとに珊瑚色と白）
        for k, fx in enumerate((0.30, 0.72)):
            cx = x0 + lx * fx
            cy = (y0 + y1) / 2 + (-1 if k == 0 else 1) * ly * 0.12
            w, d = 5.0, 3.6
            zb = WALL_TOP + 2.6
            for sx_ in (-1, 1):
                for sy_ in (-1, 1):
                    inst("wood_cyl", cx + sx_ * (w / 2 - 0.1), cy + sy_ * (d / 2 - 0.1), WALL_TOP + 0.2 + 1.2, 0.12, 0.12, 2.4)
            nstr = 10
            for q in range(nstr):
                key = "coral" if q % 2 == 0 else "pl_white"
                ya, yb = cy - d / 2 + d * q / nstr, cy - d / 2 + d * (q + 1) / nstr
                ibox(key, cx - w / 2, cx + w / 2, ya, yb, zb, zb + 0.05)
            prop("SM_PotPlant", cx - w / 2 + 0.6, cy - d / 2 + 0.6, WALL_TOP + 0.2, sc=1.0)
            prop("SM_PotPlant", cx + w / 2 - 0.6, cy + d / 2 - 0.6, WALL_TOP + 0.2, sc=1.0)
        # ヤシ（四隅の内側）と、縁ぞいの低木
        e_ = 1.4   # 縁寄り（通路から見上げて見える）。幹は屋上の中、葉は 4m より上
        xm = (x0 + x1) / 2
        for (px, py, nm) in ((x0 + e_, y0 + e_, "SM_PalmTall"), (x1 - e_, y1 - e_, "SM_PalmTall"),
                             (x0 + e_, y1 - e_, "SM_PalmBent"), (x1 - e_, y0 + e_, "SM_PalmBent"),
                             (xm, y0 + e_, "SM_PalmBent"), (xm, y1 - e_, "SM_PalmTall")):
            prop(nm, px, py, WALL_TOP + 0.2)
        nb = int((lx + ly) // 5)
        for i in range(nb):
            u = rng.uniform(0, 2 * (lx + ly))
            if u < lx:
                bx, by = x0 + u, y0 + 1.0
            elif u < lx + ly:
                bx, by = x1 - 1.0, y0 + (u - lx)
            elif u < 2 * lx + ly:
                bx, by = x0 + (u - lx - ly), y1 - 1.0
            else:
                bx, by = x0 + 1.0, y0 + (u - 2 * lx - ly)
            prop("SM_TropicBush", bx, by, WALL_TOP + 0.2)

    # ---- 壁の上（4m より上は自由）：笠石、小さな建物の屋根
    n_roof = 0
    for i, (lb, (x0, x1, y0, y1)) in enumerate(wall_rects):
        lx, ly = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ibox("sandstone" if lb in FORT else "pl_white", x0 - 0.12, x1 + 0.12, y0 - 0.12, y1 + 0.12, WALL_TOP, WALL_TOP + 0.18)    # 笠（白い屋上の縁。砦だけ砂色の石）
        if lb not in FORT and min(lx, ly) > 12.0:
            terrace(lb, x0, x1, y0, y1)
            continue
        if lb in FORT or min(lx, ly) > 12.0:
            # 砦と大きな塊：胸壁（小さな四角の歯）を縁に
            if lb in FORT:
                step = 2.0
                for k in range(int(lx // step)):
                    for yy in (y0 + 0.2, y1 - 0.2):
                        ibox("sandstone", x0 + k * step + 0.3, x0 + k * step + 1.1, yy - 0.2, yy + 0.2, WALL_TOP + 0.18, WALL_TOP + 0.7)
            continue
        hw = min(lx, ly) / 2
        rise = min(1.6, hw * 0.4)
        ov = 0.35
        run_len = max(lx, ly) + 2 * ov
        ang = math.degrees(math.atan2(rise + 0.05, hw + ov))
        ln = math.hypot(hw + ov, rise + 0.05) + 0.1
        mid = (hw + ov) / 2
        zc = WALL_TOP + 0.18 + rise / 2 - 0.025
        if lx >= ly:
            inst("roof", cx, cy - mid, zc, run_len, ln, 0.18, rot=(0, 0, ang))
            inst("roof", cx, cy + mid, zc, run_len, ln, 0.18, rot=(0, 0, -ang))
        else:
            inst("roof", cx - mid, cy, zc, ln, run_len, 0.18, rot=(-ang, 0, 0))
            inst("roof", cx + mid, cy, zc, ln, run_len, 0.18, rot=(ang, 0, 0))
        n_roof += 2

    # ---------------------------------------------------------------- 3. 遮蔽の作り込み（当たり判定の箱は変えない。出っ張り 3cm 以内）
    def faces(cx, cy, sx, sy):
        return [(1, 0, sx / 2, sy, (0, 1)), (-1, 0, sx / 2, sy, (0, -1)), (0, 1, sy / 2, sx, (-1, 0)), (0, -1, sy / 2, sx, (1, 0))]

    def fbox(cx, cy, f, key, t0, t1, z0, z1, thick, off=0.0):
        nx, ny, dn, _lt, (tx, ty) = f
        nc = dn + off + thick / 2
        tm = (t0 + t1) / 2
        px, py = cx + nx * nc + tx * tm, cy + ny * nc + ty * tm
        if nx:
            inst(key, px, py, (z0 + z1) / 2, thick, t1 - t0, z1 - z0)
        else:
            inst(key, px, py, (z0 + z1) / 2, t1 - t0, thick, z1 - z0)

    def fdiag(cx, cy, f, key, t0, z0, t1, z1, width, thick, off=0.0):
        nx, ny, dn, _lt, (tx, ty) = f
        nc = dn + off + thick / 2
        tm, zm = (t0 + t1) / 2, (z0 + z1) / 2
        px, py = cx + nx * nc + tx * tm, cy + ny * nc + ty * tm
        d = (tx * (t1 - t0), ty * (t1 - t0), z1 - z0)
        inst_dir(key, px, py, zm, math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2), thick, width, d)

    def deco_crate(cx, cy, sx, sy, z0, h):
        """木箱：太い縁取り、板の継ぎ目、筋交い。出っ張り 3cm"""
        big = h > 1.5
        fw = 0.14 if big else 0.10
        for fi, f in enumerate(faces(cx, cy, sx, sy)):
            lt = f[3]
            a = lt / 2
            zt = z0 + h
            fbox(cx, cy, f, "wood_dark", -a, -a + fw, z0, zt, 0.03)
            fbox(cx, cy, f, "wood_dark", a - fw, a, z0, zt, 0.03)
            fbox(cx, cy, f, "wood_dark", -a + fw, a - fw, z0, z0 + fw, 0.03)
            fbox(cx, cy, f, "wood_dark", -a + fw, a - fw, zt - fw, zt, 0.03)
            if big:
                n = int(lt / 0.4)
                for k in range(1, n):
                    t = -a + lt * k / n
                    fbox(cx, cy, f, "iron", t - 0.012, t + 0.012, z0 + fw, zt - fw, 0.012)
                fdiag(cx, cy, f, "wood_dark", -a + fw, z0 + fw, a - fw, zt - fw, 0.12, 0.02, off=0.01)
                fdiag(cx, cy, f, "wood_dark", -a + fw, zt - fw, a - fw, z0 + fw, 0.12, 0.02, off=0.01)
            else:
                n = max(2, int(round(h / 0.33)))
                for k in range(1, n):
                    z = z0 + h * k / n
                    fbox(cx, cy, f, "iron", -a + fw, a - fw, z - 0.012, z + 0.012, 0.012)
                if fi % 2 == 0:
                    fdiag(cx, cy, f, "wood_dark", -a + fw, z0 + fw, a - fw, zt - fw, 0.09, 0.02, off=0.01)
                else:
                    fdiag(cx, cy, f, "wood_dark", -a + fw, zt - fw, a - fw, z0 + fw, 0.09, 0.02, off=0.01)
        zt = z0 + h
        ibox("wood_dark", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy - sy / 2 + fw, zt, zt + 0.03)
        ibox("wood_dark", cx - sx / 2, cx + sx / 2, cy + sy / 2 - fw, cy + sy / 2, zt, zt + 0.03)
        ibox("wood_dark", cx - sx / 2, cx - sx / 2 + fw, cy - sy / 2 + fw, cy + sy / 2 - fw, zt, zt + 0.03)
        ibox("wood_dark", cx + sx / 2 - fw, cx + sx / 2, cy - sy / 2 + fw, cy + sy / 2 - fw, zt, zt + 0.03)
        nb = max(2, int((sy - 2 * fw) / 0.4))
        for k in range(1, nb):
            yy = cy - sy / 2 + fw + (sy - 2 * fw) * k / nb
            ibox("iron", cx - sx / 2 + fw, cx + sx / 2 - fw, yy - 0.012, yy + 0.012, zt, zt + 0.012)

    def deco_stone(cx, cy, sx, sy, z0, h):
        """石の台：石の段の目地（横線）と継ぎ目（縦線、段ごとにずらす）、土台と笠。出っ張り 3cm 以内"""
        zt = z0 + h
        rows = max(2, int(round(h / 0.5)))
        for fi, f in enumerate(faces(cx, cy, sx, sy)):
            lt = f[3]
            a = lt / 2
            fbox(cx, cy, f, "sandstone", -a, a, z0, z0 + 0.14, 0.03)                       # 土台
            for r in range(1, rows):
                z = z0 + h * r / rows
                fbox(cx, cy, f, "iron", -a, a, z - 0.012, z + 0.012, 0.012)
            nj = max(2, int(lt / 0.7))
            for r in range(rows):
                za, zb = z0 + h * r / rows, z0 + h * (r + 1) / rows
                for k in range(nj):
                    t = -a + lt * (k + (0.5 if r % 2 else 0.0)) / nj
                    if -a < t < a:
                        fbox(cx, cy, f, "iron", t - 0.012, t + 0.012, za + 0.02, zb - 0.02, 0.012)
        ibox("sandstone", cx - sx / 2 - 0.0, cx + sx / 2, cy - sy / 2, cy + sy / 2, zt, zt + 0.03)  # 笠（上面）

    def deco_sack(cx, cy, sx, sy, z0, h):
        """麻袋の箱：縦の縄、横のふくらみの線、上面の結び目。出っ張り 3cm 以内"""
        zt = z0 + h
        rows = max(2, int(round(h / 0.35)))
        for fi, f in enumerate(faces(cx, cy, sx, sy)):
            lt = f[3]
            a = lt / 2
            for k in range(1, 4):
                t = -a + lt * k / 4
                fbox(cx, cy, f, "wood_dark", t - 0.02, t + 0.02, z0, zt, 0.02)             # 縄
            for r in range(1, rows):
                z = z0 + h * r / rows
                fbox(cx, cy, f, "wood_dark", -a, a, z - 0.012, z + 0.012, 0.015)
        for k in range(1, 4):
            xx = cx - sx / 2 + sx * k / 4
            ibox("wood_dark", xx - 0.02, xx + 0.02, cy - sy / 2, cy + sy / 2, zt, zt + 0.025)
            ibox("wood_dark", cx - sx / 2, cx + sx / 2, cy - sy / 2 + sy * k / 4 - 0.02, cy - sy / 2 + sy * k / 4 + 0.02, zt, zt + 0.025)

    n_cover = 0
    for a in all_actors:
        lb = a.get_actor_label()
        if not lb.startswith("Cover"):
            continue
        base = lb.rsplit("_", 1)[0] if lb[-1].isdigit() and "_" in lb else lb
        kind = COVER_KIND.get(base, "crate")
        set_all_mats(a, MATS[COVER_MAT[kind]])
        o, e = a.get_actor_bounds(False)
        cx, cy = o.x / 100.0, o.y / 100.0
        sx, sy, h = e.x / 100.0 * 2, e.y / 100.0 * 2, e.z / 100.0 * 2
        z0 = o.z / 100.0 - h / 2
        {"crate": deco_crate, "stone": deco_stone, "sack": deco_sack}[kind](cx, cy, sx, sy, z0, h)
        n_cover += 1

    # ---------------------------------------------------------------- 4. 外：砂浜と海、防波堤、桟橋、浜の小屋（すべて外周の外、当たり判定なし）
    R0 = 41.0   # 床・外周の壁の外縁
    # 砂浜（乾いた砂 → 濡れた砂）と海
    for (x0, x1, y0, y1) in ((R0, 60, -60, 60), (-60, -R0, -60, 60), (-R0, R0, R0, 60), (-R0, R0, -60, -R0)):
        ibox("sand", x0, x1, y0, y1, -0.40, -0.15)
    ibox("sand", R0, 70, -70, 70, -0.9, -0.55)
    ibox("sand", -70, -R0, -70, 70, -0.9, -0.55)
    ibox("sand", -R0, R0, R0, 70, -0.9, -0.55)
    ibox("sand", -R0, R0, -70, -R0, -0.9, -0.55)
    for (x0, x1, y0, y1) in ((70, 71, -71, 71), (-71, -70, -71, 71), (-70, 70, 70, 71), (-70, 70, -71, -70)):
        ibox("foam", x0, x1, y0, y1, -1.0, -0.98)
    ibox("sea", -600, 600, -600, 600, -1.60, -1.55)   # 沖（濃い青）。岸の近くは SeaShallow の板（高さ -1.30）
    # 桟橋（攻撃側の南へ。板と杭）
    ibox("deck", -R0 - 30, -R0, -3.0, 3.0, -0.18, -0.12)
    for k in range(0, 8):
        xx = -R0 - 3.5 - k * 4.0
        for yy in (-2.7, 2.7):
            inst("wood_cyl", xx, yy, -0.6, 0.35, 0.35, 1.0)
    # 防波堤（低い石積み。東と西の海に張り出す）
    ibox("sandstone", -25, 25, 72, 74, -1.35, 0.5)
    ibox("sandstone", -25, 25, -74, -72, -1.35, 0.5)
    ibox("sandstone", 72, 74, -25, 25, -1.35, 0.5)
    # 浜の小屋（白い漆喰に珊瑚色の屋根）
    HUTS = [(50, -20, 6, 5), (48, 22, 5, 6), (-20, 50, 6, 5), (22, -52, 5, 6), (-50, 18, 6, 5), (-48, -24, 5, 6), (6, 54, 6, 5), (-8, -56, 5, 6)]
    for i, (hx, hy, sx_, sy_) in enumerate(HUTS):
        ibox("pl_white" if i % 2 == 0 else "pl_cream", hx - sx_ / 2, hx + sx_ / 2, hy - sy_ / 2, hy + sy_ / 2, -0.15, 3.2)
        hw = min(sx_, sy_) / 2 + 0.3
        for sg in (-1, 1):
            if sx_ >= sy_:
                inst("coral", hx, hy + sg * hw / 2, 3.2 + 0.5, sx_ + 0.6, hw + 0.2, 0.12, rot=(0, 0, -sg * 20))
            else:
                inst("coral", hx + sg * hw / 2, hy, 3.2 + 0.5, hw + 0.2, sy_ + 0.6, 0.12, rot=(sg * 20, 0, 0))

    # 浅い海（岸の近く。水色）。沖の海は ISM の "sea"（濃い青）
    spawn_slab("SeaShallow", -115, 115, -115, 115, -1.34, -1.30, MATS["MI_Pind_SeaShallow"])

    # ---------------------------------------------------------------- 4b. 外の小物（ヤシ、低木、小舟、パラソル）。砂浜は高さ -0.15、海は -1.30
    HUT_XY = [(h[0], h[1]) for h in HUTS]
    PARASOLS = [(52, 6), (46, -9), (-55, -12), (-46, 6)]
    BEACH_Z = -0.15

    def free_spot(x, y, others, dmin, hut_r=7.0):
        if any(math.hypot(x - hx, y - hy) < hut_r for hx, hy in HUT_XY):
            return False
        if any(math.hypot(x - px, y - py) < 4.0 for px, py in PARASOLS):
            return False
        if x < -41 and (abs(y) < 9 or 26 < abs(y) < 40):
            return False                       # 桟橋ぞい
        return all(math.hypot(x - ox, y - oy) >= dmin for ox, oy in others)

    def beach_point(lo, hi):
        side = rng.choice("NSEW")
        t = rng.uniform(lo, hi)
        u = rng.uniform(-56, 56)
        return {"N": (t, u), "S": (-t, u), "E": (u * 0.7, t), "W": (u * 0.7, -t)}[side]

    palms = []
    tries = 0
    while len(palms) < 14 and tries < 4000:
        tries += 1
        x, y = beach_point(45.0, 58.0)
        if free_spot(x, y, palms, 7.0):
            palms.append((x, y))
    for i, (x, y) in enumerate(palms):
        prop("SM_PalmTall" if i % 2 == 0 else "SM_PalmBent", x, y, BEACH_Z)
    bushes = []
    tries = 0
    while len(bushes) < 14 and tries < 4000:
        tries += 1
        x, y = beach_point(42.5, 47.0)
        if free_spot(x, y, bushes + palms, 3.0, hut_r=5.0):
            bushes.append((x, y))
    for (x, y) in bushes:
        prop("SM_TropicBush", x, y, BEACH_Z)
    for (x, y) in PARASOLS:
        prop("SM_Parasol", x, y, BEACH_Z, sc=1.0)
    for (x, y) in ((-85, 12), (-90, -20), (75, 40), (0, 85)):
        prop("SM_Rowboat", x, y, -1.50, sc=rng.uniform(0.9, 1.1))

    # 外周の壁のすぐ外側の高いヤシ（壁の上から葉がのぞく。場外、当たり判定なし）。壁の外縁 41m の 2.5m 外
    rim = []
    for yy in range(-32, 36, 6):
        rim.append((43.5, float(yy)))
    for xx in range(-32, 36, 6):
        rim.append((float(xx), -43.5))
        rim.append((float(xx), 43.5))
    for yy in (-14.0, 14.0):
        rim.append((-43.5, yy))
    n_rim = 0
    for i, (x, y) in enumerate(rim):
        if any(math.hypot(x - hx, y - hy) < 4.5 for hx, hy in HUT_XY):
            continue
        prop("SM_PalmTall" if i % 3 != 1 else "SM_PalmBent", x + rng.uniform(-0.6, 0.6), y + rng.uniform(-0.6, 0.6), BEACH_Z)
        n_rim += 1
    print("PIND RIM PALMS:", n_rim)

    for (nm, x, y, z, yaw, sc) in PROP_REQ:
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(cm(x), cm(y), cm(z)), unreal.Rotator(0, 0, yaw))
        a.set_actor_label("Prop_" + nm[3:])
        a.set_folder_path("Art/Props")
        c = a.static_mesh_component
        c.set_mobility(unreal.ComponentMobility.STATIC)
        c.set_static_mesh(ea.load_asset(PROP_DIR + nm))
        a.set_actor_scale3d(unreal.Vector(sc, sc, sc))
        c.set_collision_profile_name("NoCollision")
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_editor_property("can_ever_affect_navigation", False)
        a.set_editor_property("tags", ART_TAG)
    print("PIND PROPS:", len(PROP_REQ), "palms on beach", len(palms), "bushes on beach", len(bushes))

    # ---------------------------------------------------------------- 4c. 角の小物（Step 42b C、docs/26 §10 と同じ決まり）
    # 道の角・壁ぎわに、Meshy の小物（樽・小箱・麻袋・植木鉢・壺。簡易コリジョン＝凸 1 個、乗れる）を 1〜3 個ずつ置く。当たり判定あり（BlockAll）。
    # ナビメッシュに影響する（置いたあと、ナビメッシュをビルドし直す）。タグ PindDeco、フォルダ Art/Deco。作り直しは冒頭でタグ PindDeco を消す。
    # 位置は docs/tools/map_deco_sites_l_pind.py（オフラインの計算。壁から離さない、持ち場・経由点から 1.5m、設置エリアの縁から 2m、バリアから 2.5m、
    # スポーンから 6m 以内に置かない）の結果をそのまま書いた表。(番号, 場所, [(X m, Y m, 向き yaw 度, ばらつき, 種類), ...])
    DECO_SITES = [
        ("P01", "攻撃スポーンの南西の隅", [(-38.530, -36.550, 234.3, 0.93, "crate")]),   # 樽 2 個を外した（42c-2：FlankPoint_P_1 への経路が 30.8→33.9m に変わる原因。ナビのタイルの切り直し）
        ("P02", "攻撃スポーンの北西の隅", [(-38.530, 36.550, 13.5, 0.99, "pot")]),   # 樽 1 個を外した（42c-2：FlankPoint_N_1 への経路が 30.8→36.5m に変わる原因）
        ("P03", "A サイトの奥の隅（北東）", [(33.250, -37.250, 25.1, 0.93, "crate"), (32.530, -37.250, 152.8, 1.05, "sack"), (33.250, -36.530, 44.6, 0.96, "amphora")]),
        ("P04", "B サイトの奥の隅（北西）", [(33.250, 37.250, 225.9, 1.07, "sack"), (32.530, 37.250, 207.8, 0.98, "barrel")]),
        ("P05", "ミッドの南西の隅", [(-9.550, -11.550, 351.5, 0.93, "pot"), (-9.550, -10.830, 309.0, 0.97, "barrel")]),
        ("P06", "ミッドの北西の隅", [(-9.550, 11.550, 51.9, 0.94, "amphora"), (-9.550, 10.830, 111.1, 1.05, "sack")]),
        # P07（ミッドの南東の隅。樽 (9.55,-11.95)・小箱 (9.55,-11.23)）は外した（42c-2：Hold_A3 への経路が 72.66→72.49m に変わる原因。1 個だけ外す・15〜50cm ずらすでは直らず、2 個とも外すと戻る）
        ("P08", "ミッドの北東の隅", [(9.550, 11.950, 197.2, 0.93, "crate"), (9.550, 11.230, 21.5, 0.95, "amphora")]),
        ("P11", "防衛側 A ルートの奥の隅", [(39.550, -15.550, 163.1, 0.97, "pot"), (38.830, -15.550, 286.0, 1.03, "barrel")]),
        ("P12", "防衛側 B ルートの奥の隅", [(39.550, 15.550, 87.9, 1.01, "barrel"), (38.830, 15.550, 189.1, 1.06, "pot"), (39.550, 14.830, 262.6, 0.97, "sack")]),
    ]
    # 種類 → (メッシュ, 素材（None=メッシュのまま）, 縮尺。樽より幅・高さが広がらないように決めた値)
    DECO_KIND = {"barrel": ("SM_BarrelSmall", "MI_Barrel", 1.0), "crate": ("SM_CrateSmall", None, 0.86), "sack": ("SM_SackPile", None, 1.0),
                 "pot": ("SM_PotPlant", None, 0.78), "amphora": ("SM_Amphora", None, 0.95)}
    n_deco = 0
    for sid, _desc, bl in DECO_SITES:
        for k, (bx, by, yaw, vary, kind) in enumerate(bl):
            mesh, mat, base_sc = DECO_KIND[kind]
            a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(cm(bx), cm(by), 0.0), unreal.Rotator(0.0, 0.0, yaw))
            a.set_actor_label("Deco_%s_%s_%d" % (kind.capitalize(), sid, k + 1))
            a.set_folder_path("Art/Deco")
            c = a.static_mesh_component
            c.set_mobility(unreal.ComponentMobility.STATIC)
            c.set_static_mesh(ea.load_asset(PROP_DIR + mesh))
            sc = base_sc * vary
            a.set_actor_scale3d(unreal.Vector(sc, sc, sc))
            if mat:
                c.set_material(0, ea.load_asset(PROP_DIR + mat))
            c.set_collision_profile_name("BlockAll")
            a.set_editor_property("tags", [unreal.Name("PindDeco")])
            n_deco += 1
    print("PIND DECO:", n_deco, "items in", len(DECO_SITES), "sites")

    # ---------------------------------------------------------------- 5. 紹介画面の間は壁の上の屋根を隠す（GameMode の SetIntroHide が、タグ IntroHide のコンポーネントを切り替える）
    rc = ism["roof"]
    ct = list(rc.component_tags)
    if unreal.Name("IntroHide") not in ct:
        ct.append(unreal.Name("IntroHide"))
        rc.component_tags = ct

    # ---------------------------------------------------------------- ISM に流し込む
    total = 0
    for k, lst in pending.items():
        if lst:
            ism[k].add_instances(lst, False)
        total += len(lst)
    print("PIND ART: runs", n_run, "windows", n_win, "doors", n_door, "awnings", n_awn, "roofs", n_roof, "covers", n_cover,
          "banners", n_banner, "floor decor", n_fl, "overlays", n_overlay, "panels", len(panels), "ISM instances", total, {k: len(v) for k, v in pending.items()})

    # 光の仕上げ
    _light = unreal.Paths.project_dir() + "docs/tools/map_light_l_pind.py"
    exec(compile(open(_light, encoding="utf-8").read(), _light, "exec"), {"unreal": unreal})
