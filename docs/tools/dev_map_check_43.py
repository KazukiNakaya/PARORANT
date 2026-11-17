"""開発者用マップ選択の確認（Step 43）。編集状態で実行（MODE を先に定義）→ PIE 開始。結果は Saved/art43/devmap_<MODE>.log。
MODE="ui"：ToggleDevMap／SetDevMap／表示／PickMap 20・200 回／OpenMenu 前後の CanUseDevKey とフォーカスを確認し、画像を docs/images/step43_*.png に保存。
MODE="play_L_Pind" / "play_L_Canal"：固定 → OnPlay → 開いたマップ名を記録。"""
import unreal, json
P = unreal.Paths.project_dir()
MODE = globals().get("MODE", "ui")
LOG = open(P + "Saved/art43/devmap_%s.log" % MODE, "w", encoding="utf-8")
def L(*a):
    LOG.write(" ".join(str(x) for x in a) + "\n"); LOG.flush()
def W(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
st = {"f": 0, "h": None, "w": None, "gi": None, "pc": None, "step": 0, "wait": 0}
def title(w):
    ws = unreal.WidgetLibrary.get_all_widgets_of_class(w, unreal.load_class(None, "/Game/PARORANT/UI/WBP_Title.WBP_Title_C"), False)
    return ws[0] if ws else None
def gv(o, n):
    try: return o.get_editor_property(n)
    except Exception as e: return "ERR:%s" % e
def vis(t, n):
    try: return str(gv(t, n).get_visibility())
    except Exception as e: return "ERR:%s" % e
def state(t, gi, tag):
    L(tag, "DebugMap=%s" % gv(gi, "DebugMap"), "panel=%s" % vis(t, "DevPanel"), "badge=%s" % vis(t, "DevBadge"),
      "now=%s" % gv(t, "DevNow").get_text() if not isinstance(gv(t, "DevNow"), str) else "now=ERR",
      "badgeText=%s" % (gv(t, "DevBadge").get_text() if not isinstance(gv(t, "DevBadge"), str) else "ERR"),
      "items=%s" % (len(gv(t, "DevList").get_all_children()) if not isinstance(gv(t, "DevList"), str) else "ERR"))
def focus(t, tag):
    r = []
    for m in ("has_keyboard_focus", "has_any_user_focus", "has_focused_descendants", "has_user_focus_for_descendants"):
        try: r.append("%s=%s" % (m, getattr(t, m)()))
        except Exception as e: r.append("%s=n/a" % m)
    L(tag, " ".join(r), [m for m in dir(t) if "focus" in m and not m.startswith("_")][:12])
def shot(w, name):
    # UMG（タイトルの画面）も写すため Shot ShowUI を使う。画像は Saved/Screenshots/ に name 付きで出る
    unreal.SystemLibrary.execute_console_command(w, 'Shot ShowUI name=%s' % name.replace(".png", ""))
def tick(dt):
    try:
        w = W()
        if w is None: return
        st["f"] += 1
        if st["f"] < 90: return
        if st["wait"] > 0:
            st["wait"] -= 1; return
        t = title(w) if MODE == "ui" else None
        gi = unreal.GameplayStatics.get_game_instance(w)
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        s = st["step"]
        if MODE != "ui":
            if s == 0:
                tt = title(w)
                L("world", w.get_name(), "title", bool(tt))
                tt.call_method("SetDevMap", (MODE.replace("play_", ""),))
                L("pinned DebugMap=%s" % gv(gi, "DebugMap"))
                tt.call_method("OnPlay"); st["step"] = 1; st["wait"] = 240
            elif s == 1:
                L("after OnPlay world", w.get_name(), "DebugMap=%s" % gv(gi, "DebugMap"), "bSkipTitle=%s" % gv(gi, "bSkipTitle"))
                st["step"] = 2
            else:
                LOG.close(); open(P + "Saved/art43/devmap_%s.done" % MODE, "w").write("done"); unreal.unregister_slate_post_tick_callback(st["h"])
            return
        if s == 0:
            L("world", w.get_name(), "title", bool(t)); state(t, gi, "initial"); focus(t, "initial")
            L("CanUseDevKey initial", t.call_method("CanUseDevKey"))
            t.call_method("ToggleDevMap"); st["step"] = 1; st["wait"] = 20
        elif s == 1:
            state(t, gi, "after Toggle (open)"); shot(w, "step43_title_panel.png"); st["step"] = 2; st["wait"] = 40
        elif s == 2:
            t.call_method("ToggleDevMap"); state(t, gi, "after Toggle (close)")
            t.call_method("ToggleDevMap"); state(t, gi, "after Toggle (open again)")
            t.call_method("SetDevMap", ("L_Pind",)); state(t, gi, "after SetDevMap(L_Pind)"); focus(t, "after SetDevMap")
            st["step"] = 3; st["wait"] = 20
        elif s == 3:
            shot(w, "step43_title_pinned.png"); st["step"] = 4; st["wait"] = 40
        elif s == 4:
            picks = [str(gi.call_method("PickMap")) for _ in range(20)]
            L("PickMap x20 (pinned L_Pind)", {k: picks.count(k) for k in set(picks)})
            t.call_method("SetDevMap", ("L_Canal",)); state(t, gi, "after SetDevMap(L_Canal)")
            picks = [str(gi.call_method("PickMap")) for _ in range(20)]
            L("PickMap x20 (pinned L_Canal)", {k: picks.count(k) for k in set(picks)})
            t.call_method("SetDevMap", ("None",)); state(t, gi, "after SetDevMap(None)")
            picks = [str(gi.call_method("PickMap")) for _ in range(200)]
            run = best = 1
            for i in range(1, len(picks)):
                run = run + 1 if picks[i] == picks[i - 1] else 1
                best = max(best, run)
            L("PickMap x200 (random)", {k: picks.count(k) for k in set(picks)}, "max_run=%d" % best)
            st["step"] = 5
        elif s == 5:
            L("CanUseDevKey before OpenMenu", t.call_method("CanUseDevKey"))
            pc.call_method("OpenMenu"); st["step"] = 6; st["wait"] = 20
        elif s == 6:
            L("CanUseDevKey while menu open", t.call_method("CanUseDevKey")); focus(t, "menu open")
            pc.call_method("CloseMenu"); st["step"] = 7; st["wait"] = 40
        elif s == 7:
            L("CanUseDevKey after CloseMenu", t.call_method("CanUseDevKey")); focus(t, "after CloseMenu (Tick refocus)")
            st["step"] = 8; st["wait"] = 60
        else:
            focus(t, "later"); state(t, gi, "final")
            LOG.close(); open(P + "Saved/art43/devmap_ui.done", "w").write("done"); unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback; L(traceback.format_exc()); LOG.close()
        unreal.unregister_slate_post_tick_callback(st["h"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
