"""PIE の通し（Step 42c 続き 3）。slomo 6 で DUR 実時間秒のあいだ、1 秒（実時間）ごとに全 Pawn の位置・Team・State・PeekType を Saved/art42/soak43_<MAP>.jsonl へ書く。
プレイヤーを WAYPOINTS（x m, y m）の順に、MOVE_EVERY 実時間秒ごとへ SetActorLocation で動かす（味方 Bot がついて来るかを見る）。
環境音の確認のため、SOUND_AT の時刻に au.DumpActiveSounds を実行（ログ Saved/Logs/PARORANT.log に出る）。
使い方：編集状態で実行 → PIE 開始。終わると Saved/art42/soak43_done.txt。"""
import unreal, json
D = unreal.Paths.project_dir() + "Saved/art42/"
MAP = globals().get("MAP", "map")
WAYPOINTS = globals().get("WAYPOINTS", [])
DUR = globals().get("DUR", 330.0)
MOVE_EVERY = globals().get("MOVE_EVERY", 60.0)
SOUND_AT = [20.0, 120.0, 250.0]
def W(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
log = open(D + "soak43_%s.jsonl" % MAP, "w")
st = {"t": 0.0, "acc": 0.0, "h": None, "started": False, "wp": 0, "next_move": MOVE_EVERY, "snd": 0}
def prop(o, names):
    for n in names:
        try: return str(o.get_editor_property(n))
        except Exception: pass
    return None
def tick(dt):
    try:
        w = W()
        if w is None: return
        if not st["started"]:
            if unreal.GameplayStatics.get_player_pawn(w, 0) is None: return
            st["started"] = True
            unreal.SystemLibrary.execute_console_command(w, "slomo 6")
        st["t"] += dt; st["acc"] += dt
        if st["snd"] < len(SOUND_AT) and st["t"] >= SOUND_AT[st["snd"]]:
            unreal.SystemLibrary.execute_console_command(w, "au.DumpActiveSounds"); st["snd"] += 1
            log.write(json.dumps({"dump_sounds_at": round(st["t"], 1)}) + "\n")
        if st["t"] >= st["next_move"] and st["wp"] < len(WAYPOINTS):
            me = unreal.GameplayStatics.get_player_pawn(w, 0)
            if me:
                x, y = WAYPOINTS[st["wp"]]
                me.set_actor_location(unreal.Vector(x * 100, y * 100, 120), False, True)
                log.write(json.dumps({"moved_player_to": [x, y], "at": round(st["t"], 1)}) + "\n")
            st["wp"] += 1; st["next_move"] += MOVE_EVERY
        if st["acc"] >= 1.0:
            st["acc"] = 0.0
            gm = unreal.GameplayStatics.get_game_mode(w)
            info = {}
            for p in ("Phase", "RoundNum", "Round", "PlayerScore", "EnemyScore"):
                v = prop(gm, [p, p[0].lower() + p[1:]]) if gm else None
                if v is not None: info[p] = v
            ps = []
            for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Pawn):
                l = a.get_actor_location()
                c = None
                try: c = a.get_controller()
                except Exception: pass
                ps.append({"n": a.get_name(), "p": [round(l.x / 100, 1), round(l.y / 100, 1), round(l.z / 100, 1)],
                           "team": prop(a, ["Team", "team"]), "state": prop(c, ["State", "state"]) if c else None,
                           "peek": prop(c, ["PeekType", "peek_type"]) if c else None, "hp": prop(a, ["Health", "health"])})
            log.write(json.dumps({"gt": round(unreal.GameplayStatics.get_time_seconds(w), 1), "info": info, "pawns": ps}, ensure_ascii=False) + "\n"); log.flush()
        if st["t"] > DUR:
            log.close(); open(D + "soak43_done.txt", "w").write("done")
            unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception:
        import traceback; open(D + "soak43_err.txt", "w").write(traceback.format_exc())
        unreal.unregister_slate_post_tick_callback(st["h"])
st["h"] = unreal.register_slate_post_tick_callback(tick)
print("soak43 registered", MAP, len(WAYPOINTS))
