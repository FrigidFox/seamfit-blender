"""Exercise bind-space fitting on a transformed, morphed body and export visibility."""

import sys
from pathlib import Path
import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import ROOT, load_addons

sf = load_addons()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "Hock-gaiter.blend"))
s = bpy.context.scene.seamfit
rig = s.body.find_armature()
rig.matrix_world = Matrix.LocRotScale(
    Vector((0.43, -0.24, 0.18)), Euler((0.15, -0.1, 0.22)), Vector((1.15, 0.87, 1.05))
)
s.garment.matrix_world = rig.matrix_world.copy()
body = s.body
body.shape_key_add(name="Basis")
shape = body.shape_key_add(name="Broader calf")
for point in shape.data:
    point.co.x *= 1.16
shape.value = 0.65
bpy.context.view_layer.update()
graph = bpy.context.evaluated_depsgraph_get()
source_world = [
    body.matrix_world @ v.co for v in body.evaluated_get(graph).data.vertices
]
assert bpy.ops.seamfit.preview() == {"FINISHED"}
review = bpy.context.scene
b = review.seamfit.body
assert (
    max(
        (p - b.matrix_world @ v.co).length
        for p, v in zip(source_world, b.data.vertices)
    )
    < 1e-5
)
clothing = sf.session.clothes(review)[0]
fitted = [clothing.matrix_world @ v.co for v in clothing.data.vertices]
assert bpy.ops.seamfit.finish() == {"FINISHED"}
out = sf.session.clothes(bpy.context.scene)[0]
graph = bpy.context.evaluated_depsgraph_get()
assert (
    max(
        (p - out.matrix_world @ v.co).length
        for p, v in zip(fitted, out.evaluated_get(graph).data.vertices)
    )
    < 1e-5
)
assert body.data.shape_keys.key_blocks["Broader calf"].value == shape.value
out.hide_set(True)
try:
    bpy.ops.seamfit.export(filepath=str(ROOT / "qa" / "hidden.fbx"))
except RuntimeError as exc:
    assert "Show and unlock" in str(exc)
else:
    raise AssertionError("Hidden garment should block an incomplete FBX export")
assert not (ROOT / "qa" / "hidden.fbx").exists()
print(
    "PASS transformed bind space, body shape mix, final world-space garment and hidden export guard"
)
