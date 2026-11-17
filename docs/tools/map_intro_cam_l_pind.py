"""Step 44 A: L_Pind の紹介画面のカメラを斜め後ろ上（攻撃側の桟橋の側）にし、屋根を隠すのをやめる（docs/31 §2.5）。
L_Pind を開いて Unreal の Python で実行（L_Pind 以外では止まる）。何度実行しても同じ結果。
  - MapInfo の IntroCamLoc / IntroCamRot を変える
  - タグ IntroHide を、アクタ・コンポーネントから外す（形・当たり判定・光は変えない）
"""
import unreal

_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
if not _world.startswith("/Game/PARORANT/Maps/L_Pind"):
    raise RuntimeError("L_Pind を開いてから実行してください（今のレベル: %s）" % _world)

INTRO_LOC = unreal.Vector(-6700.0, -2700.0, 5000.0)
INTRO_ROT = unreal.Rotator(0.0, -40.0, 14.0)   # (roll, pitch, yaw)
TAG = unreal.Name("IntroHide")

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "MapInfo":
        a.set_editor_property("IntroCamLoc", INTRO_LOC)
        a.set_editor_property("IntroCamRot", INTRO_ROT)
        print("MapInfo camera", a.get_editor_property("IntroCamLoc"), a.get_editor_property("IntroCamRot"))
    if TAG in list(a.tags):
        a.tags = [t for t in a.tags if t != TAG]
        print("actor untagged", a.get_actor_label())
    for c in a.get_components_by_class(unreal.ActorComponent):
        if TAG in list(c.component_tags):
            c.component_tags = [t for t in c.component_tags if t != TAG]
            print("component untagged", a.get_actor_label(), c.get_name())
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
