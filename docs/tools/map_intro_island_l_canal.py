"""Step 44 B: L_Canal の紹介画面を「紫の空、雲の海に浮く島」にする（docs/31）。何度実行しても同じ結果。
L_Canal を開いて Unreal の Python で実行（L_Canal 以外では止まる）。先に intro_assets_44.py で素材とメッシュを作っておく。
  - タグ IntroIsland の物をすべて消してから作り直す。置く物はすべて タグ IntroOnly + IntroIsland、当たり判定なし、影なし、ナビに影響なし、
    Hidden In Game = true（SetIntroHide(true→false) の間だけ表示。GameMode の SetIntroHide が IntroOnly を切り替える）
  - 空の幕 Intro_Sky：球（半径 1500m、内側（裏面）だけ描く素材）。素材 M_IntroSky
  - 地面の枠 Intro_Ground_*：外壁の外側、場外の建物の下に地面（上面 z=-2、幅 約 19〜21m）。島の本体 Intro_Island：逆さの岩（上面 z=-300）
  - 雲 Intro_Cloud_*：雲の海（島の下 z=-14000 付近の層）、島の縁にかかる塊、遠くの雲
  - 遠くの小島 Intro_Islet_*：島を縮めたものに小さい家
  - 屋根：A_Roof と ISM_roof の IntroHide タグを外す（紹介画面でも屋根を見せる）
  - MapInfo の IntroCamLoc / IntroCamRot を斜めに
形・当たり判定・光は変えない（既存のアクタには、屋根のタグ以外は触らない）。"""
import math, random
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not world.get_path_name().startswith("/Game/PARORANT/Maps/L_Canal"):
    raise RuntimeError("L_Canal を開いてから実行してください（今: %s）" % world.get_path_name())

CAM_LOC = unreal.Vector(*globals().get("CAM_LOC_V", (-14200.0, -7800.0, 6000.0)))
CAM_ROT = unreal.Rotator(0.0, *globals().get("CAM_PY", (-22.0, 19.0)))   # (roll, pitch, yaw)
TAGS = [unreal.Name("IntroOnly"), unreal.Name("IntroIsland")]
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ART, MAT = "/Game/PARORANT/Art/Intro/", "/Game/PARORANT/Materials/"
CUBE, SPHERE, CONE = "/Engine/BasicShapes/Cube", "/Engine/BasicShapes/Sphere", "/Engine/BasicShapes/Cone"

# 1. 前回の物を消す
for a in EAS.get_all_level_actors():
    if unreal.Name("IntroIsland") in list(a.tags):
        EAS.destroy_actor(a)

made = []
def put(label, mesh, loc, scale, mat=None, rot=(0, 0, 0), mats=None, sort=None):
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator(*rot))
    a.set_actor_label(label)
    a.set_actor_scale3d(unreal.Vector(*scale))
    a.set_folder_path("Intro")
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset(mesh))
    if mats:
        for i, m in enumerate(mats):
            c.set_material(i, unreal.load_asset(m))
    elif mat:
        c.set_material(0, unreal.load_asset(mat))
    c.set_collision_profile_name("NoCollision")
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    c.set_editor_property("can_ever_affect_navigation", False)
    c.set_cast_shadow(False)
    c.set_editor_property("affect_distance_field_lighting", False)
    c.set_editor_property("affect_dynamic_indirect_lighting", False)
    c.set_editor_property("visible_in_ray_tracing", False)
    if sort is not None:
        c.set_editor_property("translucency_sort_priority", sort)
    a.tags = TAGS
    a.set_actor_hidden_in_game(True)
    made.append(a)
    return a

# 2. 空の幕
put("Intro_Sky", SPHERE, (0, 100, 0), (3000, 3000, 3000), MAT + "M_IntroSky", sort=-100)

# 3. 島：地面の枠（外壁 ±3700 の外側、場外の建物の下）と、島の本体（逆さの岩）
X0, X1, Y0, Y1 = 3700.0, 5600.0, 3700.0, 5600.0   # 枠の内側と外側（y は中心 100 からの対称ではなく、下で中心 100 を足す）
ZT, ZB = -2.0, -300.0
G = MAT + "M_IntroGround"
def box(label, cx, cy, sx, sy):
    put(label, CUBE, (cx, cy, (ZT + ZB) / 2), (sx / 100.0, sy / 100.0, (ZT - ZB) / 100.0), G)
box("Intro_Ground_N", (X0 + X1) / 2, 100, X1 - X0, 2 * Y1 + (Y1 - Y0) * 0 + 0)
box("Intro_Ground_S", -(X0 + X1) / 2, 100, X1 - X0, 2 * Y1)
box("Intro_Ground_E", 0, 100 + (Y0 + Y1) / 2, 2 * X0, Y1 - Y0)
box("Intro_Ground_W", 0, 100 - (Y0 + Y1) / 2, 2 * X0, Y1 - Y0)
put("Intro_Island", ART + "SM_IntroIsland", (0, 100, ZB), (1, 1, 1), mats=[G, MAT + "M_IntroRock"])

