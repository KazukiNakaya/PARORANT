"""PARORANT L_Pind 作業前後の測定（Step 42a、docs/29_pind_tropical.md §2.5）。

L_Pind を開いて Unreal の Python で実行する。形が変わっていないことを数値で比べるための測定だけをする（レベルは変えない）。
RUN_NAME を先に定義して実行すると、その名前の JSON を Saved/art42/<RUN_NAME>.json へ書く（既定は "before"）。
  測るもの：
  - nav      経路の長さ（m）。攻撃スポーン→A・B（路地経由・ミッド経由・最短）、防衛スポーン→A・B。区間ごとに find_path_to_location_synchronously の合計
  - holdpath 攻撃スポーン・防衛スポーンから、全持ち場・経由点（FlankPoint）への経路の長さ（無い・失敗は null。FlankPoint_P_1 は建物 Bld_AtkW の中にあって失敗する。元からそう）
  - navgrid  1m 格子（-41〜41m）でナビメッシュに投影できる点の数と、その並び（行ごとの 0/1 を 16 進にした文字列の SHA-1）
  - los      遮蔽 14 個の中心を挟む水平の線 4 方向 × 2 高さ（1.6m、0.6m）= 112 本と、持ち場 → 代表点の線。当たったか、当たるまでの距離（cm）、当たったアクタ
  - colliders 当たり判定のあるアクタの位置・大きさ・境界（PindArt のものは除く）と、そのハッシュ
VIEWS は撮影する視点（docs/images/pind42_before_NN.png と pind42_after_NN.png。MCP の control_editor screenshot に位置と向きを渡す）。
比べるには、同じ RUN_NAME="after" で実行して、compare() の結果（差のある項目）を見る。
"""
import json, math, hashlib

try:
    import unreal
except ImportError:
    unreal = None

# 撮影する視点（x m, y m, z m, pitch, yaw）。+X が北、+Y が東。yaw 0 は北向き
VIEWS = [
    ("atkspawn", (-36.0, 0.0, 1.7, 0.0, 0.0)),        # 攻撃スポーンから北へ
    ("alane", (-10.0, -34.0, 1.7, 0.0, 0.0)),         # A 通路を北へ
    ("asite", (14.0, -18.0, 1.7, -4.0, -40.6)),       # A サイトの入口から奥へ
    ("bsite", (14.0, 18.0, 1.7, -4.0, 40.6)),         # B サイトの入口から奥へ
    ("mid", (-8.0, 0.0, 1.7, 0.0, 0.0)),              # ミッドから北へ
    ("defspawn", (36.0, 0.0, 1.7, 0.0, 180.0)),       # 防衛スポーンから南へ
    ("asite_back", (30.0, -34.0, 1.7, -3.0, 180.0)),  # A サイトの奥（北）から南の入口へ
    ("overview", (-62.0, 0.0, 42.0, -32.0, 0.0)),     # 南の外から北へ見渡す（海と外周）
]

ROUTES = {   # 経由点（x, y）。区間ごとにナビメッシュの最短経路を足す
    "atk_A_lane": [(-36, 0), (-20, -34), (9, -34), (23, -27)],
    "atk_B_lane": [(-36, 0), (-20, 34), (9, 34), (23, 27)],
    "atk_A_mid": [(-36, 0), (-20, 0), (0, 0), (9, -16), (23, -27)],
    "atk_B_mid": [(-36, 0), (-20, 0), (0, 0), (9, 16), (23, 27)],
    "atk_A_direct": [(-36, 0), (23, -27)],
    "atk_B_direct": [(-36, 0), (23, 27)],
    "def_A": [(35, 0), (23, -27)],
    "def_B": [(35, 0), (23, 27)],
}
COVER_NAMES = ["CoverA_1", "CoverA_2", "CoverA_3", "CoverA_4", "CoverA_5", "CoverB_1", "CoverB_2", "CoverB_3", "CoverB_4",
               "CoverB_5", "CoverMid_1", "CoverMid_2", "CoverALane", "CoverBLane"]
TARGET_POINTS = [(-36, 0, 1.6), (23, -27, 1.0), (23, 27, 1.0), (0, 0, 1.6), (35, 0, 1.6), (9, -16, 1.6), (9, 16, 1.6), (20, 0, 1.6)]


def _v(x, y, z=0.0):
    return unreal.Vector(x * 100.0, y * 100.0, z * 100.0)


