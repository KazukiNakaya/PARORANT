"""Meshy の小物 9 個を、Unreal に取り込める FBX に整える Blender 用スクリプト（Step 42、樽の blender_barrel_small.py と同じ流儀）。

実行（画面なし。空のシーンから始まるのでユーザーのシーンには触れない）：
  blender.exe --background --factory-startup --python blender_props_42b.py -- [名前 ...]
名前を省くと 9 個すべて。何度実行しても同じ結果（乱数は固定、毎回読み込み直す）。

モデルごとにやること：
  1. glb を読み込み（glTF の取り込みで Z が上になる）、部品を 1 つに結合、回転・拡縮・位置を適用
  2. 重なった頂点を結合（0.2mm 相当）、法線を外向きにそろえる、本体の外接箱から離れて浮いた小さな島（面の 2% 未満）を消す
  3. 目標の大きさに一様拡縮、原点を底面の中央（X・Y は外接箱の中心。ヤシは幹の根元＝最下部の薄い層の中心）、Z は最下点
  4. Shade Smooth by Angle 35°。三角形が多すぎれば Decimate
  5. 「あり」のものは簡易コリジョン＝凸形状 1 個（面数 32 以下）。見た目との差を測る
  6. FBX（見た目＋コリジョン UCX_<メッシュ名>_00）と確認画像（_view.png、_col.png）を書き出す
  7. 数値を download/meshy/props_42b_report.json に書く
FBX の単位は樽と同じ設定（apply_unit_scale=False、FBX_SCALE_NONE）。Blender の 1 = 1m、Unreal の取り込みで cm になる。
"""
import bpy
import bmesh
import math
import json
import random
import sys
import os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = "C:/Users/kazuk/Documents/Repository/UnrealEngine/PARORANT/download/meshy/"
REPORT = ROOT + "props_42b_report.json"
SMOOTH_ANGLE = 35.0   # 度
ISLAND_FRAC = 0.02    # これ未満の面の島は「浮いた破片」として消す
COL_MAX_TRIS = int(os.environ.get("PROPS_COLTRIS", "32"))   # 植木鉢は 120（42c 続き。32 だと底が円錐になり 25cm ずれた）。実行: PROPS_COLTRIS=120 blender ... -- pot_plant
# 凸形状 1 個の三角形の上限（42c で小物ごとに変えて試す）
# 三角形の上限（これを超えたら Decimate）
TRI_BUDGET = {"deco": 5000, "corner": 3000}

# 入力と目標の表。axis: "z" 高さで合わせる／"max" いちばん長い軸で合わせる。target は cm。
# kind: deco 場外の飾り／corner 角の小物。col: 簡易コリジョンを作るか。root: "bbox" 外接箱の中心／"bottom" 最下部の層の中心
# pot_frac: pot_plant 専用。元の高さに対する鉢の上端の割合（None なら分けずに全高で合わせる）
COLMODE = json.loads(os.environ.get("PROPS_COLMODE", "{}"))   # 試すときだけ環境変数 PROPS_COLMODE（例 {"sacks": "islands:4"}）で上書き
MODELS = [
    dict(src="palm_tall",   out="SM_PalmTall",       target=900, axis="z",   kind="deco",   col=False, root="bottom"),
    dict(src="palm_bent",   out="SM_PalmBent",       target=550, axis="z",   kind="deco",   col=False, root="bottom"),
    dict(src="bush",        out="SM_TropicBush",     target=110, axis="z",   kind="deco",   col=False, root="bbox"),
    dict(src="boat",        out="SM_Rowboat",        target=380, axis="max", kind="deco",   col=False, root="bbox"),
    dict(src="parasol",     out="SM_ParasolClosed",  target=240, axis="z",   kind="deco",   col=False, root="bottom"),
    dict(src="crate_small", out="SM_CrateSmall",     target=60,  axis="z",   kind="corner", col=True,  root="bbox", col_mode="single"),
    dict(src="sacks",       out="SM_SackPile",       target=55,  axis="z",   kind="corner", col=True,  root="bbox", col_mode=COLMODE.get("sacks", "islands:4")),
    dict(src="pot_plant",   out="SM_PotPlant",       target=55,  axis="pot", kind="corner", col=True,  root="bbox", pot_frac="island", fallback=100, col_mode=COLMODE.get("pot_plant", "potisland")),
    dict(src="amphora",     out="SM_Amphora",        target=75,  axis="z",   kind="corner", col=True,  root="bbox", col_mode=COLMODE.get("amphora", "zsplit:3")),
]


