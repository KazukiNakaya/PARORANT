"""Step 44 の確認用：BP_PR_GameInstance の bSkipTitle（と DebugMap）を PIE 用にメモリ上だけ変える（保存しない）。
SKIP と MAP を先に定義して exec する。SKIP=False, MAP="" で既定へ戻す。"""
import unreal
bp = unreal.load_asset("/Game/PARORANT/Blueprints/Core/BP_PR_GameInstance")
cdo = unreal.get_default_object(bp.generated_class())
cdo.set_editor_property("bSkipTitle", globals().get("SKIP", False))
cdo.set_editor_property("DebugMap", globals().get("MAP_", ""))
print("GI bSkipTitle", cdo.get_editor_property("bSkipTitle"), "DebugMap", repr(cdo.get_editor_property("DebugMap")))
