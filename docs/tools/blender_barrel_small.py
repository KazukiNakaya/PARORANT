"""Meshy の樽（download/meshy/barrel/barrel.fbx）を、道の角に置く乗れる小さな樽（SM_BarrelSmall）に整える Blender 用スクリプト（Step 38b、docs/26 §10）。

Blender（5.x）の Python で実行する（Blender MCP の execute_blender_code でよい）。既存のシーンには触れない：
新しいコレクション "BarrelWork" の中だけで作業し、書き出したあと、読み込んだ物（オブジェクト、メッシュ、素材、画像）とコレクションを消す。
やること：
  1. FBX を読み込む（Y 上の FBX が X=90° 回転で入ってくる）。回転・拡縮・位置を適用
  2. 重なった頂点の結合（0.2mm）、読み込みで付いたカスタム法線の消去、角度 35° 未満の辺をなめらかに（Shade Smooth by Angle）
  3. 高さ 70cm（一様拡縮。直径は 約 59cm）、原点を底面の中央（XY は外形の中心、Z は底）
  4. FBX で書き出す（メッシュのみ、+Z 上）。書き出しの単位の設定（apply_unit_scale=False、FBX_SCALE_NONE、global_scale=1）は、
     試して決めた値：Blender の高さ 0.7（m）が、Unreal の取り込みでちょうど 70cm になる（apply_unit_scale=True だと 0.7cm、
     頂点を 100 倍して同じ設定にすると 70m になった）
元の樽は、8 角形に近い面の板と、別部品の鉄の輪 3 本（43 個の部品）でできている。浮いた破片は無いので削除はしない。
"""
import bpy
import math

SRC = "C:/Users/kazuk/Documents/Repository/UnrealEngine/PARORANT/download/meshy/barrel/barrel.fbx"
DST = "C:/Users/kazuk/Documents/Repository/UnrealEngine/PARORANT/download/meshy/barrel/barrel_small.fbx"
HEIGHT = 0.70          # m
SMOOTH_ANGLE = 35.0    # 度

coll = bpy.data.collections.new("BarrelWork")
bpy.context.scene.collection.children.link(coll)
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children["BarrelWork"]
before = set(bpy.data.objects.keys())
mats_before, imgs_before, meshes_before = set(bpy.data.materials.keys()), set(bpy.data.images.keys()), set(bpy.data.meshes.keys())
bpy.ops.import_scene.fbx(filepath=SRC)
new = [o for o in bpy.data.objects if o.name not in before]
meshes = [o for o in new if o.type == "MESH"]
assert len(meshes) == 1, [o.name for o in new]
o = meshes[0]
o.name = "SM_BarrelSmall"
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# 結合・法線
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.0002)
bpy.ops.object.mode_set(mode="OBJECT")
try:
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
except Exception as e:
    print("clear custom normals:", e)
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(SMOOTH_ANGLE))

# 大きさと原点
me = o.data
zs = [v.co.z for v in me.vertices]
xs = [v.co.x for v in me.vertices]
ys = [v.co.y for v in me.vertices]
k = HEIGHT / (max(zs) - min(zs))
cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
for v in me.vertices:
    v.co.x = (v.co.x - cx) * k
    v.co.y = (v.co.y - cy) * k
    v.co.z = (v.co.z - min(zs)) * k
me.update()
bpy.context.view_layer.update()
dims = tuple(round(d * 100.0, 3) for d in o.dimensions)   # cm

# 書き出し（このオブジェクトだけ）
bpy.ops.object.select_all(action="DESELECT")
o.select_set(True)
bpy.context.view_layer.objects.active = o
bpy.ops.export_scene.fbx(filepath=DST, use_selection=True, object_types={"MESH"}, apply_unit_scale=False,
                         apply_scale_options="FBX_SCALE_NONE", global_scale=1.0, axis_forward="-Y", axis_up="Z",
                         mesh_smooth_type="FACE", add_leaf_bones=False, path_mode="AUTO", bake_anim=False)
stats = {"dims_cm": dims, "verts": len(me.vertices), "tris": sum(len(p.vertices) - 2 for p in me.polygons)}

# 後始末：読み込んだ物を消す
for ob in list(coll.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
bpy.data.collections.remove(coll)
for m in list(bpy.data.meshes):
    if m.name not in meshes_before and m.users == 0:
        bpy.data.meshes.remove(m)
for m in list(bpy.data.materials):
    if m.name not in mats_before and m.users == 0:
        bpy.data.materials.remove(m)
for im in list(bpy.data.images):
    if im.name not in imgs_before and im.users == 0:
        bpy.data.images.remove(im)
result = {"stats": stats, "objects_left": sorted(bpy.data.objects.keys())}