def set_active(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def tris_of(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def world_tri_data(o):
    me = o.data
    me.calc_loop_triangles()
    verts = [o.matrix_world @ v.co for v in me.vertices]
    polys = [tuple(t.vertices) for t in me.loop_triangles]
    return verts, polys


def sample_surface(verts, polys, n, rng):
    areas = []
    for a, b, c in polys:
        areas.append(((verts[b] - verts[a]).cross(verts[c] - verts[a])).length * 0.5)
    tot = sum(areas)
    pts = []
    for (a, b, c), ar in zip(polys, areas):
        k = max(1, int(round(n * ar / tot)))
        for _ in range(k):
            r1, r2 = rng.random(), rng.random()
            if r1 + r2 > 1:
                r1, r2 = 1 - r1, 1 - r2
            pts.append(verts[a] + (verts[b] - verts[a]) * r1 + (verts[c] - verts[a]) * r2)
    return pts


def remove_islands(o):
    """面の 2% 未満の、本体と離れた島を消す。消した面の数を返す。"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    seen, islands = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for e in cur.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        stack.append(nf)
        islands.append(comp)
    total = len(bm.faces)
    removed = 0
    sizes = sorted((len(c) for c in islands), reverse=True)

    def bbox(comp):
        vs = [v.co for f in comp for v in f.verts]
        return (Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))),
                Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs))))

    mains = [c for c in islands if len(c) >= total * ISLAND_FRAC]
    if not mains:   # 大きな島が無い（細かい葉の集まりなど）ときは何も消さない
        bm.free()
        return 0, sizes[:6]
    mb = [bbox(c) for c in mains]
    size = max((b[1] - b[0]).length for b in mb) if mb else 0
    pad = Vector((size * 0.01,) * 3)
    for comp in islands:
        if comp in mains:
            continue
        if len(comp) >= total * ISLAND_FRAC:
            continue
        lo, hi = bbox(comp)
        # 本体のどの島の外接箱とも重ならない（離れて浮いている）島だけを消す
        touching = any(not (lo.x > b[1].x + pad.x or hi.x < b[0].x - pad.x or lo.y > b[1].y + pad.y or hi.y < b[0].y - pad.y
                            or lo.z > b[1].z + pad.z or hi.z < b[0].z - pad.z) for b in mb)
        if not touching:
            bmesh.ops.delete(bm, geom=[f for f in comp if f.is_valid], context="FACES")
            removed += len(comp)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return removed, sizes[:6]


def convex_hull_mesh(points, name):
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2.0), verts=bm.verts[:], edges=bm.edges[:])
    return bm


def tri_count_bm(bm):
    return sum(len(f.verts) - 2 for f in bm.faces)


def hull_planes(bm):
    return [(f.normal.copy(), f.verts[0].co.copy()) for f in bm.faces]


def make_collision(vis, name, zmax=None):
    """見た目の頂点（zmax があればそれ以下を切り取ったもの）から、凸形状 1 個を作る。
    元の凸包から頂点を減らすのではなく、少ない頂点（極値）から始めて、いまの凸包からいちばん外れた頂点を足していく。
    頂点 18 個以内（三角形 32 以下）、またはいちばん外れた距離が 2mm 未満になったら止める。"""
    bm0 = bmesh.new()
    bm0.from_mesh(vis.data)
    if zmax is not None:
        geom = bm0.verts[:] + bm0.edges[:] + bm0.faces[:]
        bmesh.ops.bisect_plane(bm0, geom=geom, plane_co=(0, 0, zmax), plane_no=(0, 0, 1), clear_outer=True)
    pts = [v.co.copy() for v in bm0.verts]
    bm0.free()
    return make_collision_pts(pts, name)


def make_collision_pts(pts, name):
    """点列から凸形状 1 個を作る（make_collision の後半。42c で複数の凸形状に分けるため切り出した）"""
    full = convex_hull_mesh(pts, name)
    ntri0 = len(full.faces)
    # 元の凸包の頂点だけを候補にする
    cand = [v.co.copy() for v in full.verts]
    full.free()
    sel = []
    for ax in range(3):
        sel.append(min(cand, key=lambda c: c[ax]))
        sel.append(max(cand, key=lambda c: c[ax]))
    max_verts = (COL_MAX_TRIS + 4) // 2   # 三角形 = 2V - 4
    bm = None
    while True:
        uniq = []
        for c in sel:
            if not any((c - u).length < 1e-9 for u in uniq):
                uniq.append(c)
        bm = bmesh.new()
        for c in uniq:
            bm.verts.new(c)
        bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.normal_update()
        planes = hull_planes(bm)
        worst, wc = 0.0, None
        for c in cand:
            d = max((n.dot(c - q) for n, q in planes), default=0.0)
            if d > worst:
                worst, wc = d, c
        nv = len(bm.verts)
        if worst < 0.002 or nv >= max_verts or wc is None:
            break
        bm.free()
        sel = uniq + [wc]
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    co = bpy.data.objects.new(name, me)
    return co, ntri0


def face_islands(me):
    """つながった面の島（面の添字の組）の一覧"""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    seen, out = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        st, comp = [f], []
        seen.add(f.index)
        while st:
            cur = st.pop()
            comp.append(cur.index)
            for e in cur.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        st.append(nf)
        out.append(comp)
    bm.free()
    return out


def island_points(me, comp):
    pts = {}
    for fi in comp:
        for vi in me.polygons[fi].vertices:
            pts[vi] = me.vertices[vi].co.copy()
    return list(pts.values())


def centroid(pts):
    c = Vector((0, 0, 0))
    for p in pts:
        c += p
    return c / len(pts)


def sub_object(o, face_ids, name):
    """面の添字の集まりだけを持つ複製（測定用）"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    keep = set(face_ids)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.matrix_world = o.matrix_world.copy()
    return ob


def collision_groups(o, mode):
    """見た目 o から、凸形状ごとの頂点の組と、測定に使う「見た目」の物（None なら o 全体）を返す。
    mode:
      single       全体で凸 1 個（小箱）
      islands:N    つながった島（大きいもの）を重心の近いもの同士まとめて N 個にする（麻袋の山：袋ごと）
      zsplit:N     高さ方向に、断面の幅がいちばんくびれた所で N 個に切る（壺：胴・首・口）。切り口は両方に含める
      potisland    いちばん大きな島（鉢）だけで凸 1 個。見た目の測定も鉢だけ（葉を除く。植木鉢）"""
    me = o.data
    if mode == "single":
        return [[v.co.copy() for v in me.vertices]], None
    isl = face_islands(me)
    if mode == "potisland":
        big = max(isl, key=len)
        return [island_points(me, big)], sub_object(o, big, "vis_pot")
    kind, _, n = mode.partition(":")
    n = int(n)
    if kind == "islands":
        total = sum(len(c) for c in isl)
        big = [c for c in isl if len(c) >= total * 0.08]
        small = [c for c in isl if len(c) < total * 0.08]
        groups = [[c] for c in big]
        cen = lambda g: centroid([p for c in g for p in island_points(me, c)])
        while len(groups) > n:
            best = None
            for i in range(len(groups)):
                for j in range(i + 1, len(groups)):
                    d = (cen(groups[i]) - cen(groups[j])).length
                    if best is None or d < best[0]:
                        best = (d, i, j)
            _, i, j = best
            groups[i] = groups[i] + groups[j]
            del groups[j]
        for c in small:
            cc = centroid(island_points(me, c))
            k = min(range(len(groups)), key=lambda g: (cen(groups[g]) - cc).length)
            groups[k].append(c)
        return [[p for c in g for p in island_points(me, c)] for g in groups], None
    if kind == "zsplit":
        zs = [v.co.z for v in me.vertices]
        z0, z1 = min(zs), max(zs)
        H = z1 - z0
        nb = 40
        rad = [0.0] * nb
        for v in me.vertices:
            b = min(nb - 1, int((v.co.z - z0) / H * nb))
            rad[b] = max(rad[b], math.hypot(v.co.x, v.co.y))
        # 内側の極小（くびれ）を、浅い順に見て、深い方から n-1 個
        mins = []
        for b in range(3, nb - 3):
            if rad[b] <= min(rad[b - 3:b + 4]) + 1e-9:
                depth = min(max(rad[max(0, b - 10):b]), max(rad[b + 1:min(nb, b + 11)])) - rad[b]
                mins.append((depth, b))
        mins.sort(reverse=True)
        cuts = sorted(z0 + (b + 0.5) / nb * H for _, b in mins[:n - 1])
        groups = []
        edges = [z0 - 1] + cuts + [z1 + 1]
        for a, b in zip(edges[:-1], edges[1:]):
            bm = bmesh.new()
            bm.from_mesh(me)
            for zc, clear_outer in ((b, True), (a, False)):
                if zc < z0 or zc > z1:
                    continue
                geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
                if clear_outer:
                    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, zc), plane_no=(0, 0, 1), clear_outer=True)
                else:
                    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, zc), plane_no=(0, 0, 1), clear_inner=True)
            groups.append([v.co.copy() for v in bm.verts])
            bm.free()
        print("zsplit cuts (cm):", [round((c - z0) * 100, 1) for c in cuts])
        return groups, None
    raise ValueError(mode)