# 4. 雲
rnd = random.Random(44)
CB, CA = ART + "SM_IntroCloudB", ART + "SM_IntroCloudA"
CM = MAT + "M_IntroCloud"
n = 0
# 4a 雲の海：島の岩の先より下の層（z=-14000 付近）。外へ向かって大きく
for ring, (r0, r1, cnt, sc) in enumerate([(15000, 24000, 8, 5.0), (20000, 40000, 16, 8.0), (40000, 70000, 22, 12.0), (70000, 110000, 20, 16.0)]):
    for i in range(cnt):
        ang = 2 * math.pi * (i + rnd.random() * 0.8) / cnt
        r = rnd.uniform(r0, r1)
        s = sc * rnd.uniform(0.8, 1.3)
        put("Intro_Cloud_%02d" % n, CB, (r * math.cos(ang), 100 + r * math.sin(ang), -14000 + rnd.uniform(-600, 400) * s / 4), (s, s * rnd.uniform(0.8, 1.2), s * 0.9),
            CM, rot=(0, 0, rnd.uniform(0, 360)))
        n += 1
# 4b 岩の先にかかる塊と、島の縁に少しかかる塊
for i in range(9):
    ang = 2 * math.pi * (i + rnd.random() * 0.6) / 9
    r = rnd.uniform(1500, 7000)
    s = rnd.uniform(1.6, 2.4)
    put("Intro_Cloud_%02d" % n, CA, (r * math.cos(ang), 100 + r * math.sin(ang), rnd.uniform(-12200, -9800)), (s, s, s * 0.8), CM, rot=(0, 0, rnd.uniform(0, 360)))
    n += 1
for i in range(5):
    ang = 2 * math.pi * (i + rnd.random() * 0.6) / 5
    r = rnd.uniform(8000, 9800)
    s = rnd.uniform(1.0, 1.6)
    put("Intro_Cloud_%02d" % n, CA, (r * math.cos(ang), 100 + r * math.sin(ang), rnd.uniform(-2600, -1400)), (s, s, s * 0.7), CM, rot=(0, 0, rnd.uniform(0, 360)))
    n += 1
# 4c 遠くの雲：地平線近く
for i in range(14):
    ang = 2 * math.pi * (i + rnd.random() * 0.7) / 14
    r = rnd.uniform(60000, 110000)
    s = rnd.uniform(9, 15)
    put("Intro_Cloud_%02d" % n, CA if i % 2 else CB, (r * math.cos(ang), 100 + r * math.sin(ang), rnd.uniform(-11000, -5000)), (s, s, s * 0.8), CM, rot=(0, 0, rnd.uniform(0, 360)))
    n += 1

# 5. 遠くの小島（島を縮めたものに小さい家）
HOUSE_W, ROOF = MAT + "MI_Canal_Plaster_Cream", MAT + "MI_Canal_Roof"
for k, (x, y, z, sc, yaw) in enumerate([(26000, -24000, -1500, 0.16, 30), (-9000, 33000, -3200, 0.22, 110), (38000, 21000, -800, 0.12, 200)]):
    put("Intro_Islet_%d" % k, ART + "SM_IntroIsland", (x, y, z), (sc, sc, sc), mats=[G, MAT + "M_IntroRock"], rot=(0, 0, yaw))
    hw = 700.0 * sc / 0.16 * 0.8
    put("Intro_Islet_%d_House" % k, CUBE, (x, y, z + hw * 0.5), (hw / 100, hw * 1.2 / 100, hw / 100), HOUSE_W, rot=(0, 0, yaw))
    put("Intro_Islet_%d_Roof" % k, CONE, (x, y, z + hw + hw * 0.3), (hw * 1.5 / 100, hw * 1.8 / 100, hw * 0.6 / 100), ROOF, rot=(0, 0, yaw))

# 6. 屋根を隠すのをやめる（A_Roof のアクタと ArtHost の ISM_roof）
HIDE = unreal.Name("IntroHide")
for a in EAS.get_all_level_actors():
    if HIDE in list(a.tags):
        a.tags = [t for t in a.tags if t != HIDE]
        print("untag actor", a.get_actor_label())
    for c in a.get_components_by_class(unreal.ActorComponent):
        if HIDE in list(c.component_tags):
            c.component_tags = [t for t in c.component_tags if t != HIDE]
            print("untag component", a.get_actor_label(), c.get_name())

# 7. 紹介画面のカメラ
for a in EAS.get_all_level_actors():
    if a.get_actor_label() == "MapInfo":
        a.set_editor_property("IntroCamLoc", CAM_LOC)
        a.set_editor_property("IntroCamRot", CAM_ROT)
        print("MapInfo camera", CAM_LOC, CAM_ROT)

from collections import Counter
chk = Counter((a.static_mesh_component.get_collision_enabled().name, str(a.static_mesh_component.get_collision_profile_name()), a.static_mesh_component.get_editor_property("can_ever_affect_navigation"), a.static_mesh_component.cast_shadow, a.get_editor_property("hidden")) for a in made)
print("IntroIsland actors", len(made), "clouds", n, "check(collision, profile, nav, shadow, hidden)", dict(chk))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
