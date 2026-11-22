import bpy
import math
from . import topology
from .fit import body_surface, adjust, suspect_vertices, fixed_vertices, PIN_IDS, PIN_STAMP

ROLE = "_seamfit_role"


def clothes(scene):
    return [o for o in scene.objects if o.get(ROLE) == "clothing"]


def set_active(context, obj):
    for selected in context.selected_objects:
        selected.select_set(False)
    obj.hide_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj


def target_rig(body):
    rigs = [m.object for m in body.modifiers if m.type == 'ARMATURE' and m.object and m.show_viewport]
    if len(rigs) != 1:
        raise ValueError("Choose a body mesh with one enabled Armature modifier.")
    rig = rigs[0]
    if rig.data.pose_position != 'REST':
        for bone in rig.pose.bones:
            if any(abs(a - b) > 0.0001 for row, rest in zip(bone.matrix, bone.bone.matrix_local)
                   for a, b in zip(row, rest)):
                raise ValueError("Set the target rig to Rest Position in Armature Data, then preview again.")
    deform = {b.name for b in rig.data.bones if b.use_deform}
    if not any(g.name in deform for g in body.vertex_groups):
        raise ValueError("The body needs weights named for deform bones on the target rig.")
    return rig


def make_rig(scene, original, *, output=False):
    data = original.data.copy()
    data.animation_data_clear()
    data.pose_position = 'POSE'
    source_name = original.get("_seamfit_source", original.name)
    suffix = " • Outfit" if output else " • Preview"
    rig = bpy.data.objects.new(source_name + suffix, data)
    rig["_seamfit_source"] = source_name
    scene.collection.objects.link(rig)
    rig.matrix_world = original.matrix_world.copy()
    rig.display_type = 'WIRE'
    rig.show_in_front = False
    rig[ROLE] = "rig"
    return rig


def snapshot(scene, obj, graph, role, *, output=False):
    if role == "clothing":
        mesh, stamp = topology.clothing_mesh(obj, graph, output=output)
    else:
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph), preserve_all_data_layers=True, depsgraph=graph)
    evaluated = obj.evaluated_get(graph)
    source_name = obj.get("_seamfit_source", obj.name)
    suffix = " • Fitted" if output else " • Preview"
    result = bpy.data.objects.new(source_name + (suffix if role == "clothing" else " • Reference"), mesh)
    result["_seamfit_source"] = source_name
    scene.collection.objects.link(result)
    result[ROLE] = role
    if role == "clothing":
        result[topology.STAMP] = stamp
        if not output and (fixed := fixed_vertices(obj)):
            result[PIN_IDS] = sorted(fixed)
            result[PIN_STAMP] = stamp
    result.matrix_world = evaluated.matrix_world.copy()
    if not mesh.polygons or abs(result.matrix_world.to_3x3().determinant()) < 1e-12:
        raise ValueError(f"{obj.name} needs faces and a nonzero object scale.")
    # Evaluated meshes reference data materials. Respect object-level overrides too.
    for i, slot in enumerate(evaluated.material_slots):
        if i < len(mesh.materials) and slot.link == 'OBJECT':
            mesh.materials[i] = slot.material
    result.color = obj.color
    return result


def bind(obj, rig):
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()
    obj.matrix_world = world
    modifier = obj.modifiers.new("Avatar armature", 'ARMATURE')
    modifier.object = rig
    modifier.use_bone_envelopes = False


def discard(scene):
    # Only dispose of objects generated for this session and owned by this scene.
    generated = [obj for obj in scene.objects if obj.get(ROLE) and len(obj.users_scene) == 1]
    for obj in generated:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data and not data.users:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Armature):
                bpy.data.armatures.remove(data)
    bpy.data.scenes.remove(scene)


def fresh_scene(source, name):
    scene = bpy.data.scenes.new(name)
    for field in ("system", "length_unit", "scale_length"):
        setattr(scene.unit_settings, field, getattr(source.unit_settings, field))
    return scene


def inputs(context):
    s = context.scene.seamfit
    if not s.body or s.body.name not in context.view_layer.objects:
        raise ValueError("Choose the avatar body in this view layer.")
    if not s.garment or s.garment == s.body or s.garment.name not in context.view_layer.objects:
        raise ValueError("Choose a clothing mesh in this view layer, separate from the body.")
    objs = [s.garment]
    if s.include_selected:
        objs += [o for o in context.selected_objects if o.type == 'MESH' and o not in (s.body, s.garment)]
    return objs


def check_clothing(garments, surface, settings):
    flagged = [(obj, set(suspect_vertices(obj, surface))) for obj in garments]
    settings.suspects = sum(len(ids) for _, ids in flagged)
    settings.fixed_suspects = sum(len(ids.intersection(fixed_vertices(obj))) for obj, ids in flagged)
    return flagged


