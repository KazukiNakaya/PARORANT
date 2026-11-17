"""PARORANT L_Pind 光の仕上げ（Step 42a、docs/29_pind_tropical.md §2.3）。昼の強い日差しの南国。

map_art_l_pind.py の最後から実行される。単独でも実行できる（L_Pind を開いて Unreal の Python で実行）。
既存のアクタ（SunLight、SkyLight、SkyAtmosphere、HeightFog、PP_Mood）の値を決めた値にそろえるだけ。何度実行しても同じ結果になる。
露出は最小＝最大の値で固定する（今までの L_Pind は自動露出の範囲が広いままだった）。
注意：unreal.Color の引数の順は (b, g, r, a)。必ずキーワード（r=, g=, b=, a=）で指定する。
"""
import unreal

_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
if not _world.startswith("/Game/PARORANT/Maps/L_Pind"):
    raise RuntimeError("L_Pind を開いてから実行してください（今のレベル: %s）" % _world)

LIGHT = {
    "sun_pitch": -58.0, "sun_yaw": 40.0, "sun_intensity": 5.0, "sun_color": (255, 244, 226),   # 高い太陽（影は短くてはっきり）
    "sky_intensity": 5.0, "sky_color": (205, 228, 255),
    "sky_luminance_factor": 1.8,       # 濃い青の空。固定の露出で暗い紺にならない範囲
    "exposure_ev": 1.5, "exposure_bias": 1.0,   # 自動露出を切り、最小＝最大のこの値に固定する
    "fog_density": 0.003,              # 薄い霞
    "saturation": 1.05, "bloom": 0.3, "vignette": 0.15,
}


def apply_light():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    L = LIGHT
    for a in eas.get_all_level_actors():
        n = a.get_actor_label()
        if n == "SunLight":
            a.set_actor_rotation(unreal.Rotator(0.0, L["sun_pitch"], L["sun_yaw"]), False)   # (roll, pitch, yaw)
            c = a.get_component_by_class(unreal.DirectionalLightComponent)
            c.set_editor_property("intensity", L["sun_intensity"])
            c.set_editor_property("light_color", unreal.Color(r=L["sun_color"][0], g=L["sun_color"][1], b=L["sun_color"][2], a=255))
        elif n == "SkyLight":
            c = a.get_component_by_class(unreal.SkyLightComponent)
            c.set_editor_property("intensity", L["sky_intensity"])
            c.set_editor_property("light_color", unreal.Color(r=L["sky_color"][0], g=L["sky_color"][1], b=L["sky_color"][2], a=255))
            c.recapture_sky()
        elif n == "SkyAtmosphere":
            c = a.get_component_by_class(unreal.SkyAtmosphereComponent)
            f = L["sky_luminance_factor"]
            c.set_editor_property("sky_luminance_factor", unreal.LinearColor(f, f, f, 1.0))
        elif n == "HeightFog":
            c = a.get_component_by_class(unreal.ExponentialHeightFogComponent)
            c.set_editor_property("fog_density", L["fog_density"])
        elif n == "PP_Mood":
            s = a.get_editor_property("settings")
            for k in ("override_auto_exposure_min_brightness", "override_auto_exposure_max_brightness", "override_auto_exposure_bias",
                      "override_color_saturation", "override_bloom_intensity", "override_vignette_intensity"):
                s.set_editor_property(k, True)
            s.set_editor_property("auto_exposure_min_brightness", L["exposure_ev"])
            s.set_editor_property("auto_exposure_max_brightness", L["exposure_ev"])
            s.set_editor_property("auto_exposure_bias", L["exposure_bias"])
            s.set_editor_property("color_saturation", unreal.Vector4(L["saturation"], L["saturation"], L["saturation"], 1.0))
            s.set_editor_property("bloom_intensity", L["bloom"])
            s.set_editor_property("vignette_intensity", L["vignette"])
            a.set_editor_property("settings", s)
    print("PIND LIGHT applied", L)


apply_light()
