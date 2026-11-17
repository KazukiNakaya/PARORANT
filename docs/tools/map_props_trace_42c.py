"""角の小物 4 種（SM_CrateSmall・SM_SackPile・SM_PotPlant・SM_Amphora）の「見た目」と「簡易コリジョン」のずれを、エンジンの中で測る（Step 42c、docs/26_art_meshy.md §8・§10 の樽のときと同じ方法）。

Unreal の Python で実行する（レベルは変えない。空の上 (9000, 9000, 500) に仮のアクタを 1 個置いて、測り終わったら消す）。
見た目への「複雑な」レイ：メッシュの三角形（LOD0）への自前のレイ交差（Möller–Trumbore）。簡易コリジョンへの「単純な」トレース：line_trace_single（Visibility、簡易）。
平行なレイを 5cm 間隔の格子で、横（±X・±Y の 4 方向）と上から撃ち、同じレイでの最初の当たりを比べる。
  pass（見えているのに抜ける）= 見た目の最初の面より奥で当たる（または当たらない）。深さ = コリジョンの当たり - 見た目の当たり（cm）、当たらないときは見た目の裏側の面までの距離
  ghost（見えないのに当たる）= 見た目に当たらないのにコリジョンに当たる。深さ = 当たった点から見た目の三角形までの最短距離（cm）
MESHES に (名前, 高さの上限 cm または None) を渡す。植木鉢は葉を除くため、つながった最大の島（鉢）だけを見た目とし、上からのレイは撃たない（MESHES の高さ値は印）。
結果は Saved/art42/props_trace_42c.json と表示。縮尺 1.0 で測る（配置では 0.78〜1.08 倍されるので、ずれも同じ比で小さくなる）。
"""
import json, math
import unreal

D = unreal.Paths.project_dir() + "Saved/art42/"
MESHES = globals().get("MESHES") or [("SM_CrateSmall", None), ("SM_SackPile", None), ("SM_PotPlant", 56.0), ("SM_Amphora", None)]
OUT = globals().get("OUT_NAME") or "props_trace_42c"
STEP = 5.0
ea = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
BASE = unreal.Vector(9000, 9000, 500)


def mt(o, d, v0, v1, v2):
    e1 = [v1[i] - v0[i] for i in range(3)]
    e2 = [v2[i] - v0[i] for i in range(3)]
    h = [d[1] * e2[2] - d[2] * e2[1], d[2] * e2[0] - d[0] * e2[2], d[0] * e2[1] - d[1] * e2[0]]
    a = e1[0] * h[0] + e1[1] * h[1] + e1[2] * h[2]
    if abs(a) < 1e-12:
        return None
    f = 1.0 / a
    s = [o[i] - v0[i] for i in range(3)]
    u = f * (s[0] * h[0] + s[1] * h[1] + s[2] * h[2])
    if u < 0 or u > 1:
        return None
    q = [s[1] * e1[2] - s[2] * e1[1], s[2] * e1[0] - s[0] * e1[2], s[0] * e1[1] - s[1] * e1[0]]
    w = f * (d[0] * q[0] + d[1] * q[1] + d[2] * q[2])
    if w < 0 or u + w > 1:
        return None
    t = f * (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2])
    return t if t > 0 else None


def sub(a, b): return [a[i] - b[i] for i in range(3)]
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def pt_tri(p, a, b, c):
    """点 p から三角形 abc までの最短距離（Ericson）"""
    ab, ac, ap = sub(b, a), sub(c, a), sub(p, a)
    d1, d2 = dot(ab, ap), dot(ac, ap)
    if d1 <= 0 and d2 <= 0: q = a
    else:
        bp = sub(p, b); d3, d4 = dot(ab, bp), dot(ac, bp)
        if d3 >= 0 and d4 <= d3: q = b
        else:
            vc = d1 * d4 - d3 * d2
            if vc <= 0 and d1 >= 0 and d3 <= 0:
                v = d1 / (d1 - d3); q = [a[i] + v * ab[i] for i in range(3)]
            else:
                cp = sub(p, c); d5, d6 = dot(ab, cp), dot(ac, cp)
                if d6 >= 0 and d5 <= d6: q = c
                else:
                    vb = d5 * d2 - d1 * d6
                    if vb <= 0 and d2 >= 0 and d6 <= 0:
                        w = d2 / (d2 - d6); q = [a[i] + w * ac[i] for i in range(3)]
                    else:
                        va = d3 * d6 - d5 * d4
                        if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
                            w = (d4 - d3) / ((d4 - d3) + (d5 - d6)); q = [b[i] + w * (c[i] - b[i]) for i in range(3)]
                        else:
                            den = 1.0 / (va + vb + vc); v = vb * den; w = vc * den
                            q = [a[i] + ab[i] * v + ac[i] * w for i in range(3)]
    return math.sqrt(sum((p[i] - q[i]) ** 2 for i in range(3)))


