"""L_Canal の経路 6 本の長さの測定（Step 42b D、docs/26 §10.6 と同じ経由点）。L_Canal を開いて Unreal の Python で実行（レベルは変えない）。
RUN_NAME を先に定義すると、Saved/art42/canal_<RUN_NAME>.json に書く（既定 before）。"""
import json, math
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not world.get_path_name().startswith("/Game/PARORANT/Maps/L_Canal"):
    raise RuntimeError("L_Canal を開いてから実行してください（今: %s）" % world.get_path_name())
ROUTES = {
    "atk_A_lane": [(-32, 0), (-20, -28), (-10, -22), (0, -20), (17, -23)],
    "atk_B_quay": [(-32, 0), (-20, 27), (3, 26), (15, 24)],
    "atk_A_bridge": [(-32, 0), (-22, 0), (3, 0), (14, -2), (14, -10), (17, -23)],
    "def_A": [(31, 2), (17, -23)],
    "def_B": [(31, 2), (15, 24)],
    "atk_bridge_def": [(-32, 0), (-22, 0), (3, 0), (31, 2)],
}
NS = unreal.NavigationSystemV1
res = {}
for k, pts in ROUTES.items():
    tot, ok = 0.0, True
    for a, b in zip(pts[:-1], pts[1:]):
        p = NS.find_path_to_location_synchronously(world, unreal.Vector(a[0] * 100, a[1] * 100, 20), unreal.Vector(b[0] * 100, b[1] * 100, 20))
        if p is None or not p.is_valid():
            ok = False
            continue
        pp = p.path_points
        for i in range(len(pp) - 1):
            d = pp[i + 1] - pp[i]
            tot += math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
    res[k] = [round(tot / 100.0, 3), ok]
name = globals().get("RUN_NAME", "before")
json.dump(res, open(unreal.Paths.project_saved_dir() + "art42/canal_" + name + ".json", "w"), indent=1)
print("CANAL ROUTES", name, res)
