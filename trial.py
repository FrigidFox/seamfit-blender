import sys, math
from pathlib import Path
import bpy
from mathutils import Euler

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "tests"))
from runtime import load_addons

if not bpy.app.background or bpy.data.filepath:
    raise RuntimeError("Run trial.py in an empty background Blender process.")
sf = load_addons()
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.name = "Hock gaiter • Source"
scene.unit_settings.system = "METRIC"


def mat(name, rgb, roughness=0.6):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    shader = m.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    return m


fur = mat("Slate | coat", (0.12, 0.185, 0.215))
cloth = mat("Glacier | shell", (0.11, 0.57, 0.57))
trim = mat("Ink | ribbing", (0.022, 0.055, 0.074))
line = mat("Lime | binding", (0.65, 0.87, 0.23))
# z, fore/aft center, half width, half depth. From toe box to thigh.
profile = [
    (0.035, -0.18, 0.10, 0.17),
    (0.062, -0.19, 0.145, 0.20),
    (0.11, -0.185, 0.15, 0.205),
    (0.16, -0.135, 0.115, 0.15),
    (0.21, -0.07, 0.085, 0.102),
    (0.30, 0.00, 0.073, 0.083),
    (0.43, 0.09, 0.075, 0.077),
    (0.54, 0.165, 0.088, 0.092),
    (0.60, 0.175, 0.102, 0.102),
    (0.68, 0.14, 0.103, 0.109),
    (0.80, 0.065, 0.125, 0.137),
    (0.94, -0.01, 0.125, 0.13),
    (1.05, -0.065, 0.106, 0.117),
    (1.16, -0.06, 0.119, 0.138),
    (1.27, -0.02, 0.146, 0.165),
    (1.42, 0.035, 0.166, 0.18),
    (1.5, 0.048, 0.161, 0.168),
]