def measure_multi(vis, cols, zmax=None):
    """複数の凸形状をまとめて 1 つの当たり判定として、measure と同じ値を返す"""
    bm = bmesh.new()
    for c in cols:
        bm.from_mesh(c.data)
    me = bpy.data.meshes.new("col_all")
    bm.to_mesh(me)
    bm.free()
    allc = bpy.data.objects.new("col_all", me)
    r = measure(vis, allc, zmax=zmax)
    return r, allc


def measure(vis, col, zmax=None):
    """コリジョンと見た目の表面の差（m）。ハウスドルフ距離（両方向の最大）と、上面の垂直レイの差。"""
    rng = random.Random(0)
    vv, vp = world_tri_data(vis)
    cv, cp = world_tri_data(col)
    vb = BVHTree.FromPolygons(vv, vp)
    cb = BVHTree.FromPolygons(cv, cp)
    c2v = []
    for p in sample_surface(cv, cp, 4000, rng):
        loc = vb.find_nearest(p)[0]
        c2v.append((p - loc).length)
    v2c = []
    vs = list(vv) + sample_surface(vv, vp, 4000, rng)
    for p in vs:
        if zmax is not None and p.z > zmax + 1e-6:
            continue
        loc = cb.find_nearest(p)[0]
        v2c.append((p - loc).length)
    # 上面：外接箱の中心 80% の範囲に格子点を置き、真上から垂直に当てる
    xs = [v.x for v in vv]
    ys = [v.y for v in vv]
    zt = max(v.z for v in vv) + 1.0
    n = 9
    dz = []
    for i in range(n):
        for j in range(n):
            x = min(xs) + (max(xs) - min(xs)) * (0.1 + 0.8 * i / (n - 1))
            y = min(ys) + (max(ys) - min(ys)) * (0.1 + 0.8 * j / (n - 1))
            a = vb.ray_cast(Vector((x, y, zt)), Vector((0, 0, -1)))
            b = cb.ray_cast(Vector((x, y, zt)), Vector((0, 0, -1)))
            if a[0] is not None and b[0] is not None:
                dz.append(b[0].z - a[0].z)
    return {
        "col_to_visual_max_cm": round(max(c2v) * 100, 2),
        "col_to_visual_mean_cm": round(sum(c2v) / len(c2v) * 100, 2),
        "visual_to_col_max_cm": round(max(v2c) * 100, 2),
        "visual_to_col_mean_cm": round(sum(v2c) / len(v2c) * 100, 2),
        "hausdorff_max_cm": round(max(max(c2v), max(v2c)) * 100, 2),
        "top_ray_dz_cm": [round(min(dz) * 100, 2), round(max(dz) * 100, 2)] if dz else None,
        "top_ray_over3cm": "%d/%d" % (sum(1 for d in dz if abs(d) > 0.03), len(dz)),
    }


