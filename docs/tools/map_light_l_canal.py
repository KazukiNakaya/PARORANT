"""PARORANT L_Canal 光の仕上げ（Step 38、docs/26 §6.5・docs/20 §5.1）。

map_art_l_canal.py の最後から実行される。単独でも実行できる（L_Canal を開いて Unreal の Python で実行）。
既存のアクタ（SunLight、SkyLight、PP_Mood、A_Lamp_0〜3、Art_StreetLamp_*）の値を決めた値にそろえるだけ。何度実行しても同じ結果になる。
注意：unreal.Color の引数の順は (b, g, r, a)。必ずキーワード（r=, g=, b=, a=）で指定する。
"""
import unreal

_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
if not _world.startswith("/Game/PARORANT/Maps/L_Canal"):
    raise RuntimeError("L_Canal を開いてから実行してください（今のレベル: %s）" % _world)

LIGHT = {
    "sun_pitch": -27.0, "sun_yaw": 40.0, "sun_intensity": 7.0, "sun_color": (255, 235, 204),
    "sky_intensity": 7.0, "sky_color": (236, 242, 252),
    "sky_luminance_factor": 2.4,   # SkyAtmosphere の空の明るさ（固定の露出で空が暗い紺にならないように）
    "exposure_ev": 1.5,          # 自動露出を切り、最小＝最大のこの値に固定（EV100 相当。histogram のまま Min と Max を同じにする）
    "exposure_bias": 1.0,
    "a_lamp_intensity": 110.0, "a_lamp_radius": 1800.0, "a_lamp_color": (255, 214, 164),
    "street_intensity": 30.0, "street_radius": 900.0, "street_color": (255, 190, 120),
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
            c.recapture_sky()   # エディタの画面に反映するため（ゲームはリアルタイム取り込みで毎フレーム更新）
        elif n == "SkyAtmosphere":
            c = a.get_component_by_class(unreal.SkyAtmosphereComponent)
            f = L["sky_luminance_factor"]
            c.set_editor_property("sky_luminance_factor", unreal.LinearColor(f, f, f, 1.0))
        elif n == "PP_Mood":
            s = a.get_editor_property("settings")
            for k in ("override_auto_exposure_min_brightness", "override_auto_exposure_max_brightness", "override_auto_exposure_bias"):
                s.set_editor_property(k, True)
            s.set_editor_property("auto_exposure_min_brightness", L["exposure_ev"])
            s.set_editor_property("auto_exposure_max_brightness", L["exposure_ev"])
            s.set_editor_property("auto_exposure_bias", L["exposure_bias"])
            a.set_editor_property("settings", s)
        elif n.startswith("A_Lamp_"):
            c = a.get_component_by_class(unreal.PointLightComponent)
            c.set_editor_property("intensity", L["a_lamp_intensity"])
            c.set_editor_property("attenuation_radius", L["a_lamp_radius"])
            c.set_editor_property("light_color", unreal.Color(r=L["a_lamp_color"][0], g=L["a_lamp_color"][1], b=L["a_lamp_color"][2], a=255))
        elif n.startswith("Art_StreetLamp_"):
            c = a.get_component_by_class(unreal.PointLightComponent)
            c.set_editor_property("intensity", L["street_intensity"])
            c.set_editor_property("attenuation_radius", L["street_radius"])
            c.set_editor_property("light_color", unreal.Color(r=L["street_color"][0], g=L["street_color"][1], b=L["street_color"][2], a=255))
    print("LIGHT applied", L)


apply_light()
