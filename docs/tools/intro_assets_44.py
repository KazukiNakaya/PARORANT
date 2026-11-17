"""Step 44 B: 紹介画面の浮島用の素材 4 つと、岩・雲のメッシュ 3 つを作る（docs/31 §3）。何度実行しても同じ結果（作り直し）。
Unreal Editor の Python で実行。レベルは変えない。入力：download/intro44/*.fbx（blender_intro_island_44.py の出力）
  Materials/M_IntroSky     空の幕。Unlit・半透明・霧を受けない。ワールド Z で、地平 桃色がかった淡い紫 → 天頂 深い青紫
  Materials/M_IntroCloud   雲。Unlit・不透明。法線の向きで、上は白に近い、下は紫
  Materials/M_IntroRock    島の下の岩。Lit。ワールド Z と noise で、上は茶〜灰、下は紫がかった灰
  Materials/M_IntroGround  島の上面（建物の外側のふち）。Lit。石畳に近い暖色の灰
  Art/Intro/SM_IntroIsland / SM_IntroCloudA / SM_IntroCloudB"""
import unreal
PROJ = unreal.Paths.project_dir()
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
MAT = "/Game/PARORANT/Materials"
ART = "/Game/PARORANT/Art/Intro"

def new_mat(name):
    p = MAT + "/" + name
    if EAL.does_asset_exist(p):
        EAL.delete_asset(p)
    return AT.create_asset(name, MAT, unreal.Material, unreal.MaterialFactoryNew())

def node(m, cls, x, y):
    return MEL.create_material_expression(m, cls, x, y)

def c3(m, r, g, b, x, y):
    n = node(m, unreal.MaterialExpressionConstant3Vector, x, y)
    n.set_editor_property("constant", unreal.LinearColor(r, g, b, 1.0))
    return n

def c1(m, v, x, y):
    n = node(m, unreal.MaterialExpressionConstant, x, y)
    n.set_editor_property("r", v)
    return n

def comp(m, src, ch, x, y):   # ch: "r" "g" "b"
    n = node(m, unreal.MaterialExpressionComponentMask, x, y)
    n.set_editor_property("r", ch == "r"); n.set_editor_property("g", ch == "g"); n.set_editor_property("b", ch == "b")
    MEL.connect_material_expressions(src, "", n, "")
    return n

def sky():
    m = new_mat("M_IntroSky")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    for prop in ("use_translucency_vertex_fog", "apply_fogging"):
        try:
            m.set_editor_property(prop, False); print("sky: set", prop, "False")
        except Exception as e:
            pass
    wp = node(m, unreal.MaterialExpressionWorldPosition, -1400, 0)
    z = comp(m, wp, "b", -1200, 0)
    div = node(m, unreal.MaterialExpressionDivide, -1000, 0)
    MEL.connect_material_expressions(z, "", div, "A"); MEL.connect_material_expressions(c1(m, 26000.0, -1200, 120), "", div, "B")
    sat = node(m, unreal.MaterialExpressionSaturate, -800, 0)
    MEL.connect_material_expressions(div, "", sat, "")
    pw = node(m, unreal.MaterialExpressionPower, -600, 0)
    MEL.connect_material_expressions(sat, "", pw, "Base"); MEL.connect_material_expressions(c1(m, 0.5, -800, 120), "", pw, "Exp")
    lerp = node(m, unreal.MaterialExpressionLinearInterpolate, -300, 0)
    MEL.connect_material_expressions(c3(m, 0.80, 0.55, 0.86, -600, -250), "", lerp, "A")    # 地平：桃色がかった淡い紫
    MEL.connect_material_expressions(c3(m, 0.22, 0.09, 0.55, -600, -120), "", lerp, "B")    # 天頂：深い青紫
    MEL.connect_material_expressions(pw, "", lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    # 両面にして、内側（裏面、TwoSidedSign が -1）だけ描く。外側から見ると透明（エディタで島や町を外から見られる）
    m.set_editor_property("two_sided", True)
    ts = node(m, unreal.MaterialExpressionTwoSidedSign, -600, 300)
    neg = node(m, unreal.MaterialExpressionMultiply, -400, 300)
    MEL.connect_material_expressions(ts, "", neg, "A"); MEL.connect_material_expressions(c1(m, -1.0, -600, 400), "", neg, "B")
    op = node(m, unreal.MaterialExpressionSaturate, -200, 300)
    MEL.connect_material_expressions(neg, "", op, "")
    MEL.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)

