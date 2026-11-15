"""PARORANT L_Canal 見た目の追加スクリプト（Step 38、docs/26_art_meshy.md §6）。

map_layout_l_canal.py の最後から実行される（ART_ONLY = True を先に定義して map_layout_l_canal.py を
実行すると、ブロックアウトは作らず、この見た目だけを作り直す）。

大原則（docs/26 §1）：足す見た目はすべて当たり判定なし（NoCollision）・ナビメッシュに影響しない・タグ CanalArt。
  - 小さな部品（腰壁、縁取り、窓、扉、アーチ、場外の建物、街灯の柱）は、アクタ "ArtHost" の
    InstancedStaticMeshComponent（名前 ISM_<key>、key は ISM_KEYS の 12 個）に入れる。ISM_<key> は Unreal MCP の edit_component で
    先に足しておく（Python からはコンポーネントを足せないため）。足りなければ不足の一覧を出して止まる。
  - 床の舗装の違い（れんが・板・タイル）は薄い板のアクタ（タグ CanalArt）
  - Step 38b：遮蔽の作り込み（§7）の飾りは ISM。円柱の部品用に ISM_iron_cyl / ISM_stone_cyl / ISM_door_cyl / ISM_water_cyl
    （メッシュは Cylinder）と ISM_plank も必要。これも MCP の edit_component で先に足す
    （componentType = InstancedStaticMeshComponent、meshPath = /Engine/BasicShapes/Cylinder など）
  - Step 38b：乗れる樽の飾り（§8）は StaticMeshActor（タグ CanalDeco、フォルダ Art/Deco）。作り直しでは CanalDeco も消す
  - 作り直しは「タグ CanalArt のアクタを消す」「ISM の中身を空にする」だけ。ゲーム用の配置には触らない
座標は m（+X が北、+Y が東、床の上面が Z=0）。
"""
import math
import random

try:
    import unreal
except ImportError:
    unreal = None

# ------------------------------------------------------------------ 素材の色（リニア値。夕暮れ寄りの光で彩度が上がりすぎないよう、少し褪せた色）
ART_COLORS = {
    "MI_Canal_Plaster_Ochre":  (0.48, 0.37, 0.21),   # 漆喰（黄土）
    "MI_Canal_Plaster_Salmon": (0.45, 0.28, 0.23),   # 漆喰（薄赤、くすんだサーモン）
    "MI_Canal_Plaster_Cream":  (0.53, 0.49, 0.40),   # 漆喰（クリーム。旧 0.64/0.56/0.43 より少し落とす）
    "MI_Canal_Stone":          (0.36, 0.35, 0.33),   # 石（明るい灰）
    "MI_Canal_Roof":           (0.27, 0.095, 0.05),   # 素焼き（赤茶）
    "MI_Canal_Cobble":         (0.26, 0.22, 0.18),   # 石畳（灰がかった茶）
    "MI_Canal_Brick":          (0.26, 0.13, 0.09),   # れんが（赤茶、暗め）
    "MI_Canal_Planks":         (0.29, 0.18, 0.10),   # 板（茶）
    "MI_Canal_Tile":           (0.34, 0.28, 0.21),   # 屋内のタイル（明るい砂色。暖色の灯りで橙に寄りすぎないように）
    "MI_Canal_Water":          (0.03, 0.19, 0.24),   # 水（緑がかった青）
    "MI_Canal_Wood":           (0.34, 0.21, 0.10),   # 木箱・板（既存の色を少し明るく）
    "MI_Canal_Shutter_Green":  (0.06, 0.17, 0.10),   # 鎧戸（深緑）
    "MI_Canal_Shutter_Red":    (0.22, 0.05, 0.06),   # 鎧戸（えんじ）
    "MI_Canal_Door":           (0.20, 0.11, 0.06),   # 扉（濃い茶）
    "MI_Canal_Glass":          (0.025, 0.035, 0.05),  # 窓ガラス（暗い青灰）
    "MI_Canal_Iron":           (0.035, 0.035, 0.04),  # 鉄（街灯の柱）
    "MI_Canal_Lamp":           (0.80, 0.62, 0.30),   # 灯りの傘（淡い黄）
    "MI_Canal_Wall_Ring":      (0.40, 0.37, 0.32),   # 外周の壁（港の石壁）
}
ISM_KEYS = {   # key: 素材名、影を落とすか
    "stone": ("MI_Canal_Stone", False), "roof": ("MI_Canal_Roof", True),
    "shutter_g": ("MI_Canal_Shutter_Green", False), "shutter_r": ("MI_Canal_Shutter_Red", False),
    "door": ("MI_Canal_Door", False), "glass": ("MI_Canal_Glass", False), "iron": ("MI_Canal_Iron", False),
    "lampglass": ("MI_Canal_Lamp", False),
    "pl_ochre": ("MI_Canal_Plaster_Ochre", False), "pl_salmon": ("MI_Canal_Plaster_Salmon", False),
    "pl_cream": ("MI_Canal_Plaster_Cream", False),
    "roof_far": ("MI_Canal_Roof", False),   # 場外の建物と鐘楼の屋根。場外の高い建物の影が、日なたになるはずの船着き場・広場まで届かないように、影を落とさない
    # Step 38b：遮蔽の飾り。*_cyl は Cylinder メッシュ（直径 1m、高さ 1m に拡縮して使う）
    "plank": ("MI_Canal_Planks", False),
    "iron_cyl": ("MI_Canal_Iron", False), "stone_cyl": ("MI_Canal_Stone", False),
    "door_cyl": ("MI_Canal_Door", False), "water_cyl": ("MI_Canal_Water", False),
}
CYL_KEYS = {"iron_cyl", "stone_cyl", "door_cyl", "water_cyl"}
PLASTERS = ["MI_Canal_Plaster_Ochre", "MI_Canal_Plaster_Salmon", "MI_Canal_Plaster_Cream"]
PL_KEY = {"MI_Canal_Plaster_Ochre": "pl_ochre", "MI_Canal_Plaster_Salmon": "pl_salmon", "MI_Canal_Plaster_Cream": "pl_cream"}

# 床の舗装（WALK の名前 → 素材）。それ以外は石畳（床の箱そのものの素材）
FLOOR_OVERLAY = {
    "Alley1": "MI_Canal_Brick", "Alley2": "MI_Canal_Brick", "Alley3": "MI_Canal_Brick", "AMain": "MI_Canal_Brick",
    "AtkSpawn": "MI_Canal_Planks", "Quay1": "MI_Canal_Planks", "Quay2": "MI_Canal_Planks",
    "ASite": "MI_Canal_Tile",
}

