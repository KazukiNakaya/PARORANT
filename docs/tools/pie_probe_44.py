"""Step 44 の確認用：PIE の 25 秒後（購入フェーズ）に、カメラの位置、霧、IntroOnly のコンポーネントの可視状態をログに書き、
VIS_OFF=True なら IntroOnly の全コンポーネントの可視を切る（試合中の見え方の切り分け用）。"""
import unreal
P = unreal.Paths.project_dir()
LOG = P + "Saved/art42/pie_probe_44.log"
open(LOG, "w").write("")
VIS_OFF = globals().get("VIS_OFF", False)
def W(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
st = {"t": 0.0, "h": None, "done": False}
def L(*a): open(LOG, "a").write(" ".join(str(x) for x in a) + "\n")
def tick(dt):
    try:
        w = W()
        if w is None: return
        st["t"] += dt
        if st["t"] > 26 and not st["done"]:
            st["done"] = True
            pc = unreal.GameplayStatics.get_player_controller(w, 0)
            cm = pc.player_camera_manager
            L("cam", cm.get_camera_location(), cm.get_camera_rotation(), "fov", cm.get_fov_angle())
            for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.ExponentialHeightFog):
                c = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
                L("fog density", c.get_editor_property("fog_density"), "start", c.get_editor_property("start_distance"), "color", c.get_editor_property("fog_inscattering_color"))
            only = unreal.GameplayStatics.get_all_actors_with_tag(w, "IntroOnly")
            vis = 0
            for a in only:
                for c in a.get_components_by_class(unreal.PrimitiveComponent):
                    if c.is_visible(): vis += 1
                    if VIS_OFF: c.set_visibility(False)
            L("IntroOnly actors", len(only), "visible components (flag)", vis, "VIS_OFF", VIS_OFF)
        if st["t"] > 34:
            L("done"); unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback; L(traceback.format_exc()); unreal.unregister_slate_post_tick_callback(st["h"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
