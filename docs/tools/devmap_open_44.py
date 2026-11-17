"""Step 44 の確認用：タイトルが出たら、開発者用マップ選択のパネルを開く（ToggleDevMap）だけをして、表示の文字を Saved/art43/devmap44_open.log に書く。
設定画面（OpenMenu）は開かない。パネルを開く以外（SetDevMap など）はしない。編集状態で実行 → PIE 開始 → 画面を撮る。"""
import unreal
P = unreal.Paths.project_dir()
LOG = P + "Saved/art43/devmap44_open.log"
open(LOG, "w").write("")
def W(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
st = {"f": 0, "h": None, "done": False}
def L(*a): open(LOG, "a").write(" ".join(str(x) for x in a) + "\n")
def texts(widget, out):
    try:
        for c in widget.get_all_children():
            if isinstance(c, unreal.TextBlock): out.append(c.get_text())
            elif isinstance(c, unreal.PanelWidget): texts(c, out)
            else:
                try:
                    root = c.get_editor_property("widget_tree").get_editor_property("root_widget")
                    if isinstance(root, unreal.TextBlock): out.append(root.get_text())
                    elif root is not None: texts(root, out)
                except Exception: pass
    except Exception: pass
def tick(dt):
    try:
        w = W()
        if w is None: return
        st["f"] += 1
        if st["f"] == 40 and not st["done"]:
            ws = unreal.WidgetLibrary.get_all_widgets_of_class(w, unreal.load_class(None, "/Game/PARORANT/UI/WBP_Title.WBP_Title_C"), False)
            L("world", w.get_name(), "title widgets", len(ws))
            if ws:
                t = ws[0]
                t.call_method("ToggleDevMap")
                L("toggled")
        if st["f"] == 100 and not st["done"]:
            st["done"] = True
            ws = unreal.WidgetLibrary.get_all_widgets_of_class(w, unreal.load_class(None, "/Game/PARORANT/UI/WBP_Title.WBP_Title_C"), False)
            t = ws[0]
            L("DevNow", t.get_editor_property("DevNow").get_text())
            out = []; texts(t.get_editor_property("DevList"), out)
            L("DevList texts", out)
            L("DebugMap", unreal.load_object(None, "/Game/PARORANT/Blueprints/Core/BP_PR_GameInstance").generated_class() and "n/a")
            L("done")
            unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback; L(traceback.format_exc()); unreal.unregister_slate_post_tick_callback(st["h"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
