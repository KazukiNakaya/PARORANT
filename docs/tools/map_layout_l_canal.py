"""PARORANT L_Canal ブロックアウト生成スクリプト（Step 28、docs/22_map_canal.md §3〜5）。

座標は m。+X が北（防衛側）、+Y が東（B 側）、床の上面が Z=0。
L_Pind の map_layout_l_proto.py と同じ方式：
  「歩ける範囲 WALK」を指定し、残り（運河を除く）を高さ 8m の壁の箱として最大長方形に統合して作る。
  床は「歩ける範囲 − 運河」に敷く。

使い方：
  1. Unreal Editor で、L_Pind を複製した L_Canal を開く
  2. このファイルを Editor の Python で実行する（MCP の execute_python の file に指定してよい）
  3. Unreal の外で実行したときは、レイアウトの集計と ASCII プレビューだけを出す

再実行しても同じ結果になる（StaticMeshActor、PointLight と、旧 L_Pind の配置物を毎回消してから作る）。
格子は 0.25m（アーチの幅 3.5m と橋の幅 5m を作るため）。
"""
import math

N = 36          # マップの半径 (m)
S = 4           # 1m あたりのセル数（0.25m 格子）
W = 2 * N * S
WALL_H = 8.0
WALL_Z0 = -2.0  # 運河の底まで壁を下ろす（運河側から見て浮かないように）

# (名前, x0, x1, y0, y1)  docs/22 §3 の表
WALK = [
    ("AtkSpawn",   -36, -26, -30, 30),
    ("Alley1",     -26, -12, -30, -26),
    ("Alley2",     -12,  -8, -30, -18),
    ("Alley3",      -8,   4, -22, -18),
    # AMain はアーチで 3.5m に絞る（表は Y -22〜-18 の 4m。0.25m ずつ内側へ）
    ("AMain",        4,   8, -21.75, -18.25),
    ("ASite",        8,  26, -32, -14),
    ("AShort",      12,  16, -14,  -6),
    ("MidLane",    -26, -18,  -3,   3),
    ("MidPlaza",   -18,  -2,  -8,   8),
    ("Bridge",      -2,   8,  -2.5, 2.5),
    ("BellTower",    8,  20,  -6,   8),
    ("TowerBack",   20,  26,  -2,   4),
    ("BShort",      12,  16,   8,  14),
    ("Quay1",      -26,  -6,  24,  30),
    ("Quay2",       -6,   0,  10,  30),
    ("Lane",        -6,  -2,   8,  10),
    ("StoneBridge",  0,   6,  24,  28),
    ("BSite",        6,  26,  14,  34),
    ("DefSpawn",    26,  36,  -8,  12),
    ("DefA",        28,  32, -20,  -8),
    ("DefADoor",    26,  28, -20, -16),
    ("DefB",        26,  30,  12,  18),
]
CANAL = (0, 6, -6, 36)   # 床も壁も作らない範囲（Bridge と StoneBridge の範囲は橋で渡る）
BRIDGE_MAIN = (-2, 8, -2.5, 2.5)


def ci(v):
    return int(round((v + N) * S))


def rect_cells(x0, x1, y0, y1):
    for ix in range(ci(x0), ci(x1)):
        for iy in range(ci(y0), ci(y1)):
            yield ix, iy


walk = [[False] * W for _ in range(W)]
canal = [[False] * W for _ in range(W)]
bridge_main = [[False] * W for _ in range(W)]
for _, x0, x1, y0, y1 in WALK:
    for ix, iy in rect_cells(x0, x1, y0, y1):
        walk[ix][iy] = True
for ix, iy in rect_cells(*CANAL):
    canal[ix][iy] = True
for ix, iy in rect_cells(*BRIDGE_MAIN):
    bridge_main[ix][iy] = True


def merge(pred):
    """pred(ix, iy) が True のセルを最大長方形に貪欲に統合。(x0, x1, y0, y1) を m で返す。"""
    used = [[False] * W for _ in range(W)]
    out = []
    for ix in range(W):
        for iy in range(W):
            if used[ix][iy] or not pred(ix, iy):
                continue
            h = 0
            while iy + h < W and pred(ix, iy + h) and not used[ix][iy + h]:
                h += 1
            w = 1
            while ix + w < W and all(pred(ix + w, iy + k) and not used[ix + w][iy + k] for k in range(h)):
                w += 1
            for a in range(w):
                for b in range(h):
                    used[ix + a][iy + b] = True
            out.append(((ix) / S - N, (ix + w) / S - N, (iy) / S - N, (iy + h) / S - N))
    return out


