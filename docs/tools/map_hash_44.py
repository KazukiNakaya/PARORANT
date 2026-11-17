"""Step 44: 形・当たり判定が変わっていないことの確認用ハッシュ（レベルは変えない）。
開いているレベルの、タグ IntroIsland が付いていないアクタすべてについて、位置・回転・拡大・各コンポーネントの当たり判定の設定・境界を数値にしてハッシュする。
RUN_NAME を先に定義すると Saved/art42/hash44_<マップ名>_<RUN_NAME>.json に書く。比べるときは ALL_HASH の値を見る。"""
import hashlib, json
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
mapname = world.get_path_name().split("/")[-1].split(".")[0]
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rows = {}
def f(v): return "%.2f,%.2f,%.2f" % (v.x, v.y, v.z)
for a in eas.get_all_level_actors():
    if unreal.Name("IntroIsland") in list(a.tags) or unreal.Name("IntroOnly") in list(a.tags):
        continue
    parts = [a.get_class().get_name(), f(a.get_actor_location()), "%.2f,%.2f,%.2f" % (a.get_actor_rotation().roll, a.get_actor_rotation().pitch, a.get_actor_rotation().yaw), f(a.get_actor_scale3d())]
    for c in a.get_components_by_class(unreal.PrimitiveComponent):
        try:
            o, e = a.get_actor_bounds(False)
            parts.append("%s|%s|%s|%s|%s" % (c.get_name(), c.get_collision_enabled().name, c.get_collision_profile_name(), c.get_editor_property("can_ever_affect_navigation"), c.get_editor_property("hidden_in_game")))
            if isinstance(c, unreal.InstancedStaticMeshComponent):
                parts.append("n=%d" % c.get_instance_count())
        except Exception as ex:
            parts.append("ERR " + str(ex)[:40])
    rows[a.get_actor_label() + "#" + a.get_name()] = "|".join(parts)
allh = hashlib.sha1("\n".join("%s=%s" % (k, rows[k]) for k in sorted(rows)).encode()).hexdigest()
name = globals().get("RUN_NAME", "before")
out = {"map": mapname, "actors": len(rows), "ALL_HASH": allh, "per": {k: hashlib.sha1(v.encode()).hexdigest()[:10] for k, v in rows.items()}}
json.dump(out, open(unreal.Paths.project_saved_dir() + "art42/hash44_%s_%s.json" % (mapname, name), "w"), indent=0)
print("HASH44", mapname, name, "actors", len(rows), allh)
