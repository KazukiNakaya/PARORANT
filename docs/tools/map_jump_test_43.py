"""角の小物にジャンプで乗れるか、横をすり抜けられるか、押し込んでも引っかからないかを、PIE の中で測る（Step 42c 続き）。

使い方：L_Pind か L_Canal を開いた状態でこのスクリプトを実行（編集状態）→ PIE を開始。Tick のコールバックが順に試して
Saved/art42/jump_log.jsonl に書き、終わると Saved/art42/jump_done.txt を作る。タグは PindDeco／CanalDeco（小物すべて。樽を含む）。
各小物について、近づける向き（地面が小物の根もとと同じ高さで、壁がない）を 1 つ選び、
  jump  小物の手前 130cm（なければ 60cm）の地面に置き、JumpZVelocity で LaunchCharacter（小物に向かって 300・150・0・450cm/s を足し、前の入力も押し続ける。乗れたら残りは省略）。
        2.1 秒後に足もとの真下が小物なら「乗れた」。最高点の高さも記録
  push  100cm 離れた所から小物に向かって 2 秒歩く（add_movement_input）。止まった距離を記録（小物に当たって止まる＝引っかからず止まるのが正常）
他の Pawn（Bot）は遠くに置いて動きを止める（プレイヤーが撃たれないように）。
"""
import unreal, json, math
D = unreal.Paths.project_dir() + "Saved/art42/"
TAG = globals().get("DECO_TAG", None)
def W():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
log = open(D + "jump_log.jsonl", "w")
st = {"h": None, "stage": "init", "n": 0, "pi": 0, "di": 0, "mode": 0, "wait": 0, "props": None, "me": None, "frames": 0, "maxz": 0}
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
def L(o):
    log.write(json.dumps(o, ensure_ascii=False) + "\n"); log.flush()
def tr(a, b, ign):
    h = unreal.SystemLibrary.line_trace_single(W(), a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ign, unreal.DrawDebugTrace.NONE, True)
    return h
def fr(b):
    b.set_actor_tick_enabled(False)
    try:
        c = b.get_controller()
        if c: c.set_actor_tick_enabled(False)
    except Exception: pass
    try: b.custom_time_dilation = 0.0001
    except Exception: pass
def init():
    if W() is None: return False
    me = unreal.GameplayStatics.get_player_pawn(W(), 0)
    if me is None: return False
    st["me"] = me
    for p in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.Pawn):
        if p != me:
            p.set_actor_location(unreal.Vector(30000, 30000, 5000), False, True)
            fr(p)
    props = []
    for a in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.StaticMeshActor):
        tg = [str(t) for t in a.tags]
        if ("PindDeco" in tg or "CanalDeco" in tg):
            c = a.get_component_by_class(unreal.StaticMeshComponent)
            props.append((a, c.static_mesh.get_name()))
    props.sort(key=lambda x: x[0].get_name())
    st["props"] = props
    cm = me.character_movement
    L({"info": "init", "n": len(props), "jumpz": cm.jump_z_velocity, "gravity_scale": cm.gravity_scale, "max_walk": cm.max_walk_speed,
       "step": cm.max_step_height, "cap_r": me.capsule_component.get_scaled_capsule_radius(), "cap_hh": me.capsule_component.get_scaled_capsule_half_height(),
       "mode": str(cm.movement_mode)})
    return True
def geom(a, name):
    o, e = a.get_actor_bounds(True)   # 当たり判定のある部分だけ
    c = a.get_actor_location()
    return c, max(e.x, e.y), e
def valid_dir(a, name, d, s0):
    """この向きから近づけるか：出発点の地面が小物の根もとと同じ高さ（±12cm）で、出発点から小物までの間にカプセル高さの壁がない"""
    me = st["me"]
    c, r, e = geom(a, name)
    cap_r = me.capsule_component.get_scaled_capsule_radius()
    dx, dy = DIRS[d]
    sx, sy = c.x + dx * (r + cap_r + s0), c.y + dy * (r + cap_r + s0)
    base = tr(unreal.Vector(c.x, c.y, c.z + 300), unreal.Vector(c.x, c.y, c.z - 100), [])
    g = tr(unreal.Vector(sx, sy, c.z + 300), unreal.Vector(sx, sy, c.z - 200), [a, me])
    if g is None: return None
    gz = g.to_tuple()[4].z
    if abs(gz - c.z) > 12: return None
    for z in (20, 100, 180):
        for k in (-1, 0, 1):
            ox, oy = -dy * k * cap_r * 0.8, dx * k * cap_r * 0.8
            h = tr(unreal.Vector(sx + ox, sy + oy, gz + z), unreal.Vector(c.x + dx * r * 1.0 + ox, c.y + dy * r * 1.0 + oy, gz + z), [a, me])
            if h is not None and h.to_tuple()[0]: return None
            h = tr(unreal.Vector(sx + ox, sy + oy, gz + z), unreal.Vector(sx - dx * 150 + ox, sy - dy * 150 + oy, gz + z), [a, me])
            if h is not None and h.to_tuple()[0]: return None
    return (sx, sy, gz)
