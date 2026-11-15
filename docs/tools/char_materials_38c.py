# Step 38c: 敵 Bot の輪郭線マテリアルと、敵の体の色マテリアルを作る（再実行しても同じ結果）
# Unreal Editor の Python（execute_python）で実行する。
import unreal

MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
DIR = "/Game/PARORANT/Materials"


def get_or_create(name, cls=unreal.Material, factory=unreal.MaterialFactoryNew):
    path = DIR + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        m = unreal.EditorAssetLibrary.load_asset(path)
        MEL.delete_all_material_expressions(m)
        return m
    return AT.create_asset(name, DIR, cls, factory())


def expr(m, cls, x, y):
    return MEL.create_material_expression(m, cls, x, y)


def vparam(m, name, rgb, x, y):
    e = expr(m, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1))
    return e


def sparam(m, name, v, x, y):
    e = expr(m, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name)
    e.set_editor_property("default_value", v)
    return e


# ---- M_Outline（裏返した外殻。Two Sided + 表面を捨てる Opacity Mask、法線方向に膨らませる）----
def build_outline():
    m = get_or_create("M_Outline")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("used_with_skeletal_mesh", True)
    m.set_editor_property("opacity_mask_clip_value", 0.5)
    col = vparam(m, "Color", (0.35, 0.02, 0.02), -600, -200)
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    # 裏面だけ描く：マスク = saturate(-TwoSidedSign)
    sign = expr(m, unreal.MaterialExpressionTwoSidedSign, -800, 100)
    neg = expr(m, unreal.MaterialExpressionMultiply, -600, 100)
    neg.set_editor_property("const_b", -1.0)
    sat = expr(m, unreal.MaterialExpressionSaturate, -400, 100)
    MEL.connect_material_expressions(sign, "", neg, "A")
    MEL.connect_material_expressions(neg, "", sat, "")
    MEL.connect_material_property(sat, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    # 膨らませる量 = clamp(カメラまでの距離 * Scale, Min, Max)（画面上でほぼ一定の太さ）
    wp = expr(m, unreal.MaterialExpressionWorldPosition, -1000, 400)
    cam = expr(m, unreal.MaterialExpressionCameraPositionWS, -1000, 550)
    dist = expr(m, unreal.MaterialExpressionDistance, -800, 450)
    MEL.connect_material_expressions(wp, "", dist, "A")
    MEL.connect_material_expressions(cam, "", dist, "B")
    scale = sparam(m, "ScreenScale", 0.0025, -800, 600)
    mul = expr(m, unreal.MaterialExpressionMultiply, -600, 480)
    MEL.connect_material_expressions(dist, "", mul, "A")
    MEL.connect_material_expressions(scale, "", mul, "B")
    mn = sparam(m, "MinWidth", 1.0, -600, 620)
    mx = sparam(m, "MaxWidth", 8.0, -600, 700)
    cl = expr(m, unreal.MaterialExpressionClamp, -400, 520)
    MEL.connect_material_expressions(mul, "", cl, "")
    MEL.connect_material_expressions(mn, "", cl, "Min")
    MEL.connect_material_expressions(mx, "", cl, "Max")
    nrm = expr(m, unreal.MaterialExpressionVertexNormalWS, -400, 420)
    off = expr(m, unreal.MaterialExpressionMultiply, -200, 480)
    MEL.connect_material_expressions(nrm, "", off, "A")
    MEL.connect_material_expressions(cl, "", off, "B")
    # World Position Offset は Python の MaterialProperty に無いため、MCP の connect で「off」の出力をつなぐ
    # （「off」＝この乗算ノード。ノード ID は get_material_info で確認）
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m


def build_inst(name, parent, color):
    path = DIR + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mi = unreal.EditorAssetLibrary.load_asset(path)
    else:
        mi = AT.create_asset(name, DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", parent)
    MEL.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(*color, 1))
    unreal.EditorAssetLibrary.save_loaded_asset(mi)


# ---- M_EnemyBody / M_EnemyHead（元のテクスチャの彩度を落として寒色の単色に寄せる）----
def build_enemy(name, tex_bc, tex_n, tint, desat):
    m = get_or_create(name)
    t = expr(m, unreal.MaterialExpressionTextureSample, -900, 0)
    t.set_editor_property("texture", unreal.EditorAssetLibrary.load_asset(tex_bc))
    n = expr(m, unreal.MaterialExpressionTextureSample, -900, 300)
    n.set_editor_property("texture", unreal.EditorAssetLibrary.load_asset(tex_n))
    n.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    ds = expr(m, unreal.MaterialExpressionDesaturation, -650, 0)
    MEL.connect_material_expressions(t, "RGB", ds, "")
    dp = sparam(m, "Desat", desat, -900, -150)
    MEL.connect_material_expressions(dp, "", ds, "Fraction")
    tn = vparam(m, "Tint", tint, -650, 150)
    mul = expr(m, unreal.MaterialExpressionMultiply, -400, 0)
    MEL.connect_material_expressions(ds, "", mul, "A")
    MEL.connect_material_expressions(tn, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(n, "RGB", unreal.MaterialProperty.MP_NORMAL)
    rough = sparam(m, "Roughness", 0.85, -400, 300)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    m.set_editor_property("used_with_skeletal_mesh", True)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)


import sys
# M_Outline 本体は初回だけ作る（WorldPositionOffset は MCP で後からつなぐため、再実行で消さない）
if "REBUILD_OUTLINE" in globals() and REBUILD_OUTLINE:
    mo = build_outline()
else:
    mo = unreal.EditorAssetLibrary.load_asset(DIR + "/M_Outline")
OUTLINE_SCALE = 0.003      # 画面上の太さ：カメラ距離 1m あたり 0.3cm 膨らむ（10m で 3cm）
build_inst("MI_Outline_Enemy", mo, (0.50, 0.02, 0.02))
build_inst("MI_Outline_Ally", mo, (0.05, 0.45, 0.90))
for nm in ("MI_Outline_Enemy", "MI_Outline_Ally"):
    mi = unreal.EditorAssetLibrary.load_asset(DIR + "/" + nm)
    MEL.set_material_instance_scalar_parameter_value(mi, "ScreenScale", OUTLINE_SCALE)
    unreal.EditorAssetLibrary.save_loaded_asset(mi)
ENEMY_TINT = (1.7, 2.3, 3.8)
build_enemy("M_EnemyBody", "/Game/PARORANT/Swat/Textures/T_Swat_Body_BC", "/Game/PARORANT/Swat/Textures/T_Swat_Body_N",
            ENEMY_TINT, 0.8)
build_enemy("M_EnemyHead", "/Game/PARORANT/Swat/Textures/T_Swat_Head_BC", "/Game/PARORANT/Swat/Textures/T_Swat_Head_N",
            ENEMY_TINT, 0.8)
print("done")
