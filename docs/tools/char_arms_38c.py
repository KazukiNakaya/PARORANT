# Step 38c: 一人称の腕の単色マテリアル（迷彩・マネキンの柄をやめる）。Unreal Editor の Python で実行（再実行しても同じ結果）
import unreal

MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
DIR = "/Game/PARORANT/Materials"
PATH = DIR + "/M_ArmsFlat"

if unreal.EditorAssetLibrary.does_asset_exist(PATH):
    m = unreal.EditorAssetLibrary.load_asset(PATH)
    MEL.delete_all_material_expressions(m)
else:
    m = AT.create_asset("M_ArmsFlat", DIR, unreal.Material, unreal.MaterialFactoryNew())

tint = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -500, 0)
tint.set_editor_property("parameter_name", "Tint")
tint.set_editor_property("default_value", unreal.LinearColor(0.05, 0.06, 0.08, 1))
rough = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -500, 200)
rough.set_editor_property("parameter_name", "Roughness")
rough.set_editor_property("default_value", 0.8)
MEL.connect_material_property(tint, "", unreal.MaterialProperty.MP_BASE_COLOR)
MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
m.set_editor_property("used_with_skeletal_mesh", True)
MEL.recompile_material(m)
unreal.EditorAssetLibrary.save_loaded_asset(m)


def inst(name, rgb):
    p = DIR + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(p):
        mi = unreal.EditorAssetLibrary.load_asset(p)
    else:
        mi = AT.create_asset(name, DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", m)
    MEL.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1))
    unreal.EditorAssetLibrary.save_loaded_asset(mi)


inst("MI_Arms_Sleeve", (0.07, 0.085, 0.11))   # 袖：落ち着いた濃い灰青の単色
inst("MI_Arms_Glove", (0.02, 0.02, 0.025))    # 手袋：ほぼ黒
print("arms materials done")
