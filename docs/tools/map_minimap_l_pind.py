"""PARORANT L_Pind ミニマップ画像の撮り直し（Step 42a、docs/29_pind_tropical.md §2.3）。

L_Pind を開いて Unreal の Python で実行する（L_Pind 以外では止まる）。見た目の部品（ArtHost、タグ PindArt の物を除く壁の上の屋根など）を隠すのではなく、
読みやすくするため撮影の間だけ、壁（Wall_*、パネル、建物）を明るい 1 色、床と舗装・桟橋を暗い 1 色にし、太陽を真上近く（ピッチ -88°、強さ 4）にして、
真上の正射影（OrthoWidth 8000＝MapInfo の MinimapMin/Max ±4000、最終色 LDR）で撮り、既存の T_PR_Minimap_Pind（圧縮・ミップ・ストリーミングの設定そのまま）へ書き込む。
撮影後は必ず元へ戻す（素材、太陽の向き・強さは map_light_l_pind.py の値を再適用）。
WRITE_TEXTURE = True を先に定義して実行すると書き込む（定義が無いと PNG を Saved/art42 へ出すだけ）。
"""
import unreal

_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
if not _world.startswith("/Game/PARORANT/Maps/L_Pind"):
    raise RuntimeError("L_Pind を開いてから実行してください（今のレベル: %s）" % _world)

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = list(eas.get_all_level_actors())
hide = []
sun = None
for a in acts:
    n = a.get_actor_label()
    if n == "ArtHost":
        hide.append(a)
    elif n == "SunLight":
        sun = a
for a in acts:   # 前回の失敗で残った撮影用アクタを消す
    if a.get_class().get_name() == "SceneCapture2D":
        eas.destroy_actor(a)
sc = sun.get_component_by_class(unreal.DirectionalLightComponent)
cap = None
mat_wall = unreal.EditorAssetLibrary.load_asset("/Game/PARORANT/Materials/MI_Nature_Wall")
mat_floor = unreal.EditorAssetLibrary.load_asset("/Game/PARORANT/Materials/MI_Nature_Floor")
saved_mats = []
for a in acts:
    n = a.get_actor_label()
    if a.get_class().get_name() != "StaticMeshActor":
        continue
    c = a.static_mesh_component
    if (n.startswith("Wall_") and n not in ("Wall_N", "Wall_S", "Wall_E", "Wall_W")) or n.startswith(("Panel_", "Bld_")):
        saved_mats.append((a, [c.get_material(i) for i in range(len(c.get_materials()))]))
        for i in range(len(c.get_materials())):
            c.set_material(i, mat_wall)
    elif n == "Floor" or n.startswith(("Paving_", "Pier_")):
        saved_mats.append((a, [c.get_material(i) for i in range(len(c.get_materials()))]))
        for i in range(len(c.get_materials())):
            c.set_material(i, mat_floor)
try:
    sun.set_actor_rotation(unreal.Rotator(0.0, -88.0, 40.0), False)
    sc.set_editor_property("intensity", 4.0)
    rt = unreal.RenderingLibrary.create_render_target2d(world, 1024, 1024, unreal.TextureRenderTargetFormat.RTF_RGBA8, unreal.LinearColor(0, 0, 0, 1), False)
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 6840), unreal.Rotator(0, -90, 0))
    cc = cap.get_editor_property("capture_component2d")
    cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
    cc.set_editor_property("ortho_width", 8000.0)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_every_frame", False)
    cc.set_editor_property("capture_on_movement", False)
    for h in hide:
        cc.hide_actor_components(h, True)
    cc.capture_scene()
    cc.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, unreal.Paths.project_saved_dir() + "art42", "minimap_pind")
    if globals().get("WRITE_TEXTURE", False):
        tex = unreal.EditorAssetLibrary.load_asset("/Game/PARORANT/UI/T_PR_Minimap_Pind")
        unreal.RenderingLibrary.convert_render_target_to_texture2d_editor_only(world, rt, tex)
        unreal.EditorAssetLibrary.save_loaded_asset(tex)
        print("texture written")
finally:
    for a, ms in saved_mats:
        for i, m in enumerate(ms):
            a.static_mesh_component.set_material(i, m)
    if cap:
        eas.destroy_actor(cap)
    _p = unreal.Paths.project_dir() + "docs/tools/map_light_l_pind.py"
    exec(compile(open(_p, encoding="utf-8").read(), _p, "exec"), {"unreal": unreal})   # 太陽の向き・強さを決めた値へ戻す
