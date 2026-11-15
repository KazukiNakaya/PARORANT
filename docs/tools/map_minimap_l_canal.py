"""PARORANT L_Canal ミニマップ画像の撮り直し（Step 38、docs/26 §6.5）。

L_Canal を開いて Unreal の Python で実行する。見た目の部品（ArtHost、タグ CanalArt の灯り）、A の屋根・2 階の回廊と手すり、A の灯りを撮影の間だけ隠し、
太陽を真上近く（ピッチ -88°、強さ 4）にして、真上の正射影（OrthoWidth 7200、最終色 LDR）で撮り、既存の T_PR_Minimap_Canal（圧縮・ミップ・ストリーミングの設定そのまま）へ書き込む。
撮影後は必ず元へ戻す（太陽の向き・強さは map_light_l_canal.py の値を再適用）。WRITE_TEXTURE = True を先に定義して実行すると書き込む（定義が無いと PNG を Saved/art38 へ出すだけ）。
"""
import unreal, math

_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
if not _world.startswith("/Game/PARORANT/Maps/L_Canal"):
    raise RuntimeError("L_Canal を開いてから実行してください（今のレベル: %s）" % _world)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = list(eas.get_all_level_actors())
hide = []
lights = []
sun = None
for a in acts:
    n = a.get_actor_label()
    tags = [str(t) for t in a.tags]
    if n == "ArtHost" or n in ("A_Roof", "A_Corridor", "A_CorridorRail_1", "A_CorridorRail_2", "A_SlopeRail"):
        hide.append(a)
    elif "CanalArt" in tags and a.get_class().get_name() == "PointLight":
        hide.append(a); lights.append(a)
    elif n.startswith("A_Lamp_"):
        hide.append(a); lights.append(a)
    elif n == "SunLight":
        sun = a

# 前回の失敗で残った撮影用アクタを消す
for a in acts:
    if a.get_class().get_name() == "SceneCapture2D":
        eas.destroy_actor(a)
sc = sun.get_component_by_class(unreal.DirectionalLightComponent)
cap = None
# 歩ける範囲と壁を読みやすくするため、撮影の間だけ壁を明るい 1 色、床と舗装を暗い 1 色にする（撮影後に元の素材へ戻す）
mat_wall = unreal.EditorAssetLibrary.load_asset("/Game/PARORANT/Materials/MI_Nature_Wall")
mat_floor = unreal.EditorAssetLibrary.load_asset("/Game/PARORANT/Materials/MI_Nature_Floor")
saved_mats = []
for a in acts:
    n = a.get_actor_label()
    if n.startswith("Wall_") and n not in ("Wall_N", "Wall_S", "Wall_E", "Wall_W"):
        saved_mats.append((a, a.static_mesh_component.get_material(0))); a.static_mesh_component.set_material(0, mat_wall)
    elif n.startswith("Floor_") or n.startswith("Paving_"):
        saved_mats.append((a, a.static_mesh_component.get_material(0))); a.static_mesh_component.set_material(0, mat_floor)
try:
    for l in lights:
        l.get_component_by_class(unreal.PointLightComponent).set_visibility(False)
    sun.set_actor_rotation(unreal.Rotator(0.0, -88.0, 40.0), False)
    sc.set_editor_property("intensity", 4.0)
    rt = unreal.RenderingLibrary.create_render_target2d(world, 1024, 1024, unreal.TextureRenderTargetFormat.RTF_RGBA8, unreal.LinearColor(0, 0, 0, 1), False)
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 6840), unreal.Rotator(0, -90, 0))
    cc = cap.get_editor_property("capture_component2d")
    cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
    cc.set_editor_property("ortho_width", 7200.0)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_every_frame", False)
    cc.set_editor_property("capture_on_movement", False)
    for h in hide:
        cc.hide_actor_components(h, True)
    cc.capture_scene()
    cc.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, unreal.Paths.project_saved_dir() + "art38", "minimap_canal")
    if globals().get("WRITE_TEXTURE", False):
        tex = unreal.EditorAssetLibrary.load_asset("/Game/PARORANT/UI/T_PR_Minimap_Canal")
        unreal.RenderingLibrary.convert_render_target_to_texture2d_editor_only(world, rt, tex)
        unreal.EditorAssetLibrary.save_loaded_asset(tex)
        print("texture written")
finally:
    for a, m in saved_mats:
        a.static_mesh_component.set_material(0, m)
    if cap:
        eas.destroy_actor(cap)
    for l in lights:
        l.get_component_by_class(unreal.PointLightComponent).set_visibility(True)
    _p = unreal.Paths.project_dir() + "docs/tools/map_light_l_canal.py"
    exec(compile(open(_p, encoding="utf-8").read(), _p, "exec"), {"unreal": unreal})   # 太陽の向き・強さを決めた値へ戻す