wall_rects = merge(lambda ix, iy: not walk[ix][iy] and not canal[ix][iy])
floor_rects = merge(lambda ix, iy: walk[ix][iy] and not canal[ix][iy])


def canal_rail_segments():
    """運河のセル（歩けない）と接する歩けるセルの境界から、手すりの線を作る。
    メイン橋のセルは別に欄干を作るので除く。戻り値は (x0, x1, y0, y1)（手すりの箱の範囲、厚さ 0.25m）。"""
    t = 1.0 / S
    # 方向ごとに (固定座標, 位置の範囲) を集める
    runs = {}
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]  # 歩けるセルが運河セルから見てこの向きにある
    for ix in range(W):
        for iy in range(W):
            if not (canal[ix][iy] and not walk[ix][iy]):
                continue
            for dx, dy in dirs:
                jx, jy = ix + dx, iy + dy
                if not (0 <= jx < W and 0 <= jy < W):
                    continue
                if walk[jx][jy] and not bridge_main[jx][jy]:
                    key = (dx, dy, jx if dx else jy)
                    runs.setdefault(key, []).append(jy if dx else jx)
    segs = []
    for (dx, dy, fixed), lst in runs.items():
        lst.sort()
        start = prev = lst[0]
        for v in lst[1:] + [None]:
            if v is not None and v == prev + 1:
                prev = v
                continue
            a, b = start / S - N, (prev + 1) / S - N
            f = fixed / S - N          # 歩けるセルの下端（座標）
            if dx:   # 歩けるセルは x 方向。手すりはそのセルの運河側の縁の内側
                if dx == 1:
                    segs.append((f, f + t, a, b))
                else:
                    segs.append((f + 1.0 / S - t, f + 1.0 / S, a, b))
            else:
                if dy == 1:
                    segs.append((a, b, f, f + t))
                else:
                    segs.append((a, b, f + 1.0 / S - t, f + 1.0 / S))
            if v is not None:
                start = prev = v
    return segs


rail_segs = canal_rail_segments()

# --- 構造物の寸法（docs/22 §4）---
RAIL_H = 1.0          # 手すり・欄干の高さ
INV_H = 4.0           # 見えない壁の高さ（手すりの上）
BRIDGE_RISE = 1.5
CORRIDOR_Z = 3.0
ROOF_Z = 7.0
HIGHGROUND_Z = 1.0
RAIL_GAP = (-24.0, -22.0)  # 2 階の回廊の手すりの切れ目（飛び降り用。Y の範囲）


# --- Step 29：ゲーム配置（docs/22 §6〜7）---
# 遮蔽：(名前, 形, 中心X, 中心Y, 幅X, 幅Y, 高さ, 下端Z, 素材)  形は "box" か "cyl"（cyl は幅X が直径）
COVERS = [
    ("Cover_A_Entry",   "box",  10, -21,   2.0, 2.0, 2.0, 0.0, "wood"),    # A 入口のすぐ内側
    ("Cover_A_Pillar1", "box",  13, -27,   1.0, 1.0, 7.0, 0.0, "stone"),   # A 中央の柱 4 本（屋根まで）
    ("Cover_A_Pillar2", "box",  13, -19,   1.0, 1.0, 7.0, 0.0, "stone"),
    ("Cover_A_Pillar3", "box",  21, -27,   1.0, 1.0, 7.0, 0.0, "stone"),
    ("Cover_A_Pillar4", "box",  21, -19,   1.0, 1.0, 7.0, 0.0, "stone"),
    ("Cover_A_Back",    "box",  23, -17,   2.0, 1.0, 1.0, 0.0, "wood"),    # A 奥（2 階の回廊の真下）
    ("Cover_B_Well",    "cyl",  14,  22,   2.0, 2.0, 1.0, 0.0, "stone"),   # B の井戸
    ("Cover_B_Cart",    "box",  10,  30,   3.0, 1.5, 2.0, 0.0, "wood"),    # B の荷車
    ("Cover_B_High",    "box",  22,  30,   2.0, 2.0, 1.0, HIGHGROUND_Z, "wood"),  # B の高台の木箱（高台の上）
    ("Cover_B_Shore",   "box", 7.5,  18,   2.0, 2.0, 2.0, 0.0, "wood"),    # B の岸の木箱（運河の手すり X 6〜6.25 を避けて X を 7 → 7.5）
    ("Cover_Fountain",  "cyl", -10,   0,   4.0, 4.0, 2.0, 0.0, "stone"),   # 橋の手前の広場の噴水
    ("Cover_Stall",     "box",  -6,  -5,   3.0, 1.5, 2.0, 0.0, "wood"),    # 屋台
    ("Cover_Barrel",    "cyl", -10, -26,   1.5, 1.5, 1.0, 0.0, "wood"),    # 路地の樽
    ("Cover_Quay",      "box", -14,  28,   2.0, 2.0, 2.0, 0.0, "wood"),    # 岸壁の道の木箱
    ("Cover_Tower",     "box",  14,   2,   2.0, 2.0, 1.0, 0.0, "wood"),    # 鐘楼の下の木箱
]