def setup_trial(a, name, d, kind, v, s0):
    me = st["me"]
    c, r, e = geom(a, name)
    hh = me.capsule_component.get_scaled_capsule_half_height()
    dx, dy = DIRS[d]
    sx, sy, gz = valid_dir(a, name, d, s0)
    me.set_actor_location(unreal.Vector(sx, sy, gz + hh + 3), False, True)
    me.character_movement.stop_movement_immediately()
    st["dir"] = (-dx, -dy); st["t"] = 0.0; st["maxz"] = 0.0; st["gz"] = gz
    st["a"] = a; st["name"] = name; st["kind"] = kind; st["d"] = d; st["r"] = r; st["v"] = v; st["s0"] = s0; st["phase"] = "settle"
def below(me):
    l = me.get_actor_location()
    hh = me.capsule_component.get_scaled_capsule_half_height()
    h = tr(l, unreal.Vector(l.x, l.y, l.z - hh - 12), [me])
    if h is None: return None
    t = h.to_tuple()
    return t[9].get_name() if len(t) > 9 and t[9] is not None else "hit"
def tick(dt):
    try:
        if st["stage"] == "init":
            st["wait"] += 1
            if st["wait"] % 20 == 0 and init():
                st["stage"] = "run"; st["trial"] = None
            if st["wait"] > 200000:
                L({"info": "no pawn"}); stop()
            return
        me = st["me"]
        if st["stage"] == "run":
            if st["trial"] is None:
                nxt_trial()
                return
            st["t"] += dt
            ph = st["phase"]
            if ph == "settle":
                if st["t"] > 0.6:
                    st["t"] = 0.0
                    l = me.get_actor_location(); st["l0"] = (l.x, l.y, l.z)
                    tx, ty = st["dir"]
                    if st["kind"] == "jump":
                        me.launch_character(unreal.Vector(tx * st["v"], ty * st["v"], me.character_movement.jump_z_velocity), True, True)
                    st["phase"] = "go"
                return
            if ph == "go":
                l = me.get_actor_location()
                st["maxz"] = max(st["maxz"], l.z - st["l0"][2])
                if st["kind"] in ("push", "jump"):   # ジャンプ中も前を押し続ける（この設定では空中の横方向は減速が強く、入力なしだと 1m も進まない）
                    tx, ty = st["dir"]
                    me.add_movement_input(unreal.Vector(tx, ty, 0), 1.0, False)
                if st["t"] > (1.5 if st["kind"] == "jump" else 1.5):
                    st["t"] = 0.0; st["phase"] = "rest"
                return
            if ph == "rest":
                if st["t"] > 0.6:
                    finish()
                return
    except Exception:
        import traceback; L({"err": traceback.format_exc()}); stop()
def nxt_trial():
    # 小物ごとに：有効な向きを探し、jump を v = 200・300・400 で（乗れたら以降は省略）、push を 1 回
    while st["pi"] < len(st["props"]):
        a, name = st["props"][st["pi"]]
        if "plan" not in st or st["plan_pi"] != st["pi"]:
            dd = None
            for s0 in (130, 60, 25):
                for d in range(4):
                    if valid_dir(a, name, d, s0) is not None:
                        dd = (d, s0); break
                if dd: break
            st["plan_pi"] = st["pi"]
            st["plan"] = [] if dd is None else [("jump", 300, dd), ("jump", 150, dd), ("jump", 0, dd), ("jump", 450, dd), ("push", 0, (dd[0], 100))]
            st["won"] = False
            if dd is None:
                L({"prop": a.get_name(), "mesh": name, "kind": "none", "note": "近づける向きなし（壁・段差）"})
        while st["plan"]:
            kind, v, (d, s0) = st["plan"].pop(0)
            if kind == "jump" and st["won"]:
                continue
            setup_trial(a, name, d, kind, v, s0)
            st["trial"] = 1
            return
        st["pi"] += 1
    L({"info": "done"}); stop()
def finish():
    me = st["me"]
    l = me.get_actor_location()
    l0 = st["l0"]
    hh = me.capsule_component.get_scaled_capsule_half_height()
    rec = {"prop": st["a"].get_name(), "mesh": st["name"], "kind": st["kind"], "dir": st["d"], "v": st["v"], "s0": st["s0"],
           "foot_z_gain_cm": round(l.z - hh - st["gz"], 1), "maxz_gain_cm": round(st["maxz"], 1), "below": below(me),
           "moved_cm": round(math.hypot(l.x - l0[0], l.y - l0[1]), 1), "r": round(st["r"], 1)}
    rec["on_prop"] = rec["below"] == st["a"].get_name()
    if rec["on_prop"] and st["kind"] == "jump":
        st["won"] = True
    L(rec)
    st["trial"] = None
def stop():
    try: unreal.unregister_slate_post_tick_callback(st["h"])
    except Exception: pass
    log.close(); open(D + "jump_done.txt", "w").write("done")
st["h"] = unreal.register_slate_post_tick_callback(tick)
print("jump test registered")
