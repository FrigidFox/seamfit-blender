"""Indexed garment connectivity and face-only clipping in the shipping extension."""
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import ROOT, load_addons

sf = load_addons()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "Hock-gaiter.blend"))
s = bpy.context.scene.seamfit
garment = s.garment
sig = sf.session.topology.fingerprint
expected = sig(garment.data)
uv = [loop.uv[:] for loop in garment.data.uv_layers.active.data]
sub = garment.modifiers.new("Display smoothing", 'SUBSURF')
sub.levels = 2
assert bpy.ops.seamfit.preview() == {'FINISHED'}
fit = sf.session.clothes(bpy.context.scene)[0]
assert sig(fit.data) == expected and sub.show_viewport
assert [loop.uv[:] for loop in fit.data.uv_layers.active.data] == uv
assert bpy.ops.seamfit.relieve() == {'FINISHED'}
assert sig(fit.data) == expected
mod = fit.modifiers.new("Review topology change", 'TRIANGULATE')
try:
    bpy.ops.seamfit.finish()
except RuntimeError as exc:
    assert "changes the mesh layout" in str(exc)
else:
    raise AssertionError("Changed preview passed verification")
fit.modifiers.remove(mod)
assert bpy.ops.seamfit.finish() == {'FINISHED'}
result = sf.session.clothes(bpy.context.scene)[0]
assert sig(result.data) == expected
assert [loop.uv[:] for loop in result.data.uv_layers.active.data] == uv
assert sig(garment.data) == expected

# Four corners of a broad cloth face clear a round body; its center cuts the cap.
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16)
body = bpy.context.object
tree = sf.fit.body_surface(body)
mesh = bpy.data.meshes.new("Fabric quad")
mesh.from_pydata([(-2,-2,.9),(2,-2,.9),(2,2,.9),(-2,2,.9)], [], [(0,1,2,3)])
obj = bpy.data.objects.new("Fabric quad", mesh)
bpy.context.scene.collection.objects.link(obj)
assert all(sf.fit.signed_gap(v.co, tree)[0] > 0 for v in mesh.vertices)
assert len(sf.fit.suspect_vertices(obj, tree)) == 4
sig_before = sig(mesh)
s.travel = .3
sf.fit.adjust(obj, tree, s, tighten=False)
assert not sf.fit.suspect_vertices(obj, tree)
assert sig(mesh) == sig_before
print("PASS subdivision cage, indexed connectivity and UVs through RWT, rejected topology edit, face-only clipping detection and repair")