# 設置エリア：(名前, サイト名, 中心X, 中心Y, 一辺 m)
ZONES = [("PlantZone_A", "A", 17, -23, 8.0), ("PlantZone_B", "B", 15, 24, 9.0)]

# 購入バリア：(名前, X, Y, 幅 cm)（攻撃スポーンの 3 つの出口）
BARRIERS = [("Barrier_Alley", -26, -28, 400.0), ("Barrier_Mid", -26, 0, 600.0), ("Barrier_Quay", -26, 27, 600.0)]

# 持ち場：(名前, Area, bForward, X, Y, 床の高さ m, 見張る目標 X, 目標 Y)。向き（yaw）は位置から目標への方向で決める。
HOLDS = [
    ("Hold_A1",     "A",   False, 24.5, -24, 3.0,  8, -21),   # 2 階の回廊
    ("Hold_A2",     "A",   False, 20,   -29, 0.0,  8, -21),   # 奥の角（仕様 (20,-30) はスロープの手すりの上なので Y を -29 へ）
    ("Hold_A3",     "A",   False, 13,   -16, 0.0,  8, -20),   # 回廊口の脇
    ("Hold_A4",     "A",   False, 22,   -18, 0.0,  8, -20),   # 裏口の前
    ("Hold_A5",     "A",   False, 10,   -30, 0.0, 11, -21),   # 入口の死角（近距離）
    ("Hold_B1",     "B",   False, 24,    31, 1.0,  3,  26),   # 高台（仕様 (23,31) は木箱の角なので X を 24 へ）
    ("Hold_B2",     "B",   False, 15,    20, 0.0, -3,  22),   # 井戸の裏（対岸を見る）
    ("Hold_B3",     "B",   False,  9,    16, 0.0,  6,  26),   # 岸の木箱の裏（石橋から入る所）
    ("Hold_B4",     "B",   False, 24,    16, 0.0, 12,  14),   # 裏口の前
    ("Hold_B5",     "B",   False, 14,    12, 0.0,  9,  20),   # アーチの中
    ("Hold_Mid1",   "Mid", False, 16,     2, 0.0,  8,   0),   # 木箱の裏（仕様 (14,1) は木箱の縁なので (16,2) へ）
    ("Hold_Mid2",   "Mid", False, 18,    -4, 0.0,  6,   0),   # 橋と回廊
    ("Hold_Mid3",   "Mid", False, 22,     1, 0.0, 12,   1),   # 鐘楼の裏
    ("Hold_AFwd",   "A",   True,  -6,   -20, 0.0, -10, -21),  # 路地の 2 つ目の角
    ("Hold_BFwd",   "B",   True,   8,    26, 0.0,  3,  26),   # 石橋の北詰
    ("Hold_MidFwd", "Mid", True, -10,     3, 0.0, -24,  0),   # 噴水の裏
]

# 裏取りの経由点：(名前, Side, Order, X, Y)。Side 1 = A の背後へ（Y が負の側）、-1 = B の背後へ。Z は 20cm（L_Pind と同じ）
FLANKS = [
    ("FlankPoint_A_0",  1, 0,   8,   0), ("FlankPoint_A_1",  1, 1, -14,  -4),
    ("FlankPoint_A_2",  1, 2, -28, -28), ("FlankPoint_A_3",  1, 3, -10, -20),
    ("FlankPoint_B_0", -1, 0,   8,   0), ("FlankPoint_B_1", -1, 1, -14,   4),
    ("FlankPoint_B_2", -1, 2, -28,  27), ("FlankPoint_B_3", -1, 3,  -3,  26),
]

