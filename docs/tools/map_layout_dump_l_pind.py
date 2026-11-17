"""L_Pind の壁・パネル・建物・遮蔽の外形、持ち場・経由点・スタート位置、設置エリア・バリアの外形を Saved/Scratch/pind_layout.json に書き出す（Step 42b C）。
L_Pind を開いて Unreal の Python で実行する（レベルは変えない）。map_deco_sites_l_pind.py（オフラインの置き場所の計算）の入力。"""
import unreal, json, os
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = {'solid': [], 'pts': {}, 'zones': []}
for a in eas.get_all_level_actors():
    lb = a.get_actor_label(); fo = str(a.get_folder_path())
    if fo.startswith('Art'):
        continue
    o, e = a.get_actor_bounds(False); l = a.get_actor_location()
    r = [round(o.x / 100 - e.x / 100, 3), round(o.x / 100 + e.x / 100, 3), round(o.y / 100 - e.y / 100, 3), round(o.y / 100 + e.y / 100, 3)]
    if lb.startswith(('Wall_', 'Panel_', 'Bld_', 'Cover')):
        out['solid'].append([lb] + r + [round((o.z + e.z) / 100, 2)])
    elif lb.startswith(('Hold_', 'FlankPoint', 'PlayerStart')):
        out['pts'][lb] = [round(l.x / 100, 2), round(l.y / 100, 2)]
    elif lb.startswith(('PlantZone', 'Barrier')):
        out['zones'].append([lb] + r)
d = unreal.Paths.project_dir() + 'Saved/Scratch'
os.makedirs(d, exist_ok=True)
json.dump(out, open(d + '/pind_layout.json', 'w'))