def preview(context):
    source = context.scene
    s = source.seamfit
    objs = inputs(context)
    rig = target_rig(s.body)
    if s.pending:
        raise ValueError("Finish the guide pair or cancel its first point.")
    graph = context.evaluated_depsgraph_get()
    scene = fresh_scene(source, "Fitting • " + s.garment.name)
    try:
        p = scene.seamfit
        p.stage = 'FIT'
        p.origin = source
        p.rig = make_rig(scene, rig)
        p.body = snapshot(scene, s.body, graph, "body")
        # Copy the reference before switching scenes to retain evaluated modifiers and shape mix.
        garments = [snapshot(scene, obj, graph, "clothing") for obj in objs]
        for attr in ("clearance", "travel", "conform", "region", "match_distance"):
            setattr(p, attr, getattr(s, attr))
        context.window.scene = scene
        context.view_layer.update()
        bind(p.body, p.rig)
        p.rig.hide_set(True)
        tree = body_surface(p.body, p.region)
        for obj in garments:
            adjust(obj, tree, p, s.guides)
        whole_body = body_surface(p.body) if p.region else tree
        check_clothing(garments, whole_body, p)
        set_active(context, garments[0])
    except Exception:
        context.window.scene = source
        discard(scene)
        raise


def rwt_status(scene):
    if not hasattr(scene, "robust_weight_transfer_settings"):
        return "Enable Robust Weight Transfer"
    if hasattr(bpy.types, "WM_OT_install_rwt_dependencies"):
        return "Install dependencies in the SENT tab"
    try:
        bpy.ops.object.skin_weight_transfer.get_rna_type()
    except (AttributeError, RuntimeError, KeyError):
        return "Enable Robust Weight Transfer"
    return ""


def clean_weights(obj, rig):
    deform = {b.name for b in rig.data.bones if b.use_deform}
    indices = {g.index for g in obj.vertex_groups if g.name in deform}
    missing = 0
    for v in obj.data.vertices:
        influences = [(g.group, g.weight) for g in v.groups if g.group in indices and math.isfinite(g.weight) and g.weight > 0]
        influences.sort(key=lambda x: -x[1])
        keep = influences[:4]
        total = sum(w for _, w in keep)
        if not total:
            missing += 1
            continue
        for i, _ in influences[4:]:
            obj.vertex_groups[i].remove([v.index])
        for i, w in keep:
            obj.vertex_groups[i].add([v.index], w / total, 'REPLACE')
    if missing:
        raise ValueError(f"{obj.name} has {missing} unweighted vertices. Adjust the fit or increase Match distance.")


def finish(context):
    fit_scene = context.scene
    p = fit_scene.seamfit
    garments = clothes(fit_scene)
    if not garments or not p.body or not p.rig:
        raise ValueError("The fitting objects are missing. Return to the source and rebuild the preview.")
    if target_rig(p.body) != p.rig:
        raise ValueError("Restore the preview body’s Armature modifier before finishing.")
    problem = rwt_status(fit_scene)
    if problem:
        raise ValueError(problem + ", then try again.")
    graph = context.evaluated_depsgraph_get()
    result = fresh_scene(fit_scene, "Export • " + garments[0].get("_seamfit_source", garments[0].name))
    try:
        r = result.seamfit
        r.stage = 'EXPORT'
        r.origin = p.origin
        r.rig = make_rig(result, p.rig, output=True)
        body = snapshot(result, p.body, graph, "body")
        copies = [snapshot(result, o, graph, "clothing", output=True) for o in garments]
        context.window.scene = result
        context.view_layer.update()
        bind(body, r.rig)
        cfg = result.robust_weight_transfer_settings
        cfg.source_object = body
        cfg.apply_to_selected = False
        cfg.group_selection = 'DEFORM_POSE_BONES'
        cfg.max_distance = p.match_distance
        cfg.use_deformed_source = False
        cfg.use_deformed_target = False
        cfg.draw_matched = False
        cfg.enforce_four_bone_limit = True
        cfg.num_limit_groups = 4
        context.view_layer.update()
        for obj in copies:
            obj.vertex_groups.clear()
            set_active(context, obj)
            # Surface mode supports tiny accessories below the point-cloud neighbor count.
            cfg.inpaint_mode = 'SURFACE' if len(obj.data.vertices) < 32 else 'POINT'
            if not bpy.ops.object.skin_weight_transfer.poll():
                raise ValueError("Robust Weight Transfer cannot run. Check its dependencies in the SENT tab.")
            try:
                status = bpy.ops.object.skin_weight_transfer('EXEC_DEFAULT')
            except RuntimeError as exc:
                raise ValueError(f"Transfer failed on {obj.name}. Check the fit of loose parts or increase Match distance, then retry.") from exc
            if 'FINISHED' not in status:
                raise ValueError("Weight transfer stopped. Check Match distance and loose garment pieces.")
            clean_weights(obj, r.rig)
            topology.verify(obj, obj.data)
            bind(obj, r.rig)
        cfg.source_object = None
        mesh = body.data
        bpy.data.objects.remove(body, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        set_active(context, copies[0])
        for o in [*copies, r.rig]:
            o.select_set(True)
    except Exception:
        context.window.scene = fit_scene
        discard(result)
        raise
    # A user may have added work to the fitting scene. Preserve that scene in that case.
    if all(o.get(ROLE) in {"rig", "body", "clothing"} for o in fit_scene.objects) and not any(
            w.scene == fit_scene for w in context.window_manager.windows):
        discard(fit_scene)