# 場所の名前（BP_AreaName）。§3 の WALK の 1 行につき 1 個。(WALK の名前, 表示名, Area, PredictSite)
AREA_Z = (-0.5, 9.0)   # 箱の高さ範囲 m（2 階の回廊や高台に立ったときも入るように、L_Pind の -50〜300cm より高くした）
AREAS = [
    ("AtkSpawn",    "船着き場",       "None", 0), ("Alley1",   "路地",         "A",   1),
    ("Alley2",      "路地の角",       "A",    1), ("Alley3",   "路地",         "A",   1),
    ("AMain",       "市場の入口",     "A",    1), ("ASite",    "市場",         "A",   0),
    ("AShort",      "回廊",           "A",    0), ("MidLane",  "橋への道",     "Mid", 0),
    ("MidPlaza",    "橋の手前の広場", "Mid",  0), ("Bridge",   "橋",           "Mid", 0),
    ("BellTower",   "鐘楼の下",       "Mid",  0), ("TowerBack", "鐘楼の裏",     "Mid", 0),
    ("BShort",      "アーチ",         "B",    0), ("Quay1",    "岸壁の道",     "B",   2),
    ("Quay2",       "岸壁",           "B",    0), ("Lane",     "小路",         "Mid", 0),
    ("StoneBridge", "石橋",           "B",    2), ("BSite",    "Bの広場",      "B",   0),
    ("DefSpawn",    "教会前",         "None", 0), ("DefA",     "教会の脇道",   "A",   0),
    ("DefADoor",    "市場の裏口",     "A",    0), ("DefB",     "広場の裏口",   "B",   0),
]


def check_points():
    """持ち場と経由点が、歩ける範囲の中にあり、遮蔽・手すりから 0.45m 以上離れているかを調べる（半径 0.35m のカプセルを想定）。"""
    r = 0.45
    boxes = []   # (x0, x1, y0, y1)
    for _, shape, cx, cy, sx, sy, h, z0, _m in COVERS:
        boxes.append((cx - sx / 2 - r, cx + sx / 2 + r, cy - sy / 2 - r, cy + sy / 2 + r, shape, cx, cy, sx / 2 + r))
    for x0, x1, y0, y1 in rail_segs:
        boxes.append((x0 - r, x1 + r, y0 - r, y1 + r, "box", 0, 0, 0))
    # スロープの手すり（A_SlopeRail）と回廊の手すりも避ける
    boxes.append((11 - r, 23 + r, -30.25 - r, -30.0 + r, "box", 0, 0, 0))
    bad = []
    pts = [(n, x, y) for n, _a, _f, x, y, _z, _tx, _ty in HOLDS] + [(n, x, y) for n, _s, _o, x, y in FLANKS]
    for n, x, y in pts:
        if not walk[ci(x)][ci(y)] or canal[ci(x)][ci(y)] and not bridge_main[ci(x)][ci(y)]:
            bad.append((n, "歩ける範囲の外"))
            continue
        for x0, x1, y0, y1, shape, cx, cy, rr in boxes:
            if shape == "cyl":
                if math.hypot(x - cx, y - cy) < rr:
                    bad.append((n, "遮蔽に近すぎる"))
            elif x0 < x < x1 and y0 < y < y1:
                bad.append((n, "遮蔽・手すりに近すぎる"))
    return bad


def summary():
    print("walls", len(wall_rects), "floors", len(floor_rects), "canal rails", len(rail_segs))
    print("point check:", check_points() or "OK")
    for x in range(N - 1, -N - 1, -1):
        row = ""
        for y in range(-N, N):
            ix, iy = (x + N) * S + 1, (y + N) * S + 1
            row += "~" if canal[ix][iy] and not walk[ix][iy] else ("=" if canal[ix][iy] else ("." if walk[ix][iy] else "#"))
        if x % 2 == 0:
            print(f"{x:4d} {row}")


try:
    import unreal
except ImportError:
    unreal = None

ART_ONLY = globals().get("ART_ONLY", False)   # True を先に定義して実行すると、ブロックアウトは作らず見た目（map_art_l_canal.py）だけを作り直す

if unreal is None:
    summary()
