"""Step 44 B: CANAL の紹介画面用の「浮島の岩」と「雲」の形を作る Blender 用スクリプト（docs/31）。
ヘッドレスで実行：blender --background --factory-startup --python docs/tools/blender_intro_island_44.py
出力（download/intro44/、書き出しの単位は blender_barrel_small.py と同じ。Blender の 1 = Unreal の 100cm）：
  SM_IntroIsland.fbx  上面が平らで、下へ細くなる逆さの岩の塊（素材スロット 0=上面、1=岩の側面）。上面は z=0、長さ 約136m×136m、深さ 75m
  SM_IntroCloudA.fbx / SM_IntroCloudB.fbx  丸い塊を寄せた雲（なめらかな面）。素材スロット 0
乱数は固定の種で、何度実行しても同じ形になる。"""
import bpy, bmesh, math, random
from mathutils import Vector, noise

OUT = "C:/Users/kazuk/Documents/Repository/UnrealEngine/PARORANT/download/intro44/"

def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)

def export(ob, name):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=OUT + name + ".fbx", use_selection=True, object_types={"MESH"}, apply_unit_scale=False,
                             apply_scale_options="FBX_SCALE_NONE", global_scale=1.0, axis_forward="-Y", axis_up="Z",
                             mesh_smooth_type="FACE", add_leaf_bones=False, path_mode="AUTO", bake_anim=False)

def island():
    N, K, D = 80, 18, 75.0
    A, B, P = 68.0, 68.0, 4.0
    random.seed(44)
    mesh = bpy.data.meshes.new("SM_IntroIsland")
    verts, faces, mats = [], [], []
    def rim(th):
        c, s = abs(math.cos(th)), abs(math.sin(th))
        return 1.0 / ((c / A) ** P + (s / B) ** P) ** (1.0 / P)
    rings = []
    for k in range(K + 1):
        t = k / K
        d = D * (t ** 1.25) if k > 0 else 0.0
        if k == 1: d = 2.5
        scale = 1.0 if k == 0 else (0.99 if k == 1 else (1.0 - t) ** 0.6)
        amp = 0.04 + 0.22 * t
        ring = []
        for i in range(N):
            th = 2 * math.pi * i / N
            r = rim(th)
            nz = noise.noise(Vector((math.cos(th) * 1.3 + 7, math.sin(th) * 1.3 + 3, t * 3.0)))
            n2 = noise.noise(Vector((math.cos(th) * 3.1, math.sin(th) * 3.1, t * 6.0 + 9)))
            f = scale * (1.0 + amp * (nz + 0.5 * n2))
            z = -d - (6.0 * t * n2 if k > 1 else 0.0)
            ring.append(len(verts)); verts.append((r * f * math.cos(th), r * f * math.sin(th), z))
        rings.append(ring)
    tip = len(verts); verts.append((random.uniform(-2, 2), random.uniform(-2, 2), -D - 4.0))
    faces.append(list(reversed(rings[0]))[::-1]); mats.append(0)       # 上面（法線は上）
    for k in range(K):
        a, b = rings[k], rings[k + 1]
        for i in range(N):
            j = (i + 1) % N
            faces.append([a[i], b[i], b[j], a[j]]); mats.append(1)
    for i in range(N):
        j = (i + 1) % N
        faces.append([rings[K][i], tip, rings[K][j]]); mats.append(1)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for m in ("IntroIslandTop", "IntroIslandRock"):
        mesh.materials.append(bpy.data.materials.new(m))
    for p, mi in zip(mesh.polygons, mats):
        p.material_index = mi; p.use_smooth = False
    ob = bpy.data.objects.new("SM_IntroIsland", mesh)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    # 面の向きを揃える（外向き）
    bm = bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(mesh); bm.free()
    # 上面の法線が上を向いていなければ反転
    top = [p for p in mesh.polygons if p.material_index == 0][0]
    if top.normal.z < 0:
        bm = bmesh.new(); bm.from_mesh(mesh); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(mesh); bm.free()
    return ob

def cloud(name, n, spread, rmin, rmax, flat, seed):
    random.seed(seed)
    bm = bmesh.new()
    for i in range(n):
        ang = random.uniform(0, 2 * math.pi)
        dist = random.uniform(0, spread) * (1.0 if i else 0.0)
        r = random.uniform(rmin, rmax) * (1.4 if i == 0 else 1.0)
        m = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r)
        for v in m["verts"]:
            v.co.z *= flat
            v.co.x += math.cos(ang) * dist * 1.6
            v.co.y += math.sin(ang) * dist
            v.co.z += random.uniform(-0.2, 0.3) * r * 0.5
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.materials.append(bpy.data.materials.new("IntroCloud"))
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

clear()
isl = island(); export(isl, "SM_IntroIsland")
print("island dims(m)", tuple(round(x, 1) for x in isl.dimensions), "verts", len(isl.data.vertices))
ca = cloud("SM_IntroCloudA", 8, 9.0, 5.0, 9.0, 0.55, 1); export(ca, "SM_IntroCloudA")
cb = cloud("SM_IntroCloudB", 12, 16.0, 4.0, 8.0, 0.40, 2); export(cb, "SM_IntroCloudB")
print("cloud dims(m)", tuple(round(x, 1) for x in ca.dimensions), tuple(round(x, 1) for x in cb.dimensions))