def measure():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world.get_path_name().startswith("/Game/PARORANT/Maps/L_Pind"):
        raise RuntimeError("L_Pind を開いてから実行してください（今のレベル: %s）" % world.get_path_name())
    NS = unreal.NavigationSystemV1
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    acts = list(eas.get_all_level_actors())
    byname = {a.get_actor_label(): a for a in acts}
    res = {}

    def plen(a, b):
        p = NS.find_path_to_location_synchronously(world, a, b)
        if p is None or not p.is_valid():
            return None
        pp = p.path_points
        t = 0.0
        for i in range(len(pp) - 1):
            d = pp[i + 1] - pp[i]
            t += math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
        return t / 100.0

    nav = {}
    for k, pts in ROUTES.items():
        tot, ok = 0.0, True
        for a, b in zip(pts[:-1], pts[1:]):
            d = plen(_v(a[0], a[1], 0.2), _v(b[0], b[1], 0.2))
            if d is None:
                ok = False
            else:
                tot += d
        nav[k] = [round(tot, 3), ok]
    res["nav"] = nav

    hp = {}
    for n, a in sorted(byname.items()):
        if n.startswith(("Hold_", "FlankPoint_")):
            l = a.get_actor_location()
            e = unreal.Vector(l.x, l.y, 20.0)
            row = []
            for s in ((-36, 0), (35, 0)):
                d = plen(_v(s[0], s[1], 0.2), e)
                row.append(None if d is None else round(d, 3))
            hp[n] = row
    res["holdpath"] = hp

    # 1m 格子でナビメッシュ上の点
    rows = []
    cnt = 0
    for ix in range(-41, 41):
        bits = ""
        for iy in range(-41, 41):
            r = NS.project_point_to_navigation(world, _v(ix + 0.5, iy + 0.5, 0.0), None, None, unreal.Vector(20, 20, 60))
            ok = r[0] if isinstance(r, tuple) else (r is not None)
            bits += "1" if ok else "0"
            cnt += 1 if ok else 0
        rows.append(hex(int(bits, 2))[2:])
    res["navgrid"] = {"count": cnt, "sha1": hashlib.sha1("\n".join(rows).encode()).hexdigest()}

    def trace(a, b):
        r = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
                                                   unreal.DrawDebugTrace.NONE, True)
        if isinstance(r, tuple):
            hit, hr = r[0], r[1]
        else:
            hit, hr = (r is not None), r
        if not hit:
            return [False, None, None]
        t = hr.to_tuple()
        act = t[9]
        return [True, round(t[3], 1), act.get_actor_label() if act else None]

    los = {}
    dirs = [(1, 0), (0, 1), (0.7071, 0.7071), (0.7071, -0.7071)]
    for cn in COVER_NAMES:
        c = byname[cn].get_actor_location()
        for di, (dx, dy) in enumerate(dirs):
            for hz in (1.6, 0.6):
                a = unreal.Vector(c.x - dx * 600.0, c.y - dy * 600.0, hz * 100.0)
                b = unreal.Vector(c.x + dx * 600.0, c.y + dy * 600.0, hz * 100.0)
                los["%s_d%d_h%.1f" % (cn, di, hz)] = trace(a, b)
    for n, a in sorted(byname.items()):
        if n.startswith("Hold_"):
            l = a.get_actor_location()
            for ti, tp in enumerate(TARGET_POINTS):
                los["%s_to%d" % (n, ti)] = trace(unreal.Vector(l.x, l.y, 160.0), _v(*tp))
    res["los"] = los

    cols = []
    for a in acts:
        if unreal.Name("PindArt") in a.tags or unreal.Name("PindDeco") in a.tags or a.get_actor_label() == "ArtHost":
            continue   # 角の小物（PindDeco、Step 42b）は別に数える。これを除いた当たり判定は作業前と同じはず
        comps = a.get_components_by_class(unreal.PrimitiveComponent)
        if not any(c.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION for c in comps):
            continue
        l, e = a.get_actor_bounds(True)
        cols.append("%s|%.1f,%.1f,%.1f|%.1f,%.1f,%.1f|%s" % (a.get_actor_label(), l.x, l.y, l.z, e.x, e.y, e.z,
                                                           ",".join(sorted(str(c.get_collision_profile_name()) for c in comps))))
    cols.sort()
    res["colliders"] = {"count": len(cols), "sha1": hashlib.sha1("\n".join(cols).encode()).hexdigest(), "list": cols}
    return res


def compare(a, b):
    """2 つの測定の差（経路の長さは 0.1% 以内、その他は完全一致）を返す。空なら同じ"""
    diff = []
    for k in a["nav"]:
        x, y = a["nav"][k], b["nav"][k]
        if x[1] != y[1] or abs(x[0] - y[0]) > max(0.05, x[0] * 0.001):
            diff.append(("nav", k, x, y))
    for k in a["holdpath"]:
        for i in (0, 1):
            x, y = a["holdpath"][k][i], b["holdpath"][k][i]
            if (x is None) != (y is None) or (x is not None and abs(x - y) > max(0.05, x * 0.001)):
                diff.append(("holdpath", k, i, x, y))
    if a["navgrid"] != b["navgrid"]:
        diff.append(("navgrid", a["navgrid"], b["navgrid"]))
    for k in a["los"]:
        x, y = a["los"][k], b["los"][k]
        if x[0] != y[0] or x[2] != y[2] or (x[1] is not None and abs(x[1] - y[1]) > 2.0):
            diff.append(("los", k, x, y))
    if a["colliders"]["sha1"] != b["colliders"]["sha1"]:
        diff.append(("colliders", a["colliders"]["count"], b["colliders"]["count"]))
    return diff


if unreal is not None:
    _name = globals().get("RUN_NAME", "before")
    _r = measure()
    _dir = unreal.Paths.project_saved_dir() + "art42/"
    json.dump(_r, open(_dir + _name + ".json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("MEASURE", _name, "nav", _r["nav"], "navgrid", _r["navgrid"], "los", len(_r["los"]),
          "hit", sum(1 for v in _r["los"].values() if v[0]), "colliders", _r["colliders"]["count"], _r["colliders"]["sha1"])
    if _name != "before":
        try:
            _b = json.load(open(_dir + "before.json", encoding="utf-8"))
            _d = compare(_b, _r)
            print("COMPARE with before: diffs =", len(_d))
            for x in _d[:20]:
                print("  DIFF", x)
        except Exception as e:
            print("compare skipped", e)