def cloud():
    m = new_mat("M_IntroCloud")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    n = node(m, unreal.MaterialExpressionVertexNormalWS, -1200, 0)
    nz = comp(m, n, "b", -1000, 0)
    mad = node(m, unreal.MaterialExpressionMultiply, -800, 0)
    MEL.connect_material_expressions(nz, "", mad, "A"); MEL.connect_material_expressions(c1(m, 0.6, -1000, 100), "", mad, "B")
    add = node(m, unreal.MaterialExpressionAdd, -600, 0)
    MEL.connect_material_expressions(mad, "", add, "A"); MEL.connect_material_expressions(c1(m, 0.4, -800, 100), "", add, "B")
    sat = node(m, unreal.MaterialExpressionSaturate, -400, 0)
    MEL.connect_material_expressions(add, "", sat, "")
    lerp = node(m, unreal.MaterialExpressionLinearInterpolate, -200, 0)
    MEL.connect_material_expressions(c3(m, 0.42, 0.30, 0.70, -400, -200), "", lerp, "A")    # 影の側：濃い紫
    MEL.connect_material_expressions(c3(m, 1.0, 0.94, 1.0, -400, -80), "", lerp, "B")       # 光の側：白
    MEL.connect_material_expressions(sat, "", lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)

def lit(name, low, high, z0, z1, noise_scale):
    m = new_mat(name)
    wp = node(m, unreal.MaterialExpressionWorldPosition, -1400, 0)
    z = comp(m, wp, "b", -1200, 0)
    sub = node(m, unreal.MaterialExpressionSubtract, -1000, 0)
    MEL.connect_material_expressions(z, "", sub, "A"); MEL.connect_material_expressions(c1(m, z0, -1200, 100), "", sub, "B")
    div = node(m, unreal.MaterialExpressionDivide, -800, 0)
    MEL.connect_material_expressions(sub, "", div, "A"); MEL.connect_material_expressions(c1(m, z1 - z0, -1000, 100), "", div, "B")
    sat = node(m, unreal.MaterialExpressionSaturate, -600, 0)
    MEL.connect_material_expressions(div, "", sat, "")
    lerp = node(m, unreal.MaterialExpressionLinearInterpolate, -400, 0)
    MEL.connect_material_expressions(c3(m, *low, -600, -200), "", lerp, "A")
    MEL.connect_material_expressions(c3(m, *high, -600, -80), "", lerp, "B")
    MEL.connect_material_expressions(sat, "", lerp, "Alpha")
    out = lerp
    if noise_scale:
        nz = node(m, unreal.MaterialExpressionNoise, -800, 300)
        nz.set_editor_property("scale", noise_scale)
        nz.set_editor_property("output_min", 0.72); nz.set_editor_property("output_max", 1.12)
        nz.set_editor_property("levels", 4)
        MEL.connect_material_expressions(wp, "", nz, "Position")
        mul = node(m, unreal.MaterialExpressionMultiply, -200, 0)
        MEL.connect_material_expressions(lerp, "", mul, "A"); MEL.connect_material_expressions(nz, "", mul, "B")
        out = mul
    MEL.connect_material_property(out, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(c1(m, 0.95, -200, 200), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(c1(m, 0.0, -200, 260), "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)

def import_mesh(name, mats):
    t = unreal.AssetImportTask()
    t.filename = PROJ + "download/intro44/%s.fbx" % name
    t.destination_path = ART
    t.automated = True; t.replace_existing = True; t.save = False
    opt = unreal.FbxImportUI()
    opt.set_editor_property("import_mesh", True)
    opt.set_editor_property("import_materials", False)
    opt.set_editor_property("import_textures", False)
    opt.set_editor_property("import_as_skeletal", False)
    opt.static_mesh_import_data.set_editor_property("auto_generate_collision", False)
    opt.static_mesh_import_data.set_editor_property("combine_meshes", True)
    t.options = opt
    AT.import_asset_tasks([t])
    sm = unreal.load_asset(ART + "/" + name)
    for i in range(len(sm.static_materials)):
        sm.set_material(i, unreal.load_asset(MAT + "/" + mats[min(i, len(mats) - 1)]))
    bs = sm.get_editor_property("body_setup")
    if bs:
        bs.get_editor_property("agg_geom").set_editor_property("convex_elems", [])
    EAL.save_loaded_asset(sm)
    print(name, "slots", len(sm.static_materials), "extent(cm)", sm.get_bounds().box_extent * 2, "tris", sm.get_num_triangles(0) if hasattr(sm, "get_num_triangles") else "?")

sky(); cloud()
lit("M_IntroRock", (0.11, 0.09, 0.19), (0.34, 0.25, 0.22), -7500.0, 0.0, 0.0006)
lit("M_IntroGround", (0.38, 0.33, 0.30), (0.38, 0.33, 0.30), -100.0, 0.0, 0.0)
EAL.make_directory(ART)
import_mesh("SM_IntroIsland", ["M_IntroGround", "M_IntroRock"])
import_mesh("SM_IntroCloudA", ["M_IntroCloud"])
import_mesh("SM_IntroCloudB", ["M_IntroCloud"])
