"""Run after trial.py, using its saved example as the input scene."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import ROOT, load_addons

sf = load_addons()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Hock-gaiter.blend'))
source = bpy.context.scene
settings = source.seamfit
body, garment = settings.body, settings.garment
rig = body.find_armature()
base_counts = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.armatures))
base_scene_count = len(bpy.data.scenes)


def expect_failure(op, message):
    try:
        result = op()
    except RuntimeError as exc:
        assert message in str(exc), exc
    else:
        assert result == {'CANCELLED'}, result
    assert message in bpy.context.scene.seamfit.message


# An invalid region fails after scratch allocation; only the source should survive.
settings.region = "Unknown group"
expect_failure(bpy.ops.seamfit.preview, "existing body vertex group")
assert bpy.context.scene == source and len(bpy.data.scenes) == base_scene_count
assert base_counts == (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.armatures))
settings.region = ""
rig.pose.bones['Hock.L'].rotation_mode = 'XYZ'
rig.pose.bones['Hock.L'].rotation_euler.x = .3
bpy.context.view_layer.update()
expect_failure(bpy.ops.seamfit.preview, "Rest Position")
rig.pose.bones['Hock.L'].rotation_euler.x = 0

# Subdivide the use case into two separate mesh objects, both with UVs.
other = garment.copy()
other.data = garment.data.copy()
source.collection.objects.link(other)
other.name = 'Second garment'
sf.session.set_active(bpy.context, garment)
other.select_set(True)
settings.include_selected = True
guide = settings.guides.add()
guide.start = garment.matrix_world @ garment.data.vertices[0].co
guide.end = Vector(guide.start) + Vector((.003, .002, 0))
assert bpy.ops.seamfit.preview() == {'FINISHED'}
fit = bpy.context.scene
pieces = sf.session.clothes(fit)
assert len(pieces) == 2
# Force genuine RWT failure on the second piece after the first one transfers.
pieces[1].location.x += 2
bpy.context.view_layer.update()
counts = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.armatures))
scene_count = len(bpy.data.scenes)
expect_failure(bpy.ops.seamfit.finish, "Transfer failed")
assert bpy.context.scene == fit and len(bpy.data.scenes) == scene_count
assert counts == (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.armatures))
assert all(len(p.vertex_groups) == 0 for p in pieces)
pieces[1].location.x -= 2
bpy.context.view_layer.update()
assert bpy.ops.seamfit.finish() == {'FINISHED'}
out = bpy.context.scene
assert len(out.objects) == 3 and len(sf.session.clothes(out)) == 2
for piece in sf.session.clothes(out):
    assert piece.find_armature() == out.seamfit.rig
    assert all(abs(sum(g.weight for g in v.groups)-1) < 1e-5 for v in piece.data.vertices)
assert bpy.ops.seamfit.source() == {'FINISHED'} and bpy.context.scene == source
print('PASS invalid-region cleanup, posed-rig check, two-piece fit with guide, real RWT failure, rollback, retry and source recovery')
