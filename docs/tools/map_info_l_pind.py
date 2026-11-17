"""PARORANT L_Pind のマップ情報（Step 42a、docs/29_pind_tropical.md §2.3）。環境音の取り込みと設定、紹介画面のカメラ、場所の名前。

L_Pind を開いて Unreal の Python で実行する（L_Pind 以外では止まる）。何度実行しても同じ結果になる。
  - SourceAudio/AMB_Pind.wav（SourceAudio/gen_ambience_pind.py で作る）を /Game/PARORANT/Audio/AMB_Pind に取り込み、ループにする
  - BP_PR_MapInfo（MapInfo）の AmbSound = AMB_Pind、AmbVolume = 0.25（CANAL と同じ）、IntroCamLoc / IntroCamRot（海が入る斜めの鳥瞰）
  - BP_AreaName の DisplayName を絵に合う名前に。位置と範囲（Box）、Area、PredictSite は変えない
表示名（MapName）は PIND のまま。
"""
import unreal

_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()
if not _world.startswith("/Game/PARORANT/Maps/L_Pind"):
    raise RuntimeError("L_Pind を開いてから実行してください（今のレベル: %s）" % _world)

INTRO_LOC = unreal.Vector(-7000.0, 0.0, 4800.0)
INTRO_ROT = unreal.Rotator(0.0, -33.0, 0.0)   # (roll, pitch, yaw)。南の海から北へ、砂浜と海が入る
AMB_VOLUME = 0.25
AREA_NAMES = {   # ラベル → 表示名。A・B・ミッド・スポーンの言葉は残し（Bot のチャットや HUD で「どこか」が分かるように）、絵に合う言葉を添える
    "Area_AtkSpawn_A": "攻撃スポーン（桟橋）", "Area_AtkSpawn_Mid": "攻撃スポーン（桟橋）", "Area_AtkSpawn_B": "攻撃スポーン（桟橋）",
    "Area_ALane": "A通路（石畳）", "Area_BLane": "B通路（石畳）",
    "Area_AMain": "Aメイン（砦の門）", "Area_BMain": "Bメイン（砦の門）",
    "Area_ASite": "Aサイト（石畳の広場）", "Area_BSite": "Bサイト（甲板）",
    "Area_AShort": "Aショート（路地）", "Area_BShort": "Bショート（路地）",
    "Area_MidLane": "ミッド通路（港の道）", "Area_Mid": "ミッド（赤土の広場）", "Area_MidTop": "ミッド奥",
    "Area_DefSpawn": "防衛スポーン（中庭）", "Area_DefA": "防衛側Aルート", "Area_DefB": "防衛側Bルート",
}

ea = unreal.EditorAssetLibrary
AUDIO = "/Game/PARORANT/Audio/AMB_Pind"
src = unreal.Paths.project_dir() + "SourceAudio/AMB_Pind.wav"
task = unreal.AssetImportTask()
task.set_editor_property("filename", src)
task.set_editor_property("destination_path", "/Game/PARORANT/Audio")
task.set_editor_property("destination_name", "AMB_Pind")
task.set_editor_property("replace_existing", True)
task.set_editor_property("automated", True)
task.set_editor_property("save", True)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
snd = ea.load_asset(AUDIO)
snd.set_editor_property("looping", True)
ea.save_loaded_asset(snd)
print("AMB_Pind", snd.get_class().get_name(), "duration", snd.get_editor_property("duration"), "looping", snd.get_editor_property("looping"))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    lb = a.get_actor_label()
    if lb == "MapInfo":
        a.set_editor_property("AmbSound", snd)
        a.set_editor_property("AmbVolume", AMB_VOLUME)
        a.set_editor_property("IntroCamLoc", INTRO_LOC)
        a.set_editor_property("IntroCamRot", INTRO_ROT)
        print("MapInfo MapName", a.get_editor_property("MapName"), "Amb", a.get_editor_property("AmbSound").get_name(), a.get_editor_property("AmbVolume"))
    elif lb in AREA_NAMES:
        old = a.get_editor_property("DisplayName")
        a.set_editor_property("DisplayName", AREA_NAMES[lb])
        print("AREA", lb, "|", old, "->", a.get_editor_property("DisplayName"))