def interp(z):
    for a, b in zip(profile, profile[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return [a[i] + t * (b[i] - a[i]) for i in range(1, 4)]
    raise ValueError(z)


def tube(name, rings, cap):
    verts = []
    faces = []
    count = 48
    for z, cy, rx, ry in rings:
        for i in range(count):
            angle = i * 2 * math.pi / count
            verts.append((rx * math.cos(angle), cy + ry * math.sin(angle), z))
    for j in range(len(rings) - 1):
        for i in range(count):
            a = j * count + i
            b = j * count + (i + 1) % count
            faces.append((a, b, b + count, a + count))
    if cap:
        faces.extend(
            [
                tuple(reversed(range(count))),
                tuple(range(len(verts) - count, len(verts))),
            ]
        )
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    for p in mesh.polygons:
        p.use_smooth = True
    return obj


body = tube("Digitigrade leg", profile, True)
body.data.materials.append(fur)
zs = [
    0.275,
    0.28,
    0.288,
    0.299,
    0.312,
    0.323,
    0.36,
    0.41,
    0.46,
    0.51,
    0.56,
    0.61,
    0.66,
    0.71,
    0.76,
    0.81,
    0.855,
    0.86,
    0.873,
    0.885,
    0.89,
]
rings = []
for j, z in enumerate(zs):
    cy, rx, ry = interp(z)
    # A straighter, narrower off-the-rack gaiter cuts into the hock.
    cy = cy * 0.67 - 0.004
    ease = 0.008 if j in (0, 1, 2, 17, 18, 19, 20) else 0.004
    rings.append((z, cy, rx * 0.90 + ease, ry * 0.93 + ease))
garment = tube("Trail gaiter", rings, False)
for m in (cloth, trim, line):
    garment.data.materials.append(m)
for p in garment.data.polygons:
    j = p.index // 48
    p.material_index = 1 if j < 4 or j >= 16 else 0
    if j in (2, 17):
        p.material_index = 2
    if j in range(5, 16) and p.index % 48 in (4, 5):
        p.material_index = 1
arm = bpy.data.armatures.new("Digitigrade skeleton")
rig = bpy.data.objects.new("Trail rig", arm)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
joints = [
    (0, 0.048, 1.5),
    (0, -0.065, 1.05),
    (0, 0.175, 0.58),
    (0, -0.07, 0.21),
    (0, -0.30, 0.075),
]
names = ["Thigh.L", "Shin.L", "Hock.L", "Paw.L"]
prev = None
for name, a, b in zip(names, joints, joints[1:]):
    bone = arm.edit_bones.new(name)
    bone.head = a
    bone.tail = b
    if prev:
        bone.parent = prev
        bone.use_connect = True
    prev = bone
bpy.ops.object.mode_set(mode="OBJECT")
groups = [body.vertex_groups.new(name=n) for n in names]
for v in body.data.vertices:
    z = v.co.z
    weights = [
        math.exp(-(((z - c) / w) ** 2))
        for c, w in ((1.36, 0.25), (0.84, 0.22), (0.395, 0.18), (0.1, 0.1))
    ]
    for g, w in zip(groups, weights):
        if w / sum(weights) > 1e-6:
            g.add([v.index], w / sum(weights), "REPLACE")
mod = body.modifiers.new("Avatar rig", "ARMATURE")
mod.object = rig
body.parent = rig
rig.hide_set(True)
# Add a UV map so material and UV survival are part of the round-trip test.
uv = garment.data.uv_layers.new(name="Fabric UV")
for poly in garment.data.polygons:
    j, i = divmod(poly.index, 48)
    for k, (u, vv) in zip(
        poly.loop_indices, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
    ):
        uv.data[k].uv = (u / 48, vv / (len(zs) - 1))
s = scene.seamfit
s.body = body
s.garment = garment
s.clearance = 0.005
s.match_distance = 0.08
sf.session.set_active(bpy.context, garment)
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        space = area.spaces.active
        space.shading.color_type = "MATERIAL"
        space.shading.light = "STUDIO"
        space.region_3d.view_distance = 2.35
        space.region_3d.view_location = (0, 0, 0.75)
        space.region_3d.view_rotation = Euler(
            (math.radians(82), 0, math.radians(58))
        ).to_quaternion()
        space.region_3d.view_perspective = "ORTHO"
        space.show_region_ui = True
        space.overlay.show_floor = False
        space.overlay.show_axis_x = False
        space.overlay.show_axis_y = False
        for region in area.regions:
            if region.type == "UI":
                try:
                    region.active_panel_category = "Seamfit"
                except Exception:
                    pass
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(root / "Hock-gaiter.blend"), compress=True)
before = sf.session.suspect_vertices(garment, sf.session.body_surface(body))
assert len(before) > 50
source_points = [v.co.copy() for v in garment.data.vertices]
assert bpy.ops.seamfit.preview() == {"FINISHED"}
fit = bpy.context.scene
print("PREVIEW", len(before), fit.seamfit.suspects, flush=True)
assert fit.seamfit.suspects < len(before) * 0.2
assert bpy.ops.seamfit.relieve() == {"FINISHED"}
assert bpy.ops.seamfit.check() == {"FINISHED"}
obj = sf.session.clothes(fit)[0]
assert obj.data.uv_layers and len(obj.data.materials) == 3
nverts = len(obj.data.vertices)
assert bpy.ops.seamfit.finish() == {"FINISHED"}
result = bpy.context.scene
result_rig = result.seamfit.rig
out = sf.session.clothes(result)[0]
print(
    "RESULT",
    result.name,
    [o.name for o in result.objects],
    out.vertex_groups.keys(),
    flush=True,
)
assert len(result.objects) == 2 and len(out.data.vertices) == nverts
assert out.parent == result_rig and out.modifiers[0].object == result_rig
assert len(out.vertex_groups) >= 2
for v in out.data.vertices:
    w = [g.weight for g in v.groups]
    assert 1 <= len(w) <= 4 and abs(sum(w) - 1) < 1e-5


def evaluated_coords(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [v.co.copy() for v in evaluated.data.vertices]


rest = evaluated_coords(out)
pb = result_rig.pose.bones["Hock.L"]
pb.rotation_mode = "XYZ"
pb.rotation_euler.x = 0.4
bpy.context.view_layer.update()
assert max((a - b).length for a, b in zip(rest, evaluated_coords(out))) > 0.02
pb.rotation_euler.x = 0
bpy.context.view_layer.update()
assert all(
    (a - v.co).length < 1e-8 for a, v in zip(source_points, garment.data.vertices)
)
dest = str(root / "test-outfit.fbx")
assert bpy.ops.seamfit.export(filepath=dest) == {"FINISHED"}
assert Path(dest).stat().st_size > 1000
test = bpy.data.scenes.new("FBX roundtrip")
bpy.context.window.scene = test
assert bpy.ops.import_scene.fbx(filepath=dest) == {"FINISHED"}
meshes = [o for o in test.objects if o.type == "MESH"]
rigs = [o for o in test.objects if o.type == "ARMATURE"]
assert len(meshes) == len(rigs) == 1 and meshes[0].find_armature() == rigs[0]
assert len(meshes[0].data.uv_layers) == 1 and len(meshes[0].data.materials) == 3
assert set(rigs[0].data.bones.keys()) == set(names)
print(
    "PASS",
    bpy.app.version_string,
    nverts,
    "vertices",
    len(before),
    "before;",
    "verified bend and FBX round trip",
    flush=True,
)
