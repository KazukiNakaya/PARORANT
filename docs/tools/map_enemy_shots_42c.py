import unreal, json, math
D = unreal.Paths.project_dir()
OUT = D + "docs/images/"
SHOTS = json.load(open(D + "Saved/art42/shots.json"))   # [{name, cam:[x,y,yaw], enemy:[x,y], ally:[x,y]?}] m
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pawns = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Pawn)
names = sorted(p.get_name() for p in pawns)
enemies = sorted([p for p in pawns if "Enemy" in p.get_name()], key=lambda a: a.get_name())
allies = sorted([p for p in pawns if "Ally" in p.get_name() or "Friend" in p.get_name()], key=lambda a: a.get_name())
me = unreal.GameplayStatics.get_player_pawn(w, 0)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
log = open(D + "Saved/art42/shots_log.txt", "w")
log.write("pawns %s\nme %s\n" % (names, me.get_name() if me else None))
def freeze(b):
    b.set_actor_tick_enabled(False)
    try:
        c = b.get_controller()
        if c: c.set_actor_tick_enabled(False)
    except Exception: pass
    try:
        b.custom_time_dilation = 0.0001
    except Exception: pass
for b in enemies + allies:
    freeze(b)
FAR = unreal.Vector(0, 0, 90000)
st = {"i": 0, "t": 0, "h": None, "stage": 0}
def place(s):
    cx, cy, yaw = s["cam"]
    for k, b in enumerate(enemies + allies):
        b.set_actor_location(unreal.Vector(30000 + 300 * k, 30000, 5000), False, True)
    me.set_actor_location(unreal.Vector(cx * 100, cy * 100, 100), False, True)
    pc.set_control_rotation(unreal.Rotator(0, yaw, 0))
    for key, lst in (("enemy", enemies), ("ally", allies)):
        if key in s and lst:
            ex, ey = s[key]
            lst[0].set_actor_location(unreal.Vector(ex * 100, ey * 100, 100), False, True)
            lst[0].set_actor_rotation(unreal.Rotator(0, yaw + 180 + s.get("turn", 0), 0), False)
            freeze(lst[0])
def rescan():
    global pawns, enemies, allies
    pawns = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Pawn)
    enemies = sorted([p for p in pawns if "Enemy" in p.get_name()], key=lambda a: a.get_name())
    allies = sorted([p for p in pawns if "Ally" in p.get_name() or "Friend" in p.get_name()], key=lambda a: a.get_name())
    for b in enemies + allies:
        freeze(b)
st["wait"] = 0
def tick(dt):
    try:
        if not enemies:
            st["wait"] += 1
            if st["wait"] % 30 == 0:
                rescan()
                log.write("scan %d pawns %s\n" % (st["wait"], sorted(p.get_name() for p in pawns))); log.flush()
            if st["wait"] > 3000:
                log.write("no bots\ndone\n"); log.close(); unreal.unregister_slate_post_tick_callback(st["h"])
            return
        if st["i"] >= len(SHOTS):
            unreal.unregister_slate_post_tick_callback(st["h"]); log.write("done\n"); log.close(); return
        s = SHOTS[st["i"]]
        st["t"] += 1
        if st["stage"] == 0:
            place(s); st["stage"] = 1; st["t"] = 0
        elif st["stage"] == 1 and st["t"] > 20:
            place(s)
            unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1600x680 filename="%s%s.png"' % (OUT, s["name"]))
            log.write("shot %s\n" % s["name"]); log.flush()
            st["stage"] = 2; st["t"] = 0
        elif st["stage"] == 2 and st["t"] > 20:
            st["i"] += 1; st["stage"] = 0
    except Exception:
        import traceback; log.write(traceback.format_exc()); log.close()
        unreal.unregister_slate_post_tick_callback(st["h"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
print("shots started", len(SHOTS), "enemies", len(enemies), "allies", len(allies))
