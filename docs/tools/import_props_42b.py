"""Meshy の小物 9 個（Step 42b A）を Unreal に取り込む。何度実行しても同じ結果（上書き取り込み）。

Unreal Editor の Python（MCP の system_control.execute_python）で実行する。
入力：download/meshy/<フォルダ>/<出力名>.fbx（Blender で整え済み。UCX_ 付きは簡易コリジョン 1 個）
出力：/Game/PARORANT/Art/Props/ に SM_*、T_*_BaseColor（最大 1024）、MI_*（親は M_Prop か M_PropFoliage）
- 親素材：M_Prop（片面）、M_PropFoliage（両面。葉のあるもの）。パラメータ Desat（彩度を落とす 0〜1）、Brightness（明るさの倍率）、テクスチャ BaseTex
- 場外の飾り（当たり判定なし）：コリジョンの形を持たせない。角の小物：取り込んだ凸 1 個だけ。CollisionTraceFlag = UseSimpleAsComplex
"""
import unreal

PROJ = unreal.Paths.project_dir()
DST = "/Game/PARORANT/Art/Props"
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary

# 見た目の三角形をそのまま当たり判定に使う小物（42c 続き。凸形状を足しても輪郭に合わなかった麻袋・壺）。植木鉢は葉まで当たらないよう、鉢だけの凸形状（UseSimpleAsComplex）
COMPLEX_COLLISION = {"sacks", "amphora"}

# フォルダ, 出力名（Unreal での名前）, 取り込む FBX 名, 両面か, 当たり判定の有無, 彩度を落とす量, 明るさ
PROPS = [
    ("palm_tall", "SM_PalmTall", "SM_PalmTall", True, False, 0.30, 1.0),
    ("palm_bent", "SM_PalmBent", "SM_PalmBent", True, False, 0.30, 1.0),
    ("bush", "SM_TropicBush", "SM_TropicBush", True, False, 0.25, 1.0),
    ("boat", "SM_Rowboat", "SM_Rowboat", False, False, 0.40, 1.0),
    ("parasol", "SM_Parasol", "SM_ParasolClosed", True, False, 0.30, 1.0),
    ("crate_small", "SM_CrateSmall", "SM_CrateSmall", False, True, 0.30, 1.0),
    ("sacks", "SM_SackPile", "SM_SackPile", False, True, 0.30, 1.0),
    ("pot_plant", "SM_PotPlant", "SM_PotPlant", True, True, 0.30, 1.0),
    ("amphora", "SM_Amphora", "SM_Amphora", False, True, 0.40, 1.0),
]


def make_parent(name, two_sided):
    path = DST + "/" + name
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    m = AT.create_asset(name, DST, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("two_sided", two_sided)
    tex = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -900, 0)
    tex.set_editor_property("parameter_name", "BaseTex")
    tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    des = MEL.create_material_expression(m, unreal.MaterialExpressionDesaturation, -600, 0)
    dp = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -900, 250)
    dp.set_editor_property("parameter_name", "Desat")
    dp.set_editor_property("default_value", 0.3)
    br = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -600, 250)
    br.set_editor_property("parameter_name", "Brightness")
    br.set_editor_property("default_value", 1.0)
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 0)
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 200)
    rough.set_editor_property("r", 0.85)
    MEL.connect_material_expressions(tex, "RGB", des, "")
    MEL.connect_material_expressions(dp, "", des, "Fraction")
    MEL.connect_material_expressions(des, "", mul, "A")
    MEL.connect_material_expressions(br, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def run():
    parents = {False: make_parent("M_Prop", False), True: make_parent("M_PropFoliage", True)}
    only = globals().get("ONLY")   # 例 ONLY = ["sacks"]：指定したフォルダだけ取り込み直す（42c）
    for folder, out, fbx, two, col, desat, bright in PROPS:
        if only and folder not in only:
            continue
        t = unreal.AssetImportTask()
        t.filename = PROJ + "download/meshy/%s/%s.fbx" % (folder, fbx)
        t.destination_path = DST
        t.automated = True
        t.replace_existing = True
        t.save = False
        AT.import_asset_tasks([t])
        imported = [str(p) for p in t.imported_object_paths]
        print(out, "imported", imported)
        # FBX のファイル名が出力名と違う（ParasolClosed）→ 名前を直す
        if fbx != out:
            src = DST + "/" + fbx
            if EAL.does_asset_exist(DST + "/" + out):
                EAL.delete_asset(DST + "/" + out)
            EAL.rename_asset(src, DST + "/" + out)
        sm = unreal.load_asset(DST + "/" + out)
        # テクスチャ：<folder>_base_color → T_<名前>_BaseColor、最大 1024
        tname = out[3:] if out.startswith("SM_") else out
        old_t = DST + "/" + folder + "_base_color"
        new_t = DST + "/T_" + tname + "_BaseColor"
        if EAL.does_asset_exist(old_t):
            if EAL.does_asset_exist(new_t):
                EAL.delete_asset(new_t)
            EAL.rename_asset(old_t, new_t)
        tex = unreal.load_asset(new_t)
        tex.set_editor_property("max_texture_size", 1024)
        EAL.save_loaded_asset(tex)
        # 素材インスタンス
        mi_path = DST + "/MI_" + tname
        if EAL.does_asset_exist(mi_path):
            mi = unreal.load_asset(mi_path)
        else:
            mi = AT.create_asset("MI_" + tname, DST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", parents[two])
        MEL.set_material_instance_texture_parameter_value(mi, "BaseTex", tex)
        MEL.set_material_instance_scalar_parameter_value(mi, "Desat", desat)
        MEL.set_material_instance_scalar_parameter_value(mi, "Brightness", bright)
        EAL.save_loaded_asset(mi)
        # メッシュの素材とコリジョン
        n = len(sm.static_materials)
        for i in range(n):
            sm.set_material(i, mi)
        bs = sm.get_editor_property("body_setup")
        if not col and bs:
            agg = bs.get_editor_property("agg_geom")
            agg.set_editor_property("convex_elems", [])
        if col and bs:
            if folder in COMPLEX_COLLISION:
                bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                # プロパティの変更イベントを出して当たり判定を作り直させる（フラグだけ変えても古い形が残る）。元に戻して保存
                sm.set_editor_property("allow_cpu_access", True)
                sm.set_editor_property("allow_cpu_access", False)
            else:
                bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
        EAL.save_loaded_asset(sm)
        # 取り込みで自動生成された素材 Mat_* は使わないので消す
        for a in EAL.list_assets(DST):
            if "/Mat_" in a:
                EAL.delete_asset(a)
        bs = sm.get_editor_property("body_setup")
        agg = bs.get_editor_property("agg_geom") if bs else None
        print(out, "slots", n, "convex", len(agg.get_editor_property("convex_elems")) if agg else None,
              "tri", sm.get_num_triangles(0) if hasattr(sm, "get_num_triangles") else "?",
              "bounds", sm.get_bounds().box_extent * 2)


run()
