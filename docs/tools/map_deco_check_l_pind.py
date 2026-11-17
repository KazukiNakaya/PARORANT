"""L_Pind の角の小物（タグ PindDeco）の上からの視線の確認（Step 42b C、docs/26 §10.5 と同じ考え方）。

L_Pind を開いて Unreal の Python で実行（レベルは変えない）。各小物について、小物の上（目の高さ = 小物の上面 + 1.6m、中心と四方 20cm の 5 点）と、
地面（同じ XY、目の高さ 1.6m）から、持ち場（床 + 1.6m）と設置エリア A・B の中心（高さ 1m）へ可視性トレースを撃つ。
「地面から見えず、小物の上から見える」組の数を数える（小物そのもの PindDeco は無視しない：地面の目は小物に遮られるので、小物を含めて比べる）。
結果を表示する。
"""
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
targets = []
for a in acts:
    lb = a.get_actor_label()
    l = a.get_actor_location()
    if lb.startswith("Hold_"):
        targets.append((lb, unreal.Vector(l.x, l.y, 160.0)))
    elif lb.startswith("PlantZone_"):
        targets.append((lb, unreal.Vector(l.x, l.y, 100.0)))
DECO_TAG = globals().get("DECO_TAG", "PindDeco")   # L_Canal では "CanalDeco" を渡す（Step 42b D）
decos = [a for a in acts if unreal.Name(DECO_TAG) in a.tags]


def vis(a, b, ignore):
    r = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignore,
                                               unreal.DrawDebugTrace.NONE, True)
    return r is None or not r.to_tuple()[0]


new_total = 0
rows = []
for d in decos:
    o, e = d.get_actor_bounds(False)
    top = o.z + e.z
    c = d.get_actor_location()
    new = []
    for (tn, tp) in targets:
        ground = vis(unreal.Vector(c.x, c.y, 160.0), tp, [d])
        if ground:
            continue
        for (ox, oy) in ((0, 0), (20, 0), (-20, 0), (0, 20), (0, -20)):
            if vis(unreal.Vector(c.x + ox, c.y + oy, top + 160.0), tp, [d]):
                new.append(tn)
                break
    new_total += len(new)
    rows.append((d.get_actor_label(), round(top), new))
for r in rows:
    if r[2]:
        print("NEW LOS", r)
print("DECO LOS CHECK: decos", len(decos), "targets", len(targets), "new sight pairs", new_total)
