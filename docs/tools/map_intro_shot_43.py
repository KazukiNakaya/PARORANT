"""紹介画面（鳥瞰、マップ名）の画像を撮る（Step 42c 続き 3）。編集状態で実行（MAP と OUT を先に定義）→ PIE 開始。
PIE の開始から SHOT_AT（実時間秒）に HighResShot（1600x680）で OUT に保存。終わると Saved/art42/intro_done.txt。"""
import unreal
MAP = globals().get("MAP", "map")
OUT = globals().get("OUT", unreal.Paths.project_dir() + "docs/images/%s_intro.png" % MAP)
SHOT_AT = globals().get("SHOT_AT", [3.0])
def W(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
st = {"t": 0.0, "i": 0, "h": None, "on": False}
def tick(dt):
    try:
        w = W()
        if w is None: return
        if not st["on"]:
            if unreal.GameplayStatics.get_player_pawn(w, 0) is None: return
            st["on"] = True
        st["t"] += dt
        if st["i"] < len(SHOT_AT) and st["t"] >= SHOT_AT[st["i"]]:
            f = OUT if len(SHOT_AT) == 1 else OUT.replace(".png", "_%d.png" % st["i"])
            unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1600x680 filename="%s"' % f)
            st["i"] += 1
        if st["i"] >= len(SHOT_AT) and st["t"] > SHOT_AT[-1] + 2:
            open(unreal.Paths.project_dir() + "Saved/art42/intro_done.txt", "w").write("done")
            unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback; open(unreal.Paths.project_dir() + "Saved/art42/intro_err.txt", "w").write(traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(st["h"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