result = {}
for name, zcap in MESHES:
    m = ea.load_asset("/Game/PARORANT/Art/Props/" + name)
    verts, tris, *_ = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(m, 0, 0)
    V = [(v.x, v.y, v.z) for v in verts]
    T = [(tris[i], tris[i + 1], tris[i + 2]) for i in range(0, len(tris), 3)]
    nsec = m.get_num_sections(0) if hasattr(m, "get_num_sections") else 1
    if zcap is not None:
        # 葉を除く：位置でつなげた最大の島（鉢）だけを見た目とする。取り込みで頂点が分かれているので、位置（0.01cm）で同じ点とみなす
        key = lambda v: (round(v[0], 2), round(v[1], 2), round(v[2], 2))
        par = {}
        def find(x):
            while par.setdefault(x, x) != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for t in T:
            ks = [key(V[i]) for i in t]
            for k2 in ks[1:]:
                par[find(ks[0])] = find(k2)
        comp = {}
        for t in T:
            comp.setdefault(find(key(V[t[0]])), []).append(t)
        T = max(comp.values(), key=len)
        zcap = max(V[i][2] for t in T for i in t)
    xs, ys, zs = [v[0] for v in V], [v[1] for v in V], [v[2] for v in V]
    bb = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
    ztop = zcap if zcap is not None else bb[5]
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, BASE)
    a.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
    a.static_mesh_component.set_static_mesh(m)
    a.static_mesh_component.set_collision_profile_name("BlockAll")
    rays = []   # (原点, 向き, 長さ)
    R = 150.0
    z = STEP / 2
    while z < ztop:
        u = bb[2] + STEP / 2
        while u < bb[3]:
            rays.append(((bb[0] - R, u, z), (1, 0, 0))); rays.append(((bb[1] + R, u, z), (-1, 0, 0)))
            u += STEP
        u = bb[0] + STEP / 2
        while u < bb[1]:
            rays.append(((u, bb[2] - R, z), (0, 1, 0))); rays.append(((u, bb[3] + R, z), (0, -1, 0)))
            u += STEP
        z += STEP
    if zcap is None:
        x = bb[0] + STEP / 2
        while x < bb[1]:
            y = bb[2] + STEP / 2
            while y < bb[3]:
                rays.append(((x, y, bb[5] + R), (0, 0, -1)))
                y += STEP
            x += STEP
    passes, ghosts, nmiss_both, nboth = [], [], 0, 0
    worst_pass, worst_ghost = None, None
    for o, d in rays:
        ts = []
        for (i0, i1, i2) in T:
            t = mt(o, d, V[i0], V[i1], V[i2])
            if t is not None:
                ts.append(t)
        end = (o[0] + d[0] * 600, o[1] + d[1] * 600, o[2] + d[2] * 600)
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(BASE.x + o[0], BASE.y + o[1], BASE.z + o[2]),
                                                     unreal.Vector(BASE.x + end[0], BASE.y + end[1], BASE.z + end[2]),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        tc = hit.to_tuple()[3] if hit is not None else None   # 距離（cm、レイの原点から）
        if ts and tc is not None:
            nboth += 1
            dep = tc - min(ts)
            if dep > 0.0: passes.append(dep)
            if dep > 0 and (worst_pass is None or dep > worst_pass[0]): worst_pass = (round(dep, 2), tuple(round(c, 1) for c in o), d)
            if dep < 0: ghosts.append(-dep)   # コリジョンが見た目より手前＝見えないのに当たる（レイの上の差）
        elif ts and tc is None:
            # 見えているのにコリジョンにまったく当たらない：レイに沿った厚みでは大きく出すぎるので、見た目の最初の当たりの点から
            # 軸（原点の鉛直線）へ向かって水平にトレースし、コリジョンまでの距離を「抜ける深さ」とする（当たらなければ軸までの距離）
            p0 = [o[i] + d[i] * min(ts) for i in range(3)]
            rr = math.hypot(p0[0], p0[1])
            if rr < 1e-6:
                dep = max(ts) - min(ts)
            else:
                tgt = (0.0, 0.0, p0[2])
                hit2 = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(BASE.x + p0[0], BASE.y + p0[1], BASE.z + p0[2]),
                                                              unreal.Vector(BASE.x + tgt[0], BASE.y + tgt[1], BASE.z + tgt[2]),
                                                              unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
                # 見た目の表面の内側から始まるのでコリジョンの外から入る当たりだけを見る（始点がコリジョンの中なら initial overlap で 0）
                dep = hit2.to_tuple()[3] if hit2 is not None and not hit2.to_tuple()[1] else (0.0 if hit2 is not None else rr)
            passes.append(dep)
            nmiss_both += 1
            if worst_pass is None or dep > worst_pass[0]: worst_pass = (round(dep, 2), tuple(round(c, 1) for c in o), d)
        elif (not ts) and tc is not None:
            p = [o[i] + d[i] * tc for i in range(3)]
            dist = min(pt_tri(p, V[t[0]], V[t[1]], V[t[2]]) for t in T)
            ghosts.append(dist)
            if worst_ghost is None or dist > worst_ghost[0]: worst_ghost = (round(dist, 2), tuple(round(c, 1) for c in o), d)
    a.destroy_actor()
    result[name] = {
        "bbox_cm": [round(c, 1) for c in bb], "tris": len(T), "rays": len(rays), "both": nboth, "visible_but_no_collision_hit": nmiss_both,
        "pass_max_cm": round(max(passes), 2) if passes else 0.0, "pass_over10": sum(1 for x in passes if x > 10), "pass_over5": sum(1 for x in passes if x > 5), "pass_n": len(passes),
        "ghost_max_cm": round(max(ghosts), 2) if ghosts else 0.0, "ghost_over10": sum(1 for x in ghosts if x > 10), "ghost_over5": sum(1 for x in ghosts if x > 5), "ghost_n": len(ghosts),
        "worst_pass": worst_pass, "worst_ghost": worst_ghost, "zcap": zcap,
    }
    print(name, json.dumps(result[name], ensure_ascii=False))
json.dump(result, open(D + OUT + ".json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