# 設定値
WALL_TOP = 8.0
PLINTH_H = 1.0
WIN_Z = 4.5
INNER_ROOF = (8.0, 26.0, -32.0, -14.0)   # A_Roof の範囲。この下は屋内
ARCHES = [  # (向き, 線の座標, 幅の範囲, 通路のある側 -1/+1)  向き 'x' = 通路が X 方向に伸びる（線は X=const）
    ("x", 8.0, (-21.75, -18.25), -1),    # A 市場の入口（AMain の東端）
    ("x", -18.0, (-3.0, 3.0), -1),       # 橋への道 → 広場の入口
    ("y", -6.0, (12.0, 16.0), -1),       # 回廊（AShort、鐘楼の下から A へ。通路は -Y 側）の入口
    ("y", 8.0, (12.0, 16.0), +1),        # アーチ（BShort、鐘楼の下から B へ。通路は +Y 側）
]


if unreal is not None:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    ea = unreal.EditorAssetLibrary
    MAT_DIR = "/Game/PARORANT/Materials"
    _world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
    if not _world.startswith("/Game/PARORANT/Maps/L_Canal"):
        raise RuntimeError("L_Canal を開いてから実行してください（今のレベル: %s）" % _world)

    ART_TAG = [unreal.Name("CanalArt")]
    CUBE = ea.load_asset("/Engine/BasicShapes/Cube")
    CYLMESH = ea.load_asset("/Engine/BasicShapes/Cylinder")

    def mi(name):
        """素材インスタンス（無ければ作る）。色は ART_COLORS の値にそろえる（再実行しても同じ）。"""
        path = f"{MAT_DIR}/{name}"
        if ea.does_asset_exist(path):
            m = ea.load_asset(path)
        else:
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            m = tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
            m.set_editor_property("parent", ea.load_asset(f"{MAT_DIR}/M_NatureFlat"))
        c = ART_COLORS[name]
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(m, "Color", unreal.LinearColor(c[0], c[1], c[2], 1.0))
        unreal.MaterialEditingLibrary.update_material_instance(m)
        ea.save_loaded_asset(m)
        return m

    MATS = {n: mi(n) for n in ART_COLORS}

    # ---------------------------------------------------------------- 前回の見た目を消す
    all_actors = list(eas.get_all_level_actors())
    host = None
    for a in all_actors:
        if a.get_actor_label() == "ArtHost":
            host = a
            continue
        if unreal.Name("CanalArt") in a.tags or unreal.Name("CanalDeco") in a.tags:
            a.destroy_actor()
    if host is None:
        raise RuntimeError("アクタ ArtHost がありません（plain Actor を置き、ISM_<key> を edit_component で足す。docs/26 の実装結果を参照）")
    comps = {c.get_name(): c for c in host.get_components_by_class(unreal.InstancedStaticMeshComponent)}
    missing = [k for k in ISM_KEYS if "ISM_" + k not in comps]
    if missing:
        raise RuntimeError("ArtHost に足りない ISM: " + ", ".join("ISM_" + k for k in missing))
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

    def spawn_slab(label, x0, x1, y0, y1, z0, z1, mat, folder="Art"):
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

    # ---------------------------------------------------------------- 1. 壁の塗り分け（隣り合う箱で色を変える。1 つの箱は 1 色）
    byname = {a.get_actor_label(): a for a in all_actors}

    def touching(r1, r2):
        ax0, ax1, ay0, ay1 = r1
        bx0, bx1, by0, by1 = r2
        if (abs(ax1 - bx0) < 1e-6 or abs(bx1 - ax0) < 1e-6) and min(ay1, by1) - max(ay0, by0) > 1e-6:
            return True
        if (abs(ay1 - by0) < 1e-6 or abs(by1 - ay0) < 1e-6) and min(ax1, bx1) - max(ax0, bx0) > 1e-6:
            return True
        return False

    wall_color = {}
    for i, r in enumerate(wall_rects):
        cy = (r[2] + r[3]) / 2
        if cy < -4:
            pref = ["MI_Canal_Plaster_Ochre", "MI_Canal_Plaster_Salmon", "MI_Canal_Plaster_Cream"]   # A 側：黄土と薄赤
        elif cy > 4:
            pref = ["MI_Canal_Plaster_Cream", "MI_Canal_Plaster_Ochre", "MI_Canal_Plaster_Salmon"]   # B 側：クリームと黄土
        else:
            pref = ["MI_Canal_Plaster_Cream", "MI_Canal_Plaster_Salmon", "MI_Canal_Plaster_Ochre"]
        used = {wall_color[j] for j in wall_color if touching(r, wall_rects[j])}
        free = [p for p in pref if p not in used]
        wall_color[i] = free[0] if free else pref[i % 3]
        a = byname.get(f"Wall_{i:02d}")
        if a:
            a.static_mesh_component.set_material(0, MATS[wall_color[i]])
    ring_color = {"Wall_S": "MI_Canal_Wall_Ring", "Wall_N": "MI_Canal_Plaster_Cream",
                  "Wall_E": "MI_Canal_Plaster_Cream", "Wall_W": "MI_Canal_Plaster_Salmon"}
    for n, mname in ring_color.items():
        if n in byname:
            byname[n].static_mesh_component.set_material(0, MATS[mname])
    # 床：石畳。れんが・板・タイルは薄い板を重ねる
    for a in all_actors:
        if a.get_actor_label().startswith("Floor_"):
            a.static_mesh_component.set_material(0, MATS["MI_Canal_Cobble"])
    # 既存の部品の素材（形は変えない）
    for a in all_actors:
        lb = a.get_actor_label()
        if lb == "CanalWater":
            a.static_mesh_component.set_material(0, MATS["MI_Canal_Water"])
        elif lb == "A_Roof":
            a.static_mesh_component.set_material(0, MATS["MI_Canal_Planks"])   # 屋内から見える天井。板張り
    n_overlay = 0
    for nm, x0, x1, y0, y1 in WALK:
        if nm in FLOOR_OVERLAY:
            spawn_slab("Paving_" + nm, x0, x1, y0, y1, 0.0, 0.01, MATS[FLOOR_OVERLAY[nm]])
            n_overlay += 1

    # ---------------------------------------------------------------- 2. 壁の面（歩ける範囲・運河から見える面）に腰壁、縁取り、窓、扉
    owner = [[-1] * W for _ in range(W)]
    for i, (x0, x1, y0, y1) in enumerate(wall_rects):
        for ix in range(ci(x0), ci(x1)):
            for iy in range(ci(y0), ci(y1)):
                owner[ix][iy] = i

    def is_open(ix, iy):
        return 0 <= ix < W and 0 <= iy < W and (walk[ix][iy] or canal[ix][iy])

    def is_solid(ix, iy):
        return not (0 <= ix < W and 0 <= iy < W) or (not walk[ix][iy] and not canal[ix][iy])

    def inner_cell(ix, iy):
        x = (ix + 0.5) / S - N
        y = (iy + 0.5) / S - N
        return INNER_ROOF[0] < x < INNER_ROOF[1] and INNER_ROOF[2] < y < INNER_ROOF[3]

    runs_raw = {}
    for ix in range(W):
        for iy in range(W):
            if not is_open(ix, iy):
                continue
            water = canal[ix][iy] and not walk[ix][iy]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):   # 開いたセルから見た壁の向き（面の法線は逆）
                jx, jy = ix + dx, iy + dy
                if not is_solid(jx, jy):
                    continue
                own = owner[jx][jy] if (0 <= jx < W and 0 <= jy < W) else -2
                if own == -1:
                    continue   # ありえない（壁でも歩けるでもない所は壁の箱になる）
                # 面の座標：開いたセルと壁のセルの境界
                if dx:
                    fixed = (max(ix, jx)) / S - N     # 境界の X
                    pos = iy
                else:
                    fixed = (max(iy, jy)) / S - N
                    pos = ix
                key = (dx, dy, round(fixed, 4), own, inner_cell(ix, iy), water)
                runs_raw.setdefault(key, []).append(pos)

    runs = []   # (nx, ny, fixed, owner, inner, water, a, b)
    for (dx, dy, fixed, own, inner, water), lst in runs_raw.items():
        lst.sort()
        s = p = lst[0]
        for v in lst[1:] + [None]:
            if v is not None and v == p + 1:
                p = v
                continue
            runs.append((-dx, -dy, fixed, own, inner, water, s / S - N, (p + 1) / S - N))
            if v is not None:
                s = p = v
    runs.sort(key=lambda r: (r[2], r[0], r[1], r[6]))

    def face_box(run, key, t0, t1, thick, z0, z1, off=0.0):
        """面の上の箱。t0〜t1 は面に沿った位置、thick は面から出る厚み、off は面から離す量。"""
        nx, ny, fixed = run[0], run[1], run[2]
        # 法線方向の範囲 [n0, n1]
        if nx > 0 or ny > 0:
            n0, n1 = fixed + off, fixed + off + thick
        else:
            n0, n1 = fixed - off - thick, fixed - off
        if nx:
            ibox(key, n0, n1, t0, t1, z0, z1)
        else:
            ibox(key, t0, t1, n0, n1, z0, z1)

    n_win = n_door = n_run = 0
    for ri, run in enumerate(runs):
        nx, ny, fixed, own, inner, water, a, b = run
        L = b - a
        if L < 1.5:
            continue
        n_run += 1
        zb = -1.0 if water else 0.0
        top = 7.0 if inner else WALL_TOP
        # 腰壁（石）と上端の石の縁
        face_box(run, "stone", a, b, 0.07, zb, PLINTH_H)
        face_box(run, "stone", a, b, 0.10, PLINTH_H, PLINTH_H + 0.12)
        face_box(run, "stone", a, b, 0.10, top - 0.40, top)
        if not inner:
            face_box(run, "stone", a, b, 0.06, 3.0, 3.18)       # 階の境の帯
        # 窓（2 階の高さ）。鎧戸の色は面ごとに緑とえんじを入れ替える
        usable = L - 1.8
        nwin = min(4, int(usable // 3.0)) if usable >= 2.0 else 0
        shut = "shutter_g" if (ri % 2 == 0) else "shutter_r"
        for k in range(nwin):
            t = a + 0.9 + usable * (k + 0.5) / nwin
            face_box(run, "stone", t - 0.65, t + 0.65, 0.05, WIN_Z - 0.95, WIN_Z + 0.95)             # 枠
            face_box(run, "glass", t - 0.5, t + 0.5, 0.06, WIN_Z - 0.8, WIN_Z + 0.8, off=0.0)        # ガラス（枠より 1cm 出る）
            face_box(run, shut, t - 1.10, t - 0.66, 0.08, WIN_Z - 0.85, WIN_Z + 0.85)                # 鎧戸
            face_box(run, shut, t + 0.66, t + 1.10, 0.08, WIN_Z - 0.85, WIN_Z + 0.85)
            n_win += 1
        # 扉（1 階。水に面した面にはつけない）
        if not water and usable >= 3.2:
            ndoor = 1 if usable < 11 else 2
            for k in range(ndoor):
                frac = 0.35 + 0.30 * k if ndoor == 1 else 0.25 + 0.5 * k
                t = a + 0.9 + usable * frac
                face_box(run, "stone", t - 0.80, t + 0.80, 0.05, 0.0, 2.45)
                face_box(run, "door", t - 0.62, t + 0.62, 0.08, 0.0, 2.25)
                n_door += 1

    # ---------------------------------------------------------------- 3. 壁の上の屋根（素焼き色。長い方向に棟を通した 2 枚の傾いた板、細い箱は平らな板）
    n_roof = 0
    for i, (x0, x1, y0, y1) in enumerate(wall_rects):
        lx, ly = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if min(lx, ly) < 2.0:
            ibox("roof", x0 - 0.15, x1 + 0.15, y0 - 0.15, y1 + 0.15, WALL_TOP, WALL_TOP + 0.15)
            n_roof += 1
            continue
        hw = min(lx, ly) / 2
        rise = min(1.6, hw * 0.4)
        ov = 0.35
        run_len = max(lx, ly) + 2 * ov
        ang = math.degrees(math.atan2(rise + 0.05, hw + ov))
        ln = math.hypot(hw + ov, rise + 0.05) + 0.1
        mid = (hw + ov) / 2
        zc = WALL_TOP + rise / 2 - 0.025
        if lx >= ly:   # 棟は X 方向。板は Y 方向の両側へ傾く（roll）
            inst("roof", cx, cy - mid, zc, run_len, ln, 0.22, rot=(0, 0, ang))
            inst("roof", cx, cy + mid, zc, run_len, ln, 0.22, rot=(0, 0, -ang))
        else:          # 棟は Y 方向。板は X 方向の両側へ傾く（pitch）
            inst("roof", cx - mid, cy, zc, ln, run_len, 0.22, rot=(-ang, 0, 0))
            inst("roof", cx + mid, cy, zc, ln, run_len, 0.22, rot=(ang, 0, 0))
        n_roof += 2

    # ---------------------------------------------------------------- 4. アーチ（柱 2 本と梁。出っ張りは 10cm、梁は 3.4m 以上の高さ）
    for axis, line, (u0, u1), side in ARCHES:
        l0, l1 = (line - 0.7, line) if side < 0 else (line, line + 0.7)
        if axis == "x":
            ibox("stone", l0, l1, u0 - 0.1, u1 + 0.1, 3.4, 4.0)                    # 梁
            ibox("stone", l0, l1, u0, u0 + 0.10, 0.0, 3.4)                          # 柱
            ibox("stone", l0, l1, u1 - 0.10, u1, 0.0, 3.4)
            ibox("stone", l0, l1, u0 + 0.10, u0 + 0.40, 3.0, 3.4)                  # 角の入り（45 度に切った形に見せる段）
            ibox("stone", l0, l1, u1 - 0.40, u1 - 0.10, 3.0, 3.4)
            inst("stone", (l0 + l1) / 2, u0 + 0.40, 3.1, l1 - l0, 0.4, 0.4, rot=(0, 0, 45))
            inst("stone", (l0 + l1) / 2, u1 - 0.40, 3.1, l1 - l0, 0.4, 0.4, rot=(0, 0, 45))
        else:
            ibox("stone", u0 - 0.1, u1 + 0.1, l0, l1, 3.4, 4.0)
            ibox("stone", u0, u0 + 0.10, l0, l1, 0.0, 3.4)
            ibox("stone", u1 - 0.10, u1, l0, l1, 0.0, 3.4)
            ibox("stone", u0 + 0.10, u0 + 0.40, l0, l1, 3.0, 3.4)
            ibox("stone", u1 - 0.40, u1 - 0.10, l0, l1, 3.0, 3.4)
            inst("stone", u0 + 0.40, (l0 + l1) / 2, 3.1, 0.4, l1 - l0, 0.4, rot=(0, 0, 45))
            inst("stone", u1 - 0.40, (l0 + l1) / 2, 3.1, 0.4, l1 - l0, 0.4, rot=(0, 0, 45))

    # ---------------------------------------------------------------- 5. 場外の建物の影（当たり判定なし）と鐘楼
    rnd = random.Random(38)
    OUT_GAP = 3.0       # 外周の壁（36〜37）の外側から
    outer = []          # (x0, x1, y0, y1, h)

    def band(side):
        pos = -52.0
        while pos < 52.0:
            w = rnd.uniform(8.0, 14.0)
            d = rnd.uniform(8.0, 12.0)
            h = rnd.uniform(12.0, 20.0)
            c0 = pos
            c1 = min(pos + w, 52.0)
            near = 37.0 + OUT_GAP
            if side == "N":
                outer.append((near, near + d, c0, c1, h))
            elif side == "S":
                outer.append((-near - d, -near, c0, c1, h))
            elif side == "E":
                outer.append((c0, c1, near, near + d, h))
            else:
                outer.append((c0, c1, -near - d, -near, h))
            pos = c1 + rnd.uniform(0.3, 1.2)

    for sd in "NSEW":
        band(sd)

    def outer_building(i, x0, x1, y0, y1, h, face):
        pk = ["pl_ochre", "pl_salmon", "pl_cream"][i % 3]
        ibox(pk, x0, x1, y0, y1, -2.0, h)
        lx, ly = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hw = min(lx, ly) / 2
        rise = min(2.4, hw * 0.45)
        ov = 0.4
        ang = math.degrees(math.atan2(rise, hw + ov))
        ln = math.hypot(hw + ov, rise) + 0.1
        mid = (hw + ov) / 2
        zc = h + rise / 2
        if lx >= ly:
            inst("roof_far", cx, cy - mid, zc, lx + 2 * ov, ln, 0.3, rot=(0, 0, ang))
            inst("roof_far", cx, cy + mid, zc, lx + 2 * ov, ln, 0.3, rot=(0, 0, -ang))
        else:
            inst("roof_far", cx - mid, cy, zc, ln, ly + 2 * ov, 0.3, rot=(-ang, 0, 0))
            inst("roof_far", cx + mid, cy, zc, ln, ly + 2 * ov, 0.3, rot=(ang, 0, 0))
        ibox("stone", cx - 0.5, cx + 0.5, cy - 0.5, cy + 0.5, h, h + rise + 1.8)   # 煙突
        # 窓（マップに向いた面に 2 段）。遠景なので鎧戸と枠は省く
        rows = [5.0, 9.5] + ([14.0] if h > 16 else [])
        ln_face = (y1 - y0) if face in ("N", "S") else (x1 - x0)
        nw = max(1, int((ln_face - 1.5) // 3.0))
        for r in rows:
            for k in range(nw):
                t = (y0 if face in ("N", "S") else x0) + 0.75 + (ln_face - 1.5) * (k + 0.5) / nw
                if face == "N":
                    ibox("glass", x0 - 0.05, x0 + 0.02, t - 0.5, t + 0.5, r - 0.8, r + 0.8)
                elif face == "S":
                    ibox("glass", x1 - 0.02, x1 + 0.05, t - 0.5, t + 0.5, r - 0.8, r + 0.8)
                elif face == "E":
                    ibox("glass", t - 0.5, t + 0.5, y0 - 0.05, y0 + 0.02, r - 0.8, r + 0.8)
                else:
                    ibox("glass", t - 0.5, t + 0.5, y1 - 0.02, y1 + 0.05, r - 0.8, r + 0.8)

    # 帯ごとに、マップに向いた面を決める（N の帯は X が小さい側が内側）
    for i, (x0, x1, y0, y1, h) in enumerate(outer):
        cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
        if abs(cxm) > abs(cym):
            face = "N" if cxm > 0 else "S"
        else:
            face = "E" if cym > 0 else "W"
        # 鐘楼の足元は空ける（下で作る）
        if x0 < 49 and x1 > 36 and y0 < 9 and y1 > -3 and cxm > 0:
            continue
        outer_building(i, x0, x1, y0, y1, h, face)

    # 鐘楼：箱を積んだ仮の塔（6 × 6 × 25 m。Meshy で作るまでの代わり）
    BX, BY = 44.0, 3.0
    ibox("pl_cream", BX - 3.0, BX + 3.0, BY - 3.0, BY + 3.0, -2.0, 17.0)
    ibox("stone", BX - 3.2, BX + 3.2, BY - 3.2, BY + 3.2, 17.0, 17.6)
    ibox("pl_cream", BX - 2.4, BX + 2.4, BY - 2.4, BY + 2.4, 17.6, 22.0)
    for sx_, sy_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if sx_:
            ibox("glass", BX + sx_ * 2.4 - (0.0 if sx_ > 0 else 0.05), BX + sx_ * 2.4 + (0.05 if sx_ > 0 else 0.0), BY - 0.9, BY + 0.9, 18.6, 21.0)
        else:
            ibox("glass", BX - 0.9, BX + 0.9, BY + sy_ * 2.4 - (0.0 if sy_ > 0 else 0.05), BY + sy_ * 2.4 + (0.05 if sy_ > 0 else 0.0), 18.6, 21.0)
    ibox("stone", BX - 2.8, BX + 2.8, BY - 2.8, BY + 2.8, 22.0, 22.5)
    ibox("roof_far", BX - 2.3, BX + 2.3, BY - 2.3, BY + 2.3, 22.5, 23.7)
    ibox("roof_far", BX - 1.5, BX + 1.5, BY - 1.5, BY + 1.5, 23.7, 24.9)
    ibox("roof_far", BX - 0.8, BX + 0.8, BY - 0.8, BY + 0.8, 24.9, 26.0)
    ibox("iron", BX - 0.12, BX + 0.12, BY - 0.12, BY + 0.12, 26.0, 28.0)

    # ---------------------------------------------------------------- 6. 街灯（壁掛け。細い柱と傘、弱い暖色の光。影は落とさない）
    LAMP_TARGETS = [(-24, -28), (-10, -22), (5, -18.25), (-18, 3.0), (-8, 8), (-12, 30), (10, 14), (30, 10), (-34, 12)]
    lamp_runs = [r for r in runs if (r[6] is not None) and (r[7] - r[6]) >= 2.0 and not r[5] and not r[4]]
    n_lamp = 0
    for tx, ty in LAMP_TARGETS:
        best = None
        for r in lamp_runs:
            nx, ny, fixed, own, inner, water, a, b = r
            t = ty if nx else tx
            t = min(max(t, a + 0.6), b - 0.6)
            px, py = (fixed, t) if nx else (t, fixed)
            d = math.hypot(px - tx, py - ty)
            if best is None or d < best[0]:
                best = (d, r, t)
        d, r, t = best
        nx, ny, fixed, own, inner, water, a, b = r
        run = r
        # 柱（壁にぴったり 0.1m）、腕と傘
        face_box(run, "iron", t - 0.05, t + 0.05, 0.10, 2.6, 4.0)
        face_box(run, "iron", t - 0.04, t + 0.04, 0.30, 3.9, 3.98)
        face_box(run, "lampglass", t - 0.12, t + 0.12, 0.26, 3.45, 3.85, off=0.04)
        if nx:
            pos = unreal.Vector(cm(fixed + nx * 0.17), cm(t), cm(3.65))
        else:
            pos = unreal.Vector(cm(t), cm(fixed + ny * 0.17), cm(3.65))
        pl = eas.spawn_actor_from_class(unreal.PointLight, pos)
        pl.set_actor_label(f"Art_StreetLamp_{n_lamp}")
        pl.set_folder_path("Art")
        lc = pl.get_component_by_class(unreal.PointLightComponent)
        lc.set_mobility(unreal.ComponentMobility.MOVABLE)
        lc.set_editor_property("light_color", unreal.Color(r=255, g=190, b=120, a=255))
        lc.set_editor_property("intensity", 1500.0)
        lc.set_editor_property("attenuation_radius", 900.0)
        lc.set_editor_property("cast_shadows", False)
        pl.set_editor_property("tags", ART_TAG)
        n_lamp += 1

    # ---------------------------------------------------------------- 7. 遮蔽の作り込み（Step 38b、docs/26 §9）
    # 当たり判定の箱（Cover_*）の位置・大きさ・形は変えない。素材を塗り、表面に当たり判定なしの薄い飾り（出っ張り 3cm 以内）を足す。
    # 例外：井戸の屋根と柱、屋台の天幕、噴水の柱と受け皿は、箱の上（頭より上）に細く足す。
    # Meshy の樽は遮蔽に使わない（隙間が最大 62cm 出たため）。Cover_Barrel は表示に戻し、大きな 1 個の樽として飾る。
    ML = unreal.MathLibrary

    def inst_dir(key, cx, cy, cz, length, wy, wz, d):
        """X 軸を方向 d=(dx, dy, dz) に向けた箱。scale = (length, wy, wz)（wy は水平な横、wz は上下の幅）"""
        rot = ML.find_look_at_rotation(unreal.Vector(0, 0, 0), unreal.Vector(d[0], d[1], d[2]))
        pending[key].append(unreal.Transform(unreal.Vector(cm(cx), cm(cy), cm(cz)), rot, unreal.Vector(length, wy, wz)))

    def inst_cyl(key, cx, cy, z0, z1, dia, dia_y=None):
        inst(key, cx, cy, (z0 + z1) / 2, dia, dia if dia_y is None else dia_y, z1 - z0)

    def inst_disc(key, cx, cy, cz, dia, thick, axis):
        """軸が axis（'x' か 'y'）に向いた円盤"""
        zz = unreal.Vector(1, 0, 0) if axis == "x" else unreal.Vector(0, 1, 0)
        rot = ML.make_rot_from_z(zz)
        pending[key].append(unreal.Transform(unreal.Vector(cm(cx), cm(cy), cm(cz)), rot, unreal.Vector(dia, dia, thick)))

    def faces(cx, cy, sx, sy):
        """側面 4 つ：(nx, ny, 中心から面までの距離, 面の横幅, 横方向の単位ベクトル)"""
        return [(1, 0, sx / 2, sy, (0, 1)), (-1, 0, sx / 2, sy, (0, -1)), (0, 1, sy / 2, sx, (-1, 0)), (0, -1, sy / 2, sx, (1, 0))]

    def fbox(cx, cy, f, key, t0, t1, z0, z1, thick, off=0.0):
        """面の上の箱。t0〜t1 は面の中央からの横位置、z0〜z1 は高さ（絶対）、thick は面から出る厚み"""
        nx, ny, dn, _lt, (tx, ty) = f
        nc = dn + off + thick / 2
        tm = (t0 + t1) / 2
        px, py = cx + nx * nc + tx * tm, cy + ny * nc + ty * tm
        if nx:
            inst(key, px, py, (z0 + z1) / 2, thick, t1 - t0, z1 - z0)
        else:
            inst(key, px, py, (z0 + z1) / 2, t1 - t0, thick, z1 - z0)

    def fdiag(cx, cy, f, key, t0, z0, t1, z1, width, thick, off=0.0):
        """面の上の斜めの板（(t0,z0) から (t1,z1)）"""
        nx, ny, dn, _lt, (tx, ty) = f
        nc = dn + off + thick / 2
        tm, zm = (t0 + t1) / 2, (z0 + z1) / 2
        px, py = cx + nx * nc + tx * tm, cy + ny * nc + ty * tm
        d = (tx * (t1 - t0), ty * (t1 - t0), z1 - z0)
        inst_dir(key, px, py, zm, math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2), thick, width, d)

    def deco_crate(cx, cy, sx, sy, z0, h, big):
        """木箱。大：太い枠、縦の板の継ぎ目、X 字の筋交い。小：細い枠、横の板の継ぎ目、1 本の筋交い。出っ張りは 3cm 以内"""
        fw = 0.14 if big else 0.10
        for fi, f in enumerate(faces(cx, cy, sx, sy)):
            lt = f[3]
            a = lt / 2
            zt = z0 + h
            fbox(cx, cy, f, "door", -a, -a + fw, z0, zt, 0.03)                     # 縁取り（左右）
            fbox(cx, cy, f, "door", a - fw, a, z0, zt, 0.03)
            fbox(cx, cy, f, "door", -a + fw, a - fw, z0, z0 + fw, 0.03)            # 縁取り（下・上）
            fbox(cx, cy, f, "door", -a + fw, a - fw, zt - fw, zt, 0.03)
            if big:
                n = int(lt / 0.4)
                for k in range(1, n):                                                # 縦の継ぎ目（0.4m ごと）
                    t = -a + lt * k / n
                    fbox(cx, cy, f, "iron", t - 0.012, t + 0.012, z0 + fw, zt - fw, 0.012)
                fdiag(cx, cy, f, "door", -a + fw, z0 + fw, a - fw, zt - fw, 0.12, 0.02, off=0.01)    # X 字の筋交い
                fdiag(cx, cy, f, "door", -a + fw, zt - fw, a - fw, z0 + fw, 0.12, 0.02, off=0.01)
            else:
                n = max(2, int(round(h / 0.33)))
                for k in range(1, n):                                                # 横の継ぎ目（板の幅 0.33m）
                    z = z0 + h * k / n
                    fbox(cx, cy, f, "iron", -a + fw, a - fw, z - 0.012, z + 0.012, 0.012)
                if fi % 2 == 0:                                                      # 1 本の筋交い（面ごとに向きを変える）
                    fdiag(cx, cy, f, "door", -a + fw, z0 + fw, a - fw, zt - fw, 0.09, 0.02, off=0.01)
                else:
                    fdiag(cx, cy, f, "door", -a + fw, zt - fw, a - fw, z0 + fw, 0.09, 0.02, off=0.01)
        # 上面：縁取りと板の継ぎ目
        zt = z0 + h
        ibox("door", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy - sy / 2 + fw, zt, zt + 0.03)
        ibox("door", cx - sx / 2, cx + sx / 2, cy + sy / 2 - fw, cy + sy / 2, zt, zt + 0.03)
        ibox("door", cx - sx / 2, cx - sx / 2 + fw, cy - sy / 2 + fw, cy + sy / 2 - fw, zt, zt + 0.03)
        ibox("door", cx + sx / 2 - fw, cx + sx / 2, cy - sy / 2 + fw, cy + sy / 2 - fw, zt, zt + 0.03)
        nb = int((sy - 2 * fw) / 0.4)
        for k in range(1, max(nb, 2)):
            yy = cy - sy / 2 + fw + (sy - 2 * fw) * k / max(nb, 2)
            ibox("iron", cx - sx / 2 + fw, cx + sx / 2 - fw, yy - 0.012, yy + 0.012, zt, zt + 0.012)

    def deco_barrel(cx, cy, dia, z0, h):
        """大きな樽 1 個：鉄の輪 3 本、ふたの縁、板の継ぎ目の縦線、ふたの板の線"""
        r = dia / 2
        for zc in (0.13, 0.50, 0.87):
            inst_cyl("iron_cyl", cx, cy, z0 + zc - 0.045, z0 + zc + 0.045, dia + 0.06)     # 輪（太さ +3cm）
        inst_cyl("door_cyl", cx, cy, z0 + h - 0.01, z0 + h + 0.025, dia + 0.03)              # ふたの縁（上に 2.5cm）
        for k in range(20):                                                                  # 板の継ぎ目（縦線）
            th = 2 * math.pi * (k + 0.5) / 20
            rr = r + 0.008
            inst("door", cx + rr * math.cos(th), cy + rr * math.sin(th), z0 + h / 2, 0.016, 0.05, h - 0.02, rot=(0, math.degrees(th), 0))
        for k in range(-3, 4):                                                               # ふたの板の線
            yy = k * 0.2
            hl = math.sqrt(max(r * r - yy * yy, 0.0)) - 0.03
            ibox("iron", cx - hl, cx + hl, cy + yy - 0.01, cy + yy + 0.01, z0 + h, z0 + h + 0.012)

    def deco_well(cx, cy, dia, z0, h):
        """井戸：石積みの線、縁、暗い穴と水。上に木の枠と小さな屋根（頭より上、細く）"""
        r = dia / 2
        for zc, off in ((0.33, 0.0), (0.66, 0.5)):                                          # 石の段の境（横線）と継ぎ目（縦線、段ごとにずらす）
            inst_cyl("iron_cyl", cx, cy, z0 + zc - 0.013, z0 + zc + 0.013, dia + 0.03)
        for row, (za, zb) in enumerate(((0.0, 0.33), (0.33, 0.66), (0.66, 1.0))):
            n = 12
            for k in range(n):
                th = 2 * math.pi * (k + (0.5 if row % 2 else 0.0)) / n
                inst("iron", cx + (r + 0.006) * math.cos(th), cy + (r + 0.006) * math.sin(th), z0 + (za + zb) / 2, 0.012, 0.025, zb - za - 0.03,
                     rot=(0, math.degrees(th), 0))
        inst_cyl("stone_cyl", cx, cy, z0 + h - 0.12, z0 + h + 0.02, dia + 0.06)             # 縁
        inst_cyl("iron_cyl", cx, cy, z0 + h, z0 + h + 0.025, dia * 0.72)                   # 穴
        inst_cyl("water_cyl", cx, cy, z0 + h, z0 + h + 0.03, dia * 0.56)                    # 水
        # 枠：2 本の柱（縁の上、Y 方向の両端）と梁、巻き上げの軸
        for sgn in (-1, 1):
            ibox("door", cx - 0.06, cx + 0.06, cy + sgn * (r - 0.15) - 0.06, cy + sgn * (r - 0.15) + 0.06, z0 + h + 0.03, z0 + h + 1.6)
        ibox("door", cx - 0.07, cx + 0.07, cy - r + 0.05, cy + r - 0.05, z0 + h + 1.5, z0 + h + 1.62)
        inst_disc("door_cyl", cx, cy, z0 + h + 1.05, 0.16, 2 * (r - 0.15), "y")             # 巻き上げの軸（円柱を横に倒す）
        # 小さな屋根（棟は Y 方向。2 枚の傾いた板）。上端は 頭より上（床から 2.7〜3.3m）
        zr = z0 + h + 1.62
        for sgn in (-1, 1):
            inst_dir("roof_far", cx + sgn * 0.38, cy, zr + 0.2, math.hypot(0.8, 0.45), 1.5, 0.05, (-sgn * 0.8, 0, 0.45))

    def deco_cart(cx, cy, sx, sy, z0, h):
        """荷車：枠と板の線、側面の車輪（円盤、軸は Y）、スポーク、後ろの取っ手。長手は X 方向"""
        for fi, f in enumerate(faces(cx, cy, sx, sy)):
            lt = f[3]
            a = lt / 2
            zt = z0 + h
            fbox(cx, cy, f, "door", -a, -a + 0.12, z0, zt, 0.03)
            fbox(cx, cy, f, "door", a - 0.12, a, z0, zt, 0.03)
            fbox(cx, cy, f, "door", -a + 0.12, a - 0.12, zt - 0.12, zt, 0.03)
            fbox(cx, cy, f, "door", -a + 0.12, a - 0.12, z0 + 1.1, z0 + 1.2, 0.03)            # 荷台の縁
            for k in (0.5, 1.5):
                fbox(cx, cy, f, "iron", -a + 0.12, a - 0.12, z0 + k - 0.012, z0 + k + 0.012, 0.012)
        zt = z0 + h
        for yy in (-0.5, -0.17, 0.17, 0.5):                                                  # 荷台の上面の板（長手）
            ibox("iron", cx - sx / 2 + 0.12, cx + sx / 2 - 0.12, cy + yy * (sy / 1.5) - 0.01, cy + yy * (sy / 1.5) + 0.01, zt, zt + 0.012)
        ibox("door", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy - sy / 2 + 0.1, zt, zt + 0.03)
        ibox("door", cx - sx / 2, cx + sx / 2, cy + sy / 2 - 0.1, cy + sy / 2, zt, zt + 0.03)
        ibox("door", cx - sx / 2, cx - sx / 2 + 0.1, cy - sy / 2 + 0.1, cy + sy / 2 - 0.1, zt, zt + 0.03)
        ibox("door", cx + sx / 2 - 0.1, cx + sx / 2, cy - sy / 2 + 0.1, cy + sy / 2 - 0.1, zt, zt + 0.03)
        for wx in (-sx * 0.3, sx * 0.3):                                                     # 車輪（直径 1.1m、側面の左右）
            for sgn in (-1, 1):
                yc = cy + sgn * (sy / 2 + 0.01)
                wz = z0 + 0.55
                inst_disc("door_cyl", cx + wx, yc, wz, 1.1, 0.02, "y")
                inst_disc("iron_cyl", cx + wx, cy + sgn * (sy / 2 + 0.015), wz, 0.2, 0.03, "y")   # ハブ
                for ang in (0, 45, 90, 135):
                    ar = math.radians(ang)
                    inst_dir("iron", cx + wx, cy + sgn * (sy / 2 + 0.025), wz, 1.05, 0.01, 0.05, (math.cos(ar), 0, math.sin(ar)))
        # 取っ手（-X 側の端の面に沿って）
        fe = faces(cx, cy, sx, sy)[1]
        fbox(cx, cy, fe, "iron", -0.6, 0.6, z0 + 1.55, z0 + 1.63, 0.03)
        fbox(cx, cy, fe, "iron", -0.62, -0.54, z0 + 1.2, z0 + 1.63, 0.03)
        fbox(cx, cy, fe, "iron", 0.54, 0.62, z0 + 1.2, z0 + 1.63, 0.03)

    def deco_stall(cx, cy, sx, sy, z0, h):
        """屋台：台の板の線と縁、天幕（赤とクリームの縞。箱の真上の範囲、高さ 2.03〜2.5m、薄い板）、前の布の垂れ、柱"""
        zt = z0 + h
        for fi, f in enumerate(faces(cx, cy, sx, sy)):
            lt = f[3]
            a = lt / 2
            fbox(cx, cy, f, "door", -a, -a + 0.1, z0, zt, 0.03)
            fbox(cx, cy, f, "door", a - 0.1, a, z0, zt, 0.03)
            fbox(cx, cy, f, "door", -a + 0.1, a - 0.1, z0, z0 + 0.12, 0.03)
            fbox(cx, cy, f, "door", -a + 0.1, a - 0.1, z0 + 0.9, z0 + 1.0, 0.03)             # 台の縁
            for k in (0.3, 0.6, 1.3, 1.6):
                fbox(cx, cy, f, "iron", -a + 0.1, a - 0.1, z0 + k - 0.012, z0 + k + 0.012, 0.012)
        # 布の垂れ（長い面、上端）。赤とクリームの縞
        for fi in (2, 3):
            f = faces(cx, cy, sx, sy)[fi]
            a = f[3] / 2
            n = int(f[3] / 0.5)
            for k in range(n):
                fbox(cx, cy, f, "shutter_r" if k % 2 == 0 else "pl_cream", -a + f[3] * k / n, -a + f[3] * (k + 1) / n, zt - 0.28, zt - 0.06, 0.03, off=0.0)
        # 天幕：長手（X）に沿って傾いた板 3 枚の縞。北側（+X）が高い。箱の上面（2.0m）より上に、箱の真上の範囲だけ
        lo, hi = zt + 0.07, zt + 0.5
        ln = math.hypot(sx - 0.1, hi - lo)
        sw = (sy - 0.1) / 3
        for k in range(3):
            yy = cy - (sy - 0.1) / 2 + sw * (k + 0.5)
            inst_dir("shutter_r" if k % 2 == 0 else "pl_cream", cx, yy, (lo + hi) / 2, ln, sw, 0.03, (sx - 0.1, 0, hi - lo))
        for px_, hz in ((cx + sx / 2 - 0.08, hi), (cx - sx / 2 + 0.08, lo)):                  # 柱（四隅）
            for py_ in (cy - sy / 2 + 0.08, cy + sy / 2 - 0.08):
                ibox("door", px_ - 0.04, px_ + 0.04, py_ - 0.04, py_ + 0.04, zt, hz)

    def deco_fountain(cx, cy, dia, z0, h):
        """噴水：円柱の外側に石の段の線と縦の継ぎ目、縁、水の面。中央の柱と受け皿は上に出る細い部分（直径 0.55m）"""
        r = dia / 2
        inst_cyl("stone_cyl", cx, cy, z0, z0 + 0.2, dia + 0.06)                              # 台座
        inst_cyl("stone_cyl", cx, cy, z0 + h - 0.15, z0 + h + 0.02, dia + 0.06)             # 縁
        for zc in (0.7, 1.3):
            inst_cyl("iron_cyl", cx, cy, z0 + zc - 0.013, z0 + zc + 0.013, dia + 0.03)
        n = 28
        for row, (za, zb) in enumerate(((0.2, 0.7), (0.7, 1.3), (1.3, 1.85))):
            for k in range(n):
                th = 2 * math.pi * (k + (0.5 if row % 2 else 0.0)) / n
                inst("iron", cx + (r + 0.006) * math.cos(th), cy + (r + 0.006) * math.sin(th), z0 + (za + zb) / 2, 0.012, 0.03, zb - za - 0.04,
                     rot=(0, math.degrees(th), 0))
        inst_cyl("water_cyl", cx, cy, z0 + h, z0 + h + 0.03, dia * 0.86)                   # 水の面（縁の内側）
        inst_cyl("stone_cyl", cx, cy, z0 + h, z0 + h + 1.1, 0.55)                          # 中央の柱
        inst_cyl("stone_cyl", cx, cy, z0 + h + 0.55, z0 + h + 0.69, 1.5)                   # 下の受け皿
        inst_cyl("water_cyl", cx, cy, z0 + h + 0.69, z0 + h + 0.705, 1.3)
        inst_cyl("stone_cyl", cx, cy, z0 + h + 1.05, z0 + h + 1.17, 0.8)                   # 上の受け皿
        inst_cyl("stone_cyl", cx, cy, z0 + h + 1.17, z0 + h + 1.55, 0.2)                   # 先端

    def deco_pillar(cx, cy, sx, z0, h):
        """柱（石）：台座、柱頭、帯、縦の溝（出っ張り 3cm）"""
        a = sx / 2 + 0.03
        ibox("stone", cx - a, cx + a, cy - a, cy + a, z0, z0 + 0.35)
        ibox("stone", cx - a, cx + a, cy - a, cy + a, z0 + h - 0.3, z0 + h)
        b = sx / 2 + 0.02
        ibox("stone", cx - b, cx + b, cy - b, cy + b, z0 + h * 0.5 - 0.08, z0 + h * 0.5 + 0.08)
        for f in faces(cx, cy, sx, sx):
            for t in (-0.2, 0.2):
                fbox(cx, cy, f, "iron", t - 0.012, t + 0.012, z0 + 0.4, z0 + h - 0.35, 0.012)

    for a in all_actors:
        lb = a.get_actor_label()
        if not lb.startswith("Cover_"):
            continue
        l = a.get_actor_location()
        sc = a.get_actor_scale3d()
        cx, cy = l.x / 100.0, l.y / 100.0
        h = sc.z
        z0 = l.z / 100.0 - h / 2
        if lb == "Cover_Barrel":
            deco_barrel(cx, cy, sc.x, z0, h)
            a.set_actor_hidden_in_game(False)           # 樽の箱は表示に戻す（Meshy の樽は遮蔽に使わない）
            a.static_mesh_component.set_visibility(True)
        elif lb == "Cover_B_Well":
            deco_well(cx, cy, sc.x, z0, h)
        elif lb == "Cover_B_Cart":
            deco_cart(cx, cy, sc.x, sc.y, z0, h)
        elif lb == "Cover_Stall":
            deco_stall(cx, cy, sc.x, sc.y, z0, h)
        elif lb == "Cover_Fountain":
            deco_fountain(cx, cy, sc.x, z0, h)
        elif "Pillar" in lb:
            deco_pillar(cx, cy, sc.x, z0, h)
        else:                                            # 木箱（大：高さ 2m、小：高さ 1m）
            deco_crate(cx, cy, sc.x, sc.y, z0, h, big=(h > 1.5))

    # ---------------------------------------------------------------- 8. 乗れる樽の飾り（Step 38b、docs/26 §10）
    # 道の角・壁ぎわに、Meshy で作った樽（SM_BarrelSmall：高さ 70cm、直径 約 59cm、原点は底面の中央、簡易コリジョン＝凸形状 1 個で上面は平ら）を
    # 1〜3 個ずつ置く。遮蔽の箱と同じ当たり判定（BlockAll）。ナビメッシュに影響する（静的な障害物。置いたあとにナビメッシュをビルドする）。
    # タグ CanalDeco、フォルダ Art/Deco。作り直しは冒頭で「タグ CanalArt / CanalDeco のアクタを消す」
    DECO_MESH = "/Game/PARORANT/Art/Props/SM_BarrelSmall"
    DECO_MAT = "/Game/PARORANT/Art/Props/MI_Barrel"
    DECO_SITES = [   # (番号, 場所, [(X m, Y m, 向き yaw 度, 縮尺), ...])  docs/26 §10.4。Saved の配置計算（角から壁ぎわに寄せ、制約を確認済み）の結果
        ("D01", "船着き場の南西の隅", [(-35.691, -29.691, 234.3, 0.96), (-35.687, -29.077, 182.7, 0.91), (-35.075, -29.708, 152.8, 0.91)]),
        ("D02", "船着き場の北東の隅", [(-35.660, 29.650, 80.4, 1.07), (-35.637, 28.942, 351.5, 1.03)]),
        ("D03", "路地の 1 つ目の折れ（外側の角）", [(-8.340, -29.670, 104.3, 0.91)]),
        ("D04", "路地の 2 つ目の折れ（外側の角）", [(-11.701, -18.309, 111.1, 0.93)]),
        ("D05", "橋の手前の広場の南東の角", [(-2.350, -7.660, 209.4, 1.06), (-2.371, -6.982, 21.5, 1.03)]),
        ("D06", "鐘楼の下の北西の角", [(8.330, 7.660, 153.9, 0.94), (8.334, 7.018, 286.0, 0.96)]),
        ("D07", "鐘楼の下の北東の角（鐘楼の裏の脇）", [(19.652, 7.652, 206.8, 1.04), (19.622, 6.967, 352.9, 1.01)]),
        ("D08", "A の市場の北西の隅", [(8.311, -14.321, 272.6, 0.92)]),
        ("D09", "広場の裏口の奥の隅", [(29.673, 17.673, 14.1, 0.93), (29.627, 16.968, 112.9, 1.03)]),
        ("D10", "教会前の南東の隅", [(35.635, -7.645, 208.8, 1.04), (35.613, -6.951, 239.1, 0.99)]),
        ("D11", "B の広場の南の壁ぎわ", [(21.867, 14.352, 233.0, 0.91), (22.583, 14.387, 138.9, 1.10)]),
        ("D12", "岸壁の道の南の壁ぎわ", [(-18.698, 24.354, 166.2, 1.03)]),
    ]
    if ea.does_asset_exist(DECO_MESH):
        _dm, _dmat = ea.load_asset(DECO_MESH), ea.load_asset(DECO_MAT)
        n_deco = 0
        for sid, _desc, bl in DECO_SITES:
            for k, (bx, by, yaw, sc) in enumerate(bl):
                a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(cm(bx), cm(by), 0.0), unreal.Rotator(0.0, 0.0, yaw))
                a.set_actor_label("Deco_Barrel_%s_%d" % (sid, k + 1))
                a.set_folder_path("Art/Deco")
                c = a.static_mesh_component
                c.set_mobility(unreal.ComponentMobility.STATIC)
                c.set_static_mesh(_dm)
                a.set_actor_scale3d(unreal.Vector(sc, sc, sc))
                c.set_material(0, _dmat)
                c.set_collision_profile_name("BlockAll")
                a.set_editor_property("tags", [unreal.Name("CanalDeco")])
                n_deco += 1
        print("DECO barrels", n_deco, "sites", len(DECO_SITES))

    # ---------------------------------------------------------------- ISM に流し込む
    total = 0
    for k, lst in pending.items():
        if lst:
            ism[k].add_instances(lst, False)
        total += len(lst)
    print("ART: facade runs", n_run, "windows", n_win, "doors", n_door, "roofs", n_roof, "outer", len(outer),
          "overlays", n_overlay, "lamps", n_lamp, "ISM instances", total, {k: len(v) for k, v in pending.items()})

# --- 光の仕上げ（太陽・環境光・露出・A の灯り・街灯の値。map_light_l_canal.py）
_light = unreal.Paths.project_dir() + "docs/tools/map_light_l_canal.py"
exec(compile(open(_light, encoding="utf-8").read(), _light, "exec"), {"unreal": unreal})