elif not ART_ONLY:
    # ------------------------------------------------------------------ Unreal 側
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    ea = unreal.EditorAssetLibrary
    MAT_DIR = "/Game/PARORANT/Materials"
    # 守り：L_Canal 以外（L_Pind など）で実行すると、配置物を全部消してしまうので止める
    _world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
    if not _world.startswith("/Game/PARORANT/Maps/L_Canal"):
        raise RuntimeError("L_Canal を開いてから実行してください（今のレベル: %s）" % _world)

    def get_mi(name, color, parent="/Game/PARORANT/Materials/M_NatureFlat"):
        path = f"{MAT_DIR}/{name}"
        if ea.does_asset_exist(path):
            return ea.load_asset(path)
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mi = tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", ea.load_asset(parent))
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(*color, 1.0))
        unreal.MaterialEditingLibrary.update_material_instance(mi)
        ea.save_loaded_asset(mi)
        return mi

    M_WALL = ea.load_asset(f"{MAT_DIR}/MI_Nature_Wall")
    M_FLOOR = ea.load_asset(f"{MAT_DIR}/MI_Nature_Floor")
    M_RING = ea.load_asset(f"{MAT_DIR}/MI_Nature_Ring")
    M_STONE = get_mi("MI_Canal_Stone", (0.30, 0.29, 0.28))
    M_WATER = get_mi("MI_Canal_Water", (0.02, 0.16, 0.26))
    M_ROOF = get_mi("MI_Canal_Roof", (0.22, 0.07, 0.04))
    CUBE = ea.load_asset("/Engine/BasicShapes/Cube")
    PLANE = ea.load_asset("/Engine/BasicShapes/Plane")
    RAMP = ea.load_asset("/Game/LevelPrototyping/Meshes/SM_Ramp")  # 原点は角、-Y 側が高い（Y 方向に下る）

    # ---- 既存の配置物を消す（L_Pind を複製した L_Canal の中だけ）----
    DEL_BP = ("BP_AreaName_C", "BP_FlankPoint_C", "BP_HoldPoint_C", "BP_PlantZone_C", "BP_SpawnBarrier_C", "BP_Drawbridge_C")
    for a in eas.get_all_level_actors():
        cn = a.get_class().get_name()
        if cn in ("StaticMeshActor", "PointLight") or cn in DEL_BP:
            a.destroy_actor()   # 見た目の部品（タグ CanalArt）もここで消え、最後に map_art_l_canal.py が作り直す。ArtHost（plain Actor）は残る

    TAG = [unreal.Name("mcp.placement.ok")]

    def cm(v):
        return v * 100.0

    def spawn_mesh(label, mesh, cx, cy, cz, sx, sy, sz, mat, folder, rot=(0, 0, 0), collision="block", hidden_game=False):
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(cm(cx), cm(cy), cm(cz)), unreal.Rotator(rot[2], rot[0], rot[1]))
        a.set_actor_label(label)
        a.set_folder_path(folder)
        c = a.static_mesh_component
        c.set_mobility(unreal.ComponentMobility.STATIC)
        c.set_static_mesh(mesh)
        a.set_actor_scale3d(unreal.Vector(sx, sy, sz))
        if mat:
            c.set_material(0, mat)
        if collision == "none":
            c.set_collision_profile_name("NoCollision")
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            c.set_cast_shadow(False)
        elif collision == "pawn":     # Pawn だけ止める見えない壁（弾・視線・ナビには影響しない）
            c.set_collision_profile_name("Custom")  # 先に Custom にしないと、応答の変更が BlockAll に戻される
            c.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            c.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
            c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN, unreal.CollisionResponseType.ECR_BLOCK)
            c.set_cast_shadow(False)
        if collision in ("none", "pawn", "nonav"):
            c.set_editor_property("can_ever_affect_navigation", False)
        if hidden_game:
            a.set_actor_hidden_in_game(True)
            c.set_visibility(False)  # エディタでも描かない（衝突は残る）
        a.set_editor_property("tags", TAG)
        return a

    def box(label, x0, x1, y0, y1, z0, z1, mat, folder, **kw):
        return spawn_mesh(label, CUBE, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, x1 - x0, y1 - y0, z1 - z0, mat, folder, **kw)

    def ramp(label, x0, x1, y0, y1, z0, z1, high, mat, folder):
        """SM_Ramp（-Y 側が高い、原点は角）。high は高い側の向き '+x' '-x' '+y' '-y'。"""
        yaw = {"-y": 0, "+x": 90, "+y": 180, "-x": 270}[high]
        piv = {0: (x0, y0), 90: (x1, y0), 180: (x1, y1), 270: (x0, y1)}[yaw]
        lx, ly = ((x1 - x0), (y1 - y0)) if yaw in (0, 180) else ((y1 - y0), (x1 - x0))
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(cm(piv[0]), cm(piv[1]), cm(z0)), unreal.Rotator(0, 0, yaw))
        a.set_actor_label(label)
        a.set_folder_path(folder)
        c = a.static_mesh_component
        c.set_mobility(unreal.ComponentMobility.STATIC)
        c.set_static_mesh(RAMP)
        a.set_actor_scale3d(unreal.Vector(lx, ly, z1 - z0))
        c.set_material(0, mat)
        a.set_editor_property("tags", TAG)
        return a

    # ---- 壁・床・外周 ----
    for i, (x0, x1, y0, y1) in enumerate(wall_rects):
        box(f"Wall_{i:02d}", x0, x1, y0, y1, WALL_Z0, WALL_H, M_WALL, "Map/Walls")
    for i, (x0, x1, y0, y1) in enumerate(floor_rects):
        box(f"Floor_{i:02d}", x0, x1, y0, y1, -1.0, 0.0, M_FLOOR, "Map/Floor")
    for n, (cx, cy), (sx, sy) in [("Wall_N", (N + 0.5, 0), (1, 2 * N + 2)), ("Wall_S", (-N - 0.5, 0), (1, 2 * N + 2)),
                                  ("Wall_E", (0, N + 0.5), (2 * N, 1)), ("Wall_W", (0, -N - 0.5), (2 * N, 1))]:
        box(n, cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, WALL_Z0, WALL_H, M_RING, "Map/Walls")

    # ---- 運河：水面、底、手すり、見えない壁 ----
    cx0, cx1, cy0, cy1 = CANAL
    spawn_mesh("CanalWater", PLANE, (cx0 + cx1) / 2, (cy0 + cy1) / 2, -0.8, cx1 - cx0, cy1 - cy0, 1, M_WATER, "Map/Canal", collision="none")
    box("CanalBottom", cx0, cx1, cy0, cy1, -2.5, -2.0, M_STONE, "Map/Canal", collision="nonav")
    for i, (x0, x1, y0, y1) in enumerate(rail_segs):
        box(f"CanalRail_{i:02d}", x0, x1, y0, y1, 0.0, RAIL_H, M_STONE, "Map/Canal")
        box(f"CanalBarrier_{i:02d}", x0, x1, y0, y1, RAIL_H, RAIL_H + INV_H, None, "Map/Canal", collision="pawn", hidden_game=True)

    # ---- 橋（Step 35：跳ね橋）：岸側の固定部分。運河の上（X 0〜6）は BP_Drawbridge の跳ね橋板（下りているとき X -2〜8 が従来と同じ形になる）----
    # 従来（Step 28、固定の橋）：Bridge_Up X -2〜2、Bridge_Top X 2〜4（Z 0〜1.5）、Bridge_Down X 4〜8、欄干 BridgeRail_Up/Top/Down_E/W。docs/22 §9.4 に記録
    half = BRIDGE_RISE / 2          # 運河の岸（X=0 と 6）での橋の高さ 0.75m
    ramp("Bridge_LandS", -2, 0, -2.5, 2.5, 0, half, "+x", M_STONE, "Map/Bridge")
    ramp("Bridge_LandN", 6, 8, -2.5, 2.5, 0, half, "-x", M_STONE, "Map/Bridge")
    th = math.degrees(math.atan2(half, 2.0))
    ln = math.hypot(2.0, half)
    for sgn, nm in ((1, "E"), (-1, "W")):
        yc = sgn * (2.5 - 0.125)
        spawn_mesh(f"BridgeRail_LandS_{nm}", CUBE, -1.0, yc, half / 2 + RAIL_H / 2, ln, 0.25, RAIL_H, M_STONE, "Map/Bridge", rot=(th, 0, 0))
        spawn_mesh(f"BridgeRail_LandN_{nm}", CUBE, 7.0, yc, half / 2 + RAIL_H / 2, ln, 0.25, RAIL_H, M_STONE, "Map/Bridge", rot=(-th, 0, 0))
        box(f"BridgeBarrier_{nm}", -2, 8, yc - 0.125, yc + 0.125, RAIL_H, RAIL_H + INV_H + 1.0, None, "Map/Bridge", collision="pawn", hidden_game=True)
    # 石橋（平ら）
    box("StoneBridge_Deck", 0, 6, 24, 28, -0.5, 0.0, M_STONE, "Map/Bridge")

    # ---- A サイト：屋根、2 階の回廊、スロープ、手すり ----
    box("A_Roof", 8, 26, -32, -14, ROOF_Z, ROOF_Z + 0.5, M_ROOF, "Map/ASite")
    box("A_Corridor", 23, 26, -32, -14, CORRIDOR_Z - 0.5, CORRIDOR_Z, M_STONE, "Map/ASite")
    ramp("A_Slope", 11, 23, -32, -30, 0, CORRIDOR_Z, "+x", M_STONE, "Map/ASite")
    box("A_CorridorRail_1", 22.75, 23, -30, RAIL_GAP[0], CORRIDOR_Z, CORRIDOR_Z + RAIL_H, M_STONE, "Map/ASite")
    box("A_CorridorRail_2", 22.75, 23, RAIL_GAP[1], -14, CORRIDOR_Z, CORRIDOR_Z + RAIL_H, M_STONE, "Map/ASite")
    sth = math.degrees(math.atan2(CORRIDOR_Z, 12.0))
    spawn_mesh("A_SlopeRail", CUBE, 17.0, -30.125, CORRIDOR_Z / 2 + RAIL_H / 2, math.hypot(12.0, CORRIDOR_Z), 0.25, RAIL_H, M_STONE, "Map/ASite", rot=(sth, 0, 0))

    # ---- B の高台（Z=1）と段 ----
    box("B_HighGround", 20, 26, 28, 34, 0, HIGHGROUND_Z, M_STONE, "Map/BSite")
    ramp("B_StepWest", 20, 26, 26, 28, 0, HIGHGROUND_Z, "+y", M_STONE, "Map/BSite")
    ramp("B_StepSouth", 18, 20, 28, 34, 0, HIGHGROUND_Z, "+x", M_STONE, "Map/BSite")

    # ---- A の屋内の灯り（暖色 PointLight 4 個）----
    for i, (lx, ly) in enumerate([(12, -27), (12, -19), (22, -27), (22, -19)]):
        pl = eas.spawn_actor_from_class(unreal.PointLight, unreal.Vector(cm(lx), cm(ly), cm(5.5)))
        pl.set_actor_label(f"A_Lamp_{i}")
        pl.set_folder_path("Lighting")
        lc = pl.get_component_by_class(unreal.PointLightComponent)
        lc.set_mobility(unreal.ComponentMobility.MOVABLE)
        lc.set_editor_property("light_color", unreal.Color(r=255, g=176, b=104, a=255))   # Color の引数順は (b, g, r, a)。位置引数だと青くなる
        lc.set_editor_property("intensity", 8000.0)
        lc.set_editor_property("attenuation_radius", 1800.0)
        pl.set_editor_property("tags", TAG)

    # ================= Step 29：ゲーム配置 =================
    M_WOOD = get_mi("MI_Canal_Wood", (0.36, 0.22, 0.11))
    CYL = ea.load_asset("/Engine/BasicShapes/Cylinder")
    for nm, shape, cx, cy, sx, sy, h, z0, mat in COVERS:
        m = M_WOOD if mat == "wood" else M_STONE
        # 遮蔽の見た目は map_art_l_canal.py §7 が飾りを足す（Meshy は遮蔽に使わない。樽の箱も表示のまま。docs/26 §9）
        spawn_mesh(nm, CYL if shape == "cyl" else CUBE, cx, cy, z0 + h / 2, sx, sy, h, m, "Map/Cover")

    def bp_class(name):
        return ea.load_blueprint_class("/Game/PARORANT/Blueprints/World/" + name)

    def spawn_bp(cls, label, x, y, z, yaw, folder):
        a = eas.spawn_actor_from_class(cls, unreal.Vector(cm(x), cm(y), z), unreal.Rotator(0, 0, yaw))
        a.set_actor_label(label)
        a.set_folder_path(folder)
        a.set_editor_property("tags", TAG)
        return a

    # 設置エリア（箱の大きさは Zone の Extent、床の印は FloorMark の拡大で一辺を合わせる）
    for nm, site, x, y, side in ZONES:
        a = spawn_bp(bp_class("BP_PlantZone"), nm, x, y, 0.0, 0.0, "Gameplay/PlantZones")
        a.set_editor_property("SiteName", unreal.Name(site))
        a.get_editor_property("Zone").set_editor_property("box_extent", unreal.Vector(side * 50, side * 50, 150))
        fm = a.get_editor_property("FloorMark")
        fm.set_editor_property("relative_scale3d", unreal.Vector(side, side, 0.02))
        # Step 38：枠（M_PR_ZoneFrame）と床に描いた文字（SiteLabel は BP の既定で床に寝かせてある）。以前の「A の文字を屋根の上へ」は廃止
        a.get_editor_property("SiteLabel").set_editor_property("text", unreal.Text(site))

    # 購入バリア（初期は無効。購入フェーズ中だけ GameMode が有効にする）
    for nm, x, y, width in BARRIERS:
        a = spawn_bp(bp_class("BP_SpawnBarrier"), nm, x, y, 0.0, 0.0, "Gameplay/Barriers")
        a.set_editor_property("Width", width)
        a.set_editor_property("bStartActive", False)

    # 持ち場
    for nm, area, fwd, x, y, fz, tx, ty in HOLDS:
        yaw = math.degrees(math.atan2(ty - y, tx - x))
        a = spawn_bp(bp_class("BP_HoldPoint"), nm, x, y, cm(fz), yaw, "Gameplay/HoldPoints")
        a.set_editor_property("Area", unreal.Name(area))
        a.set_editor_property("bForward", fwd)
        a.get_editor_property("Label").set_editor_property("text", unreal.Text(area + (" FWD" if fwd else "")))

    # 裏取りの経由点
    for nm, side, order, x, y in FLANKS:
        a = spawn_bp(bp_class("BP_FlankPoint"), nm, x, y, 20.0, 0.0, "Gameplay/FlankPoints")
        a.set_editor_property("Side", float(side))
        a.set_editor_property("Order", order)

    # 跳ね橋（Step 35。原点に置く。橋板・見えない壁・ナビの切り替えは BP の中。docs/22 §9）
    spawn_bp(bp_class("BP_Drawbridge"), "Drawbridge", 0.0, 0.0, 0.0, 0.0, "Map/Bridge")

    # 場所の名前（箱は WALK の範囲そのまま。高さは AREA_Z）
    rects = {w[0]: w[1:] for w in WALK}
    for key, disp, area, ps in AREAS:
        x0, x1, y0, y1 = rects[key]
        z0, z1 = AREA_Z
        a = spawn_bp(bp_class("BP_AreaName"), "Area_" + key, (x0 + x1) / 2, (y0 + y1) / 2, cm((z0 + z1) / 2), 0.0, "Gameplay/Areas")
        a.set_actor_scale3d(unreal.Vector((x1 - x0), (y1 - y0), (z1 - z0)))   # 箱の Extent は 50（= 1m 立方）。拡大で大きさを決める（L_Pind と同じ）
        a.set_editor_property("DisplayName", unreal.Text(disp))
        a.set_editor_property("Area", unreal.Name(area))
        a.set_editor_property("PredictSite", ps)

    print("point check:", check_points() or "OK")

    # ---- 既存のアクタの調整（光は L_Pind から複製したものをそのまま使う）----
    for a in eas.get_all_level_actors():
        cn = a.get_class().get_name()
        if cn == "PlayerStart":
            a.set_actor_location(unreal.Vector(cm(-32), 0, 100), False, False)
            a.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
        elif cn == "NavMeshBoundsVolume":
            # 元の箱は半径 4100×4100×300（スケール 1）。X・Y は ±37m、Z は -3〜+10m
            a.set_actor_location(unreal.Vector(0, 0, cm(3.5)), False, False)
            a.set_actor_scale3d(unreal.Vector(3700.0 / 4100.0, 3700.0 / 4100.0, 650.0 / 300.0))
        elif cn == "RecastNavMesh":
            a.set_editor_property("runtime_generation", unreal.RuntimeGenerationType.DYNAMIC_MODIFIERS_ONLY)
        elif cn == "BP_PR_MapInfo_C":
            a.set_editor_property("MapName", "CANAL")  # 表示名（2026-11-12 に決定）。ここ 1 か所を変えれば画面の表示が変わる
            a.set_editor_property("MinimapMin", unreal.Vector2D(-3600, -3600))
            a.set_editor_property("MinimapMax", unreal.Vector2D(3600, 3600))
            a.set_editor_property("IntroCamLoc", unreal.Vector(0, 0, 6840))
            a.set_editor_property("IntroCamRot", unreal.Rotator(0, -90, 0))   # (roll, pitch, yaw) = 真下向き、上が +X（L_Pind と同じ）
            a.set_editor_property("FlankFallback", False)
            # Step 29：サイトの寄り先、ミニマップの A / B の文字、前に出るときの寄り先（docs/22 §7.3）
            a.set_editor_property("SiteDestA", unreal.Vector(1700, -2300, 0))
            a.set_editor_property("SiteDestB", unreal.Vector(1500, 2400, 0))
            a.set_editor_property("MinimapLabelA", unreal.Vector2D(1700, -2300))
            a.set_editor_property("MinimapLabelB", unreal.Vector2D(1500, 2400))
            a.set_editor_property("ForwardDestA", unreal.Vector(-1000, -2000, 0))   # 路地の 2 つ目の角
            a.set_editor_property("ForwardDestB", unreal.Vector(-300, 2600, 0))     # 岸壁の B 側（石橋の手前）
            if ea.does_asset_exist("/Game/PARORANT/UI/T_PR_Minimap_Canal"):
                a.set_editor_property("MinimapTex", ea.load_asset("/Game/PARORANT/UI/T_PR_Minimap_Canal"))
    print("built: walls", len(wall_rects), "floors", len(floor_rects), "rails", len(rail_segs))

# --- Step 38：見た目（腰壁、窓、屋根、場外の建物、街灯、素材の塗り分け）。ArtHost と ISM_<key> は map_art_l_canal.py の説明を参照
if unreal is not None:
    _art = unreal.Paths.project_dir() + "docs/tools/map_art_l_canal.py"
    exec(compile(open(_art, encoding="utf-8").read(), _art, "exec"), globals())
