import unreal, json
D = unreal.Paths.project_dir() + "Saved/art42/"
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
unreal.SystemLibrary.execute_console_command(w, "slomo 6")
log = open(D + "soak_log.jsonl", "w")
st = {"t": 0.0, "acc": 0.0, "h": None}
DUR = 330.0   # real seconds
def tick(dt):
    try:
        st["t"] += dt; st["acc"] += dt
        if st["acc"] >= 1.0:
            st["acc"] = 0.0
            gm = unreal.GameplayStatics.get_game_mode(w)
            info = {}
            for p in ("Phase", "PlayerScore", "EnemyScore", "RoundNum", "Round", "RoundNumber", "CurrentRound"):
                try: info[p] = str(gm.get_editor_property(p))
                except Exception: pass
            bots = []
            for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Pawn):
                l = a.get_actor_location()
                bots.append([a.get_name(), round(l.x / 100, 1), round(l.y / 100, 1), round(l.z / 100, 1)])
            log.write(json.dumps({"gt": round(unreal.GameplayStatics.get_time_seconds(w), 1), "info": info, "pawns": bots}) + "\n"); log.flush()
        if st["t"] > DUR:
            log.close(); open(D + "soak_done.txt", "w").write("done")
            unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback; open(D + "soak_err.txt", "w").write(traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(st["h"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
print("soak started")