def render_view(objs, path, wire_obj=None, res=900):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Standard"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "TEXTURE"
    sh.show_shadows = False
    sh.show_cavity = False
    sc.world = bpy.data.worlds.new("w") if sc.world is None else sc.world
    sc.world.color = (0.55, 0.58, 0.62)
    # 全体の外接箱
    pts = []
    for o in objs:
        pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = (mn + mx) / 2
    r = (mx - mn).length / 2
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 50
    cam_d.clip_end = 1000
    cam = bpy.data.objects.new("cam", cam_d)
    sc.collection.objects.link(cam)
    fov = 2 * math.atan(cam_d.sensor_width / 2 / cam_d.lens)
    dist = r / math.sin(fov / 2) * 1.1
    d = Vector((1.0, -1.3, 0.8)).normalized()
    cam.location = ctr + d * dist
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    # 地面の目安（細い板）
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)


def wire_object(col):
    """コリジョンをワイヤー（赤）で見せる複製。"""
    ob = bpy.data.objects.new(col.name + "_wire", col.data.copy())
    bpy.context.scene.collection.objects.link(ob)
    m = bpy.data.materials.new("wire_red")
    m.diffuse_color = (1.0, 0.05, 0.05, 1.0)
    ob.data.materials.append(m)
    md = ob.modifiers.new("w", "WIREFRAME")
    md.thickness = 0.006
    md.use_replace = True
    return ob


