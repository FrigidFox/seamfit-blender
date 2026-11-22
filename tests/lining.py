"""Fit a lined garment, check signed thickness against its paired outer patch."""
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import ROOT, load_addons

sf = load_addons()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "Hock-gaiter.blend"))
s = bpy.context.scene.seamfit
obj = s.garment
mesh = obj.data
mesh.calc_loop_triangles()
outer = tuple(mesh.loop_triangles[len(mesh.loop_triangles)//2].vertices)
a, b, c = (mesh.vertices[i].co.copy() for i in outer)
normal = (b-a).cross(c-a).normalized()
thickness = .0006
mix = ((.5,.25,.25), (.25,.5,.25), (.25,.25,.5))
bm = bmesh.new()
bm.from_mesh(mesh)
inner = [bm.verts.new(a*u+b*v+c*w-normal*thickness) for u,v,w in mix]
face = bm.faces.new(inner[::-1])
bm.verts.ensure_lookup_table()
# Include a connecting rim, which must not act as an outer attachment.
bm.faces.new((bm.verts[outer[0]], bm.verts[outer[1]], inner[1], inner[0]))
bm.faces.index_update()
bm.verts.index_update()
face_id = face.index
ids = [vert.index for vert in inner]
bm.to_mesh(mesh)
bm.free()
mesh.update()
assert bpy.ops.seamfit.protect() == {'FINISHED'}
bm = bmesh.from_edit_mesh(mesh)
bm.faces.ensure_lookup_table()
bm.faces[face_id].select_set(True)
bmesh.update_edit_mesh(mesh, destructive=False)
assert bpy.ops.seamfit.protect() == {'FINISHED'}
assert set(obj[sf.fit.PIN_IDS]) == set(ids) and obj[sf.lining.FOLLOW]
shape = sf.session.topology.fingerprint(mesh)
original = [v.co.copy() for v in mesh.vertices]
g = s.guides.add()
g.start = (0,0,0)
g.end = (.004,.007,.003)

def check_spacing(garment):
    assert sf.session.topology.fingerprint(garment.data) == shape
    a,b,c = [garment.data.vertices[i].co.copy() for i in outer]
    n = (b-a).cross(c-a).normalized()
    for i, (u,v,w) in zip(ids, mix):
        offset = garment.data.vertices[i].co - (a*u+b*v+c*w)
        assert (offset+n*thickness).length < 2e-6, (i, offset, n*thickness)
        assert offset.dot(n) < 0

assert bpy.ops.seamfit.preview() == {'FINISHED'}
fit = sf.session.clothes(bpy.context.scene)[0]
check_spacing(fit)
assert all((fit.data.vertices[i].co-original[i]).length > thickness for i in ids)
anchors = list(fit[sf.lining.TRIANGLES])
for level in (.005,.01):
    bpy.context.scene.seamfit.clearance = level
    assert bpy.ops.seamfit.relieve() == {'FINISHED'}
    check_spacing(fit)
    assert list(fit[sf.lining.TRIANGLES]) == anchors
assert bpy.ops.seamfit.finish() == {'FINISHED'}
out = sf.session.clothes(bpy.context.scene)[0]
check_spacing(out)
for i, factors in zip(ids, mix):
    expected = {}
    for corner, factor in zip(outer, factors):
        for g in out.data.vertices[corner].groups:
            expected[g.group] = expected.get(g.group, 0) + factor * g.weight
    expected = dict(sorted(expected.items(), key=lambda kv: -kv[1])[:4])
    groups = out.data.vertices[i].groups
    for g in groups:
        assert abs(g.weight-expected[g.group]/sum(expected.values())) < 1e-4
    assert 1 <= len(groups) <= 4 and abs(sum(g.weight for g in groups)-1) < .00001
assert all(v.co == before for v,before in zip(mesh.vertices, original))
print("PASS 0.6 mm signed lining offset through guided fit, two repairs and RWT binding; rim and topology retained")

# Parallel fabric on a flat body: the lining is thicker than body clearance.
bpy.ops.mesh.primitive_plane_add(size=4)
surface = sf.fit.body_surface(bpy.context.object)
mesh = bpy.data.meshes.new("Fabric with a thick lining")
mesh.from_pydata([(-1,-1,-.01), (1,-1,-.01), (0,1,-.01),
                  (-.4,-.4,-.03), (.4,-.4,-.03), (0,.4,-.03)], [],
                 [(0,1,2), (5,4,3), (0,3,4,1)])
cloth = bpy.data.objects.new("Double layer", mesh)
bpy.context.scene.collection.objects.link(cloth)
cloth[sf.fit.PIN_IDS] = [3,4,5]
cloth[sf.fit.PIN_STAMP] = sf.session.topology.fingerprint(mesh)
cloth[sf.lining.FOLLOW] = True
s.clearance = .003
s.travel = .05
sf.fit.adjust(cloth, surface, s)
for v in mesh.vertices:
    expected = .023 if v.index < 3 else .003
    assert abs(v.co.z - expected) < 1e-6, v.co.z
print("PASS both layers translate together; outer surface leaves room for 20 mm lining and 3 mm clearance")
