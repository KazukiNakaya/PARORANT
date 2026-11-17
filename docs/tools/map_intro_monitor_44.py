"""Step 44 の確認用：PIE 中、1 秒ごとに IntroOnly の物の Hidden の数、IntroHide の物の数、フレーム時間の平均（ms）を Saved/art42/intro44_monitor_<MAP>.log に書く。
編集状態で実行（MAPNAME と SECS を先に定義）→ PIE 開始。終わると同じログの末尾に done。"""
import unreal
P = unreal.Paths.project_dir()
MAPNAME = globals().get("MAPNAME", "map"); SECS = globals().get("SECS", 40)
LOG = P + "Saved/art42/intro44_monitor_%s.log" % MAPNAME
open(LOG, "w").write("")
def W(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
st = {"t": 0.0, "acc": 0.0, "n": 0, "h": None, "on": False, "last": 0}
def tick(dt):
    try:
        w = W()
        if w is None: return
        if not st["on"]:
            if unreal.GameplayStatics.get_player_pawn(w, 0) is None: return
            st["on"] = True
        st["t"] += dt; st["acc"] += dt; st["n"] += 1
        if st["t"] - st["last"] >= 1.0:
            st["last"] = st["t"]
            only = unreal.GameplayStatics.get_all_actors_with_tag(w, "IntroOnly")
            hid = sum(1 for a in only if a.is_hidden_ed() is None) if False else sum(1 for a in only if a.get_editor_property("hidden"))
            ih = unreal.GameplayStatics.get_all_actors_with_tag(w, "IntroHide")
            ihh = sum(1 for a in ih if a.get_editor_property("hidden"))
            pc = unreal.GameplayStatics.get_player_controller(w, 0)
            vt = pc.get_view_target().get_class().get_name() if pc else "?"
            open(LOG, "a").write("t=%.1f IntroOnly total=%d hidden=%d | IntroHide total=%d hidden=%d | viewtarget=%s | avg_ms=%.2f fps=%.1f\n" % (st["t"], len(only), hid, len(ih), ihh, vt, st["acc"] / st["n"] * 1000, st["n"] / st["acc"]))
            st["acc"] = 0.0; st["n"] = 0
        if st["t"] > SECS:
            open(LOG, "a").write("done\n")
            unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback; open(LOG, "a").write(traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(st["h"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
