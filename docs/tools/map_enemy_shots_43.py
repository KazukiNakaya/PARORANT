"""敵・味方 Bot の見え方の撮影（Step 42c 続き 3）。編集状態で実行（SHOTS_JSON は Saved/art42/shots43.json）→ PIE 開始。
42c の map_enemy_shots_42c.py からの変更：
  - Tick を止めない（止めると置き直しでアニメの姿勢が壊れ、敵が逆さまに写った）。CustomTimeDilation を 0.02 にして動きを遅くし、AIController の移動を止める
  - 味方は Team==1 の BP_PR_Bot（名前に Ally を含まない）、敵は名前に EnemyBot を含むもの
  - プレイヤー・敵を置き直したあと 30 フレーム待ってから撮る（姿勢が落ち着くのを待つ）。撮影後、敵は遠くへ戻す
撮影は HighResShot 1600x680。SHOTS = [{name, cam:[x,y,yaw], enemy:[x,y]?, ally:[x,y]?}]（m）。"""
import unreal, json
D = unreal.Paths.project_dir()
OUT = D + "docs/images/"
SHOTS = json.load(open(D + "Saved/art42/shots43.json"))
def W(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
log = open(D + "Saved/art42/shots43_log.txt", "w")
st = {"i": 0, "t": 0, "stage": 0, "h": None, "on": False, "enemies": [], "allies": [], "me": None, "pc": None}
FAR = lambda k: unreal.Vector(30000 + 300 * k, 30000, 5000)
def scan(w):
    me = unreal.GameplayStatics.get_player_pawn(w, 0)
    pawns = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Pawn)
    en = sorted([p for p in pawns if "EnemyBot" in p.get_name()], key=lambda a: a.get_name())
    al = sorted([p for p in pawns if p != me and "EnemyBot" not in p.get_name() and "Bot" in p.get_name()], key=lambda a: a.get_name())
    return me, en, al
def slow(b):
    try: b.custom_time_dilation = 0.02
    except Exception: pass
    try:
        c = b.get_controller()
        if c: c.stop_movement()
    except Exception: pass
def place(w, s):
    me, en, al = st["me"], st["enemies"], st["allies"]
    cx, cy, yaw = s["cam"]
    for k, b in enumerate(en + al):
        b.set_actor_location(FAR(k), False, True)
    me.set_actor_location(unreal.Vector(cx * 100, cy * 100, 120), False, True)
    st["pc"].set_control_rotation(unreal.Rotator(0, yaw, 0))
    for key, lst in (("enemy", en), ("ally", al)):
        if key in s and lst:
            ex, ey = s[key]
            b = lst[0]
            b.set_actor_location(unreal.Vector(ex * 100, ey * 100, 100), False, True)
            b.set_actor_rotation(unreal.Rotator(0, yaw + 180 + s.get("turn", 0), 0), False)
            slow(b)
def tick(dt):
    try:
        w = W()
        if w is None: return
        if not st["on"]:
            me, en, al = scan(w)
            if me is None or not en or not al: return
            st.update(me=me, enemies=en, allies=al, pc=unreal.GameplayStatics.get_player_controller(w, 0), on=True)
            for b in en + al: slow(b)
            log.write("enemies %s allies %s\n" % ([b.get_name() for b in en], [b.get_name() for b in al])); log.flush()
            return
        if st["i"] >= len(SHOTS):
            unreal.unregister_slate_post_tick_callback(st["h"]); log.write("done\n"); log.close()
            open(D + "Saved/art42/shots43_done.txt", "w").write("done"); return
        s = SHOTS[st["i"]]
        st["t"] += 1
        if st["stage"] == 0:
            place(w, s); st["stage"] = 1; st["t"] = 0
        elif st["stage"] == 1 and st["t"] % 10 == 0 and st["t"] < 30:
            place(w, s)
        elif st["stage"] == 1 and st["t"] >= 30:
            unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1600x680 filename="%s%s.png"' % (OUT, s["name"]))
            log.write("shot %s\n" % s["name"]); log.flush(); st["stage"] = 2; st["t"] = 0
        elif st["stage"] == 2 and st["t"] > 20:
            st["i"] += 1; st["stage"] = 0
    except Exception:
        import traceback; log.write(traceback.format_exc()); log.close()
        unreal.unregister_slate_post_tick_callback(st["h"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
print("shots43 registered", len(SHOTS))
