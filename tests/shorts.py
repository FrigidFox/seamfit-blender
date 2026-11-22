"""Check the original waistband, both leg openings and inseam on a synthetic fit."""
import math
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import ROOT, load_addons


def shorts_mesh():
    coords, faces, indices = [], [], {}

    def point(x, y, z):
        key = tuple(round(v, 8) for v in (x, y, z))
        if key not in indices:
            indices[key] = len(coords)
            coords.append(key)
        return indices[key]

    angles = [i * math.tau / 24 - math.pi / 2 for i in range(24)]
    for side in (1, -1):
        def strip(lower, upper, closed=True):
            for i in range(len(lower) if closed else len(lower) - 1):
                j = (i + 1) % len(lower)
                face = (lower[i], lower[j], upper[j], upper[i])
                faces.append(face if side == 1 else face[::-1])

        lower = []
        for z in (0, .03, .11, .18):
            ring = [point(side * (.14 + .115 * math.cos(t)), .13 * math.sin(t), z) for t in angles]
            if lower:
                strip(lower, ring)
            lower = ring
        # The inner halves of the two rings share the inseam, and the outer
        # halves continue into a single waistband.
        ring = [point(side * .265 * max(0, math.cos(t)), .14 * math.sin(t),
                      .27 + .045 * min(0, math.cos(t))) for t in angles]
        strip(lower, ring)
        lower = ring[:13]
        for z in (.32, .38, .40):
            upper = [point(side * .265 * math.cos(t), .14 * math.sin(t), z) for t in angles[:13]]
            strip(lower, upper, closed=False)
            lower = upper
    mesh = bpy.data.meshes.new("Connected shorts")
    mesh.from_pydata(coords, [], faces)
    mesh.update()
    return mesh


sf = load_addons()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "Hock-gaiter.blend"))
s = bpy.context.scene.seamfit
rig = s.body.find_armature()
shorts = bpy.data.objects.new("Shorts", shorts_mesh())
bpy.context.scene.collection.objects.link(shorts)
body = bpy.data.objects.new("Test hips and thighs", shorts.data.copy())
bpy.context.scene.collection.objects.link(body)
for v in body.data.vertices:
    v.co.y *= 1.12
body.data.update()
group = body.vertex_groups.new(name="Thigh.L")
group.add(list(range(len(body.data.vertices))), 1.0, 'REPLACE')
body.modifiers.new("Skin", 'ARMATURE').object = rig
shorts.modifiers.new("Viewport subdivision", 'SUBSURF').levels = 1
s.body, s.garment = body, shorts
bpy.context.view_layer.update()
initial = sf.fit.suspect_vertices(shorts, sf.fit.body_surface(body))
assert initial
sig = sf.session.topology.fingerprint(shorts.data)
assert bpy.ops.seamfit.preview() == {'FINISHED'}
review = bpy.context.scene
fitted = sf.session.clothes(review)[0]
assert sf.session.topology.fingerprint(fitted.data) == sig
assert review.seamfit.suspects < len(initial)
print("Synthetic shorts:", len(shorts.data.vertices), "vertices,", len(initial), "flagged before,", review.seamfit.suspects, "after preview")
assert bpy.ops.seamfit.relieve() == {'FINISHED'}
assert bpy.ops.seamfit.check() == {'FINISHED'}
print("After Fix clipping:", review.seamfit.suspects, "flagged")
assert review.seamfit.suspects == 0
assert sf.session.topology.fingerprint(fitted.data) == sig
assert bpy.ops.seamfit.finish() == {'FINISHED'}
out = sf.session.clothes(bpy.context.scene)[0]
assert sf.session.topology.fingerprint(out.data) == sig
assert out.find_armature() == bpy.context.scene.seamfit.rig
assert bpy.ops.seamfit.export(filepath=str(ROOT / "qa" / "shorts-test.fbx")) == {'FINISHED'}
print("PASS connected shorts cage through fit, weight transfer and export")