def process(cfg, report):
    name, out = cfg["src"], cfg["out"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    bpy.ops.import_scene.gltf(filepath=f"{ROOT}{name}/{name}.glb")
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    assert meshes, name
    set_active(meshes[0])
    for m in meshes:
        m.select_set(True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = out
    o.data.name = out
    # 親があれば外して変換を適用
    o.parent = None
    set_active(o)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    n_parts = len(meshes)

    # 結合・向き・島
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0002)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception as e:
        print("clear custom normals:", e)
    removed, island_sizes = remove_islands(o)

    # 大きさと原点
    me = o.data
    cos = [v.co.copy() for v in me.vertices]
    zmin, zmax = min(c.z for c in cos), max(c.z for c in cos)
    H0 = zmax - zmin
    xs = [c.x for c in cos]
    ys = [c.y for c in cos]
    ext = (max(xs) - min(xs), max(ys) - min(ys), H0)
    pot_note = None
    pot_top = None
    if cfg["axis"] == "pot" and cfg.get("pot_frac") == "island":
        # 鉢＝いちばん大きな島（つながった部分）。その最上点を鉢の上端とする
        bmx = bmesh.new()
        bmx.from_mesh(me)
        bmx.faces.ensure_lookup_table()
        seen2, best = set(), []
        for f in bmx.faces:
            if f.index in seen2:
                continue
            st, comp = [f], []
            seen2.add(f.index)
            while st:
                cur = st.pop()
                comp.append(cur)
                for e in cur.edges:
                    for nf in e.link_faces:
                        if nf.index not in seen2:
                            seen2.add(nf.index)
                            st.append(nf)
            if len(comp) > len(best):
                best = comp
        pot_z = max(v.co.z for f in best for v in f.verts)
        bmx.free()
        cfg = dict(cfg, pot_frac=(pot_z - zmin) / H0)
    if cfg["axis"] == "z":
        k = cfg["target"] / 100.0 / H0
    elif cfg["axis"] == "max":
        k = cfg["target"] / 100.0 / max(ext)
    else:  # pot
        pf = cfg.get("pot_frac")
        if pf:
            k = cfg["target"] / 100.0 / (H0 * pf)
            pot_note = "鉢の上端は元の高さの %.1f%%（いちばん大きなつながり部分の最上点）。植物込みの全高は %.1fcm" % (pf * 100, H0 * k * 100)
            pot_top = cfg["target"] / 100.0
        else:
            k = cfg["fallback"] / 100.0 / H0
            pot_note = "鉢と植物を分けずに全高 %dcm で合わせた" % cfg["fallback"]
    if cfg["root"] == "bottom":
        low = [c for c in cos if c.z < zmin + 0.03 * H0]
        cx = (max(c.x for c in low) + min(c.x for c in low)) / 2
        cy = (max(c.y for c in low) + min(c.y for c in low)) / 2
    else:
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    for v in me.vertices:
        v.co.x = (v.co.x - cx) * k
        v.co.y = (v.co.y - cy) * k
        v.co.z = (v.co.z - zmin) * k
    me.update()

    # 三角形の数と Decimate
    budget = TRI_BUDGET[cfg["kind"]]
    tris_before = tris_of(me)
    decimated = None
    if tris_before > budget:
        set_active(o)
        md = o.modifiers.new("dec", "DECIMATE")
        md.ratio = budget * 0.95 / tris_before
        bpy.ops.object.modifier_apply(modifier="dec")
        decimated = [tris_before, tris_of(o.data)]

    # スムーズ
    set_active(o)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(SMOOTH_ANGLE))

    # マテリアルとテクスチャ（元の png をそのまま参照）
    mat = o.data.materials[0]
    mat.name = "Mat_" + out[3:]
    png = f"{ROOT}{name}/{name}_base_color.png"
    img = bpy.data.images.load(png)
    img.name = name + "_base_color"
    for nd in mat.node_tree.nodes:
        if nd.type == "TEX_IMAGE":
            nd.image = img
    bpy.context.view_layer.update()

    dims = [round(d * 100.0, 2) for d in o.dimensions]
    info = {
        "out": out, "parts_in": n_parts, "islands_removed_faces": removed, "island_sizes_top": island_sizes,
        "tris": tris_of(o.data), "verts": len(o.data.vertices), "dims_cm": dims,
        "decimated": decimated, "texture_px": list(img.size), "material": mat.name,
        "scale_factor": round(k, 4), "origin_root": cfg["root"],
    }
    if pot_note:
        info["pot_note"] = pot_note
    if cfg["kind"] == "corner" and False:
        pass

    # コリジョン（42c：凸形状を 1〜3 個に。col_mode は MODELS の表。無ければ single＝全体で 1 個）
    cols = []
    col = wire = None
    if cfg["col"]:
        mode = cfg.get("col_mode", "single")
        groups, vis_m = collision_groups(o, mode)
        ntris0 = []
        for i, pts in enumerate(groups):
            c, ntri0 = make_collision_pts(pts, "UCX_%s_%02d" % (out, i))
            sc.collection.objects.link(c)
            cols.append(c)
            ntris0.append(ntri0)
        vis_for = vis_m if vis_m is not None else o
        meas, allc = measure_multi(vis_for, cols)
        info["collision"] = {"mode": mode, "parts": len(cols), "tris": [len(c.data.polygons) for c in cols],
                             "hull_tris_before_reduce": ntris0, "verts": [len(c.data.vertices) for c in cols]}
        info["collision"].update(meas)
        col = allc
        sc.collection.objects.link(allc)
        wire = wire_object(allc)
        allc.hide_render = True
        for c in cols:
            c.hide_render = True

    # 確認画像
    render_view([o], f"{ROOT}{name}/{out}_view.png")
    if wire:
        render_view([o, wire], f"{ROOT}{name}/{out}_col.png")
        bpy.data.objects.remove(wire, do_unlink=True)
    if col is not None:
        bpy.data.objects.remove(col, do_unlink=True)

    # 書き出し（見た目＋コリジョン UCX_<名前>_00, _01, ...）
    sel = [o] + cols
    bpy.ops.object.select_all(action="DESELECT")
    for s_ in sel:
        s_.select_set(True)
    bpy.context.view_layer.objects.active = o
    dst = f"{ROOT}{name}/{out}.fbx"
    bpy.ops.export_scene.fbx(filepath=dst, use_selection=True, object_types={"MESH"}, apply_unit_scale=False,
                             apply_scale_options="FBX_SCALE_NONE", global_scale=1.0, axis_forward="-Y", axis_up="Z",
                             mesh_smooth_type="FACE", add_leaf_bones=False, path_mode="AUTO", bake_anim=False)
    info["fbx"] = dst
    report[name] = info
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    report = {}
    if os.path.exists(REPORT):
        report = json.load(open(REPORT, encoding="utf-8"))
    for cfg in MODELS:
        if argv and cfg["src"] not in argv:
            continue
        try:
            info = process(cfg, report)
            print("DONE", cfg["src"], json.dumps(info, ensure_ascii=False))
        except Exception as e:
            import traceback
            traceback.print_exc()
            report[cfg["src"]] = {"error": str(e)}
    json.dump(report, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


main()
