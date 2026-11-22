"""Exercise face selection, exact pins through fitting and repair, and real binding."""
from pathlib import Path
import sys

import bpy
import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import ROOT, load_addons

sf = load_addons()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "Hock-gaiter.blend"))
s = bpy.context.scene.seamfit
obj = s.garment
s.body.select_set(True)
assert bpy.ops.seamfit.protect() == {'FINISHED'}
bm = bmesh.from_edit_mesh(obj.data)
bm.faces.ensure_lookup_table()
face = bm.faces[10]
fixed = {v.index for v in face.verts}
face.select_set(True)
bmesh.update_edit_mesh(obj.data, destructive=False)
assert bpy.ops.seamfit.protect() == {'FINISHED'}
assert s.body.select_get()
assert sf.fit.fixed_vertices(obj) == fixed
before = [v.co[:] for v in obj.data.vertices]
guide = s.guides.add()
guide.start = (0, 0, 0)
guide.end = (.002, .003, 0)
assert bpy.ops.seamfit.preview() == {'FINISHED'}
fit = sf.session.clothes(bpy.context.scene)[0]
assert sf.fit.fixed_vertices(fit) == fixed
assert all(fit.data.vertices[i].co[:] == before[i] for i in fixed)
assert any(v.co[:] != before[v.index] for v in fit.data.vertices if v.index not in fixed)
for _ in range(2):
    assert bpy.ops.seamfit.relieve() == {'FINISHED'}
    assert all(fit.data.vertices[i].co[:] == before[i] for i in fixed)
assert bpy.ops.seamfit.check() == {'FINISHED'}
assert bpy.context.scene.seamfit.fixed_suspects == sum(fit.data.vertices[i].select for i in fixed)
assert bpy.ops.seamfit.protect() == {'FINISHED'}
bm = bmesh.from_edit_mesh(fit.data)
assert {v.index for f in bm.faces if f.select for v in f.verts} == fixed
bpy.ops.mesh.select_all(action='DESELECT')
assert bpy.ops.seamfit.protect() == {'FINISHED'}
assert not sf.fit.fixed_vertices(fit) and sf.fit.fixed_vertices(obj) == fixed
assert bpy.ops.seamfit.finish() == {'FINISHED'}
result = sf.session.clothes(bpy.context.scene)[0]
assert all(result.data.vertices[i].co[:] == before[i] for i in fixed)
assert [v.co[:] for v in obj.data.vertices] == before
print("PASS selected faces kept exact coordinates through guides, fit, repeated repair and binding")

# An intentionally buried lining and an exterior face that crosses only in its interior.
bpy.ops.mesh.primitive_uv_sphere_add()
surface = sf.fit.body_surface(bpy.context.object)
mesh = bpy.data.meshes.new("Lined fabric")
mesh.from_pydata([(-.1,-.1,.8), (.1,-.1,.8), (0,.1,.8),
                  (-2,-2,.99), (2,-2,.99), (2,2,.99), (-2,2,.99)],
                 [], [(0,1,2), (3,4,5,6)])
cloth = bpy.data.objects.new("Lined fabric", mesh)
bpy.context.scene.collection.objects.link(cloth)
cloth[sf.fit.PIN_IDS] = [0,1,2,3]
cloth[sf.fit.PIN_STAMP] = sf.session.topology.fingerprint(mesh)
original = [v.co[:] for v in mesh.vertices]
s.travel = .5
sf.fit.adjust(cloth, surface, s, tighten=False)
assert [v.co[:] for v in mesh.vertices[:4]] == original[:4]
assert any(v.co[:] != original[v.index] for v in mesh.vertices[4:])
sf.session.check_clothing([cloth], surface, s)
assert s.fixed_suspects >= 3 and s.suspects >= s.fixed_suspects
print("PASS buried lining stays fixed and reported, mixed-pin crossing moves free corners")
