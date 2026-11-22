import textwrap
import traceback
import bmesh
import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, IntProperty, PointerProperty, StringProperty)
from bpy_extras import view3d_utils
from bpy_extras.io_utils import ExportHelper
from . import guides, session, lining
from .fit import adjust, body_surface, PIN_IDS, PIN_STAMP

RWT_RELEASE = "https://github.com/sentfromspacevr/robust-weight-transfer/releases/tag/v1.1.9"


def mesh_only(self, obj):
    return obj.type == 'MESH'


def clear_guides(self, context):
    self.guides.clear()
    self.region = ""


class SF_Guide(bpy.types.PropertyGroup):
    start: FloatVectorProperty(size=3)
    end: FloatVectorProperty(size=3)


class SF_Settings(bpy.types.PropertyGroup):
    stage: EnumProperty(items=[('SETUP', "Setup", ""), ('FIT', "Review", ""), ('EXPORT', "Export", "")])
    body: PointerProperty(name="Avatar body", type=bpy.types.Object, poll=mesh_only, update=clear_guides,
                          description="Weighted target body mesh in its bind pose")
    garment: PointerProperty(name="Clothing", type=bpy.types.Object, poll=mesh_only, update=clear_guides,
                             description="Main garment, roughly aligned to the target avatar")
    include_selected: BoolProperty(name="Include other selected meshes",
                                   description="Fit the other selected meshes together with the clothing. The chosen body is excluded")
    clearance: FloatProperty(name="Body clearance", default=0.003, min=0, soft_max=0.03,
                             subtype='DISTANCE', unit='LENGTH', precision=4,
                             description="Desired space above the body surface")
    travel: FloatProperty(name="Max correction", default=0.12, min=0.000001, soft_max=0.5,
                          subtype='DISTANCE', unit='LENGTH', description="Maximum per-vertex surface correction after guide alignment")
    conform: FloatProperty(name="Pull loose fabric closer", subtype='FACTOR', default=0.0,
                           min=0, max=1, description="Zero preserves loose fabric. One brings fabric toward the clearance distance")
    match_distance: FloatProperty(name="Match distance", default=0.05, min=0.00001, soft_max=0.25,
                                  unit='LENGTH', subtype='DISTANCE', description="Maximum distance Robust Weight Transfer uses to find a direct body match")
    region: StringProperty(name="Fit region", description="Optional body group. Fit against faces with all vertex weights at least 0.25 in this group")
    guides: CollectionProperty(type=SF_Guide)
    pending: BoolProperty(default=False, options={'SKIP_SAVE'})
    picked: BoolProperty(options={'SKIP_SAVE'})
    picked_point: FloatVectorProperty(size=3, options={'SKIP_SAVE'})
    origin: PointerProperty(type=bpy.types.Scene)
    rig: PointerProperty(type=bpy.types.Object)
    lining_suspects: IntProperty(default=0)
    fixed_suspects: IntProperty(default=0)
    suspects: IntProperty(default=-1)
    advanced: BoolProperty(name="More fit options", default=False)
    show_guides: BoolProperty(name="Alignment guides", default=False)
    message: StringProperty()


class SF_OT_guide(bpy.types.Operator):
    bl_idname = "seamfit.add_guide"
    bl_label = "Pick guide pair"
    bl_description = "Click a landmark on the garment, then its intended location on the body. Orbit between clicks"
    bl_options = {'UNDO', 'BLOCKING'}

    def end_pick(self, context):
        self.settings.pending = False
        self.settings.picked = False
        self.area.header_text_set(None)
        context.window.cursor_modal_restore()
        self.area.tag_redraw()

    def invoke(self, context, event):
        self.settings = context.scene.seamfit
        try:
            session.inputs(context)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.area = context.area
        self.region = next(r for r in self.area.regions if r.type == 'WINDOW')
        self.start = None
        self.settings.pending = True
        self.area.header_text_set("Click a point on the clothing   •   Esc to cancel")
        context.window.cursor_modal_set('CROSSHAIR')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'} or context.scene.seamfit != self.settings:
            self.end_pick(context)
            return {'CANCELLED'}
        if event.type != 'LEFTMOUSE' or event.value != 'PRESS':
            return {'PASS_THROUGH'}
        region = self.region
        xy = (event.mouse_x - region.x, event.mouse_y - region.y)
        if not (0 <= xy[0] < region.width and 0 <= xy[1] < region.height):
            return {'RUNNING_MODAL'}
        view = self.area.spaces.active.region_3d
        obj = self.settings.garment if self.start is None else self.settings.body
        if not obj:
            self.end_pick(context)
            return {'CANCELLED'}
        obj = obj.evaluated_get(context.evaluated_depsgraph_get())
        matrix = obj.matrix_world
        inv = matrix.inverted_safe()
        origin = view3d_utils.region_2d_to_origin_3d(region, view, xy)
        direction = view3d_utils.region_2d_to_vector_3d(region, view, xy)
        hit, point, _, _ = obj.ray_cast(inv @ origin, inv.to_3x3() @ direction)
        if not hit:
            self.area.header_text_set(f"Missed {obj.name}. Click its surface   •   Esc to cancel")
            return {'RUNNING_MODAL'}
        if self.start is None:
            self.start = matrix @ point
            self.settings.picked = True
            self.settings.picked_point = self.start
            self.area.tag_redraw()
            self.area.header_text_set("Click the matching point on the body   •   Esc to cancel")
            return {'RUNNING_MODAL'}
        guide = self.settings.guides.add()
        guide.start = self.start
        guide.end = matrix @ point
        self.end_pick(context)
        return {'FINISHED'}

    def cancel(self, context):
        self.end_pick(context)


class SF_OT_remove_guide(bpy.types.Operator):
    bl_idname = "seamfit.remove_guide"
    bl_label = "Remove last guide"
    bl_options = {'UNDO'}

    def execute(self, context):
        guides = context.scene.seamfit.guides
        if guides:
            guides.remove(len(guides) - 1)
        return {'FINISHED'}


class SF_Action:
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.scene.seamfit.stage == cls.stage

    def execute(self, context):
        settings = context.scene.seamfit
        settings.message = ""
        try:
            context.window.cursor_set('WAIT')
            self.run(context)
        except Exception as exc:
            traceback.print_exc()
            settings.message = str(exc).strip() or type(exc).__name__
            self.report({'ERROR'}, settings.message)
            return {'CANCELLED'}
        finally:
            context.window.cursor_set('DEFAULT')
        return {'FINISHED'}


def protection_target(context):
    s = context.scene.seamfit
    obj = context.active_object
    if s.stage == 'SETUP':
        if s.include_selected and obj and obj.type == 'MESH' and obj != s.body and obj.select_get():
            return obj
        return s.garment
    if s.stage == 'FIT' and obj and obj.get(session.ROLE) == "clothing":
        return obj
    return None


class SF_OT_protect(bpy.types.Operator):
    bl_idname = "seamfit.protect"
    bl_label = "Choose lining faces"
    follow_shell: BoolProperty(default=True, options={'SKIP_SAVE', 'HIDDEN'})
    bl_description = "Select inner faces that should follow the outer layer"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = protection_target(context)
        return obj is not None and obj.name in context.view_layer.objects and (
            context.mode == 'OBJECT' or (context.mode == 'EDIT_MESH' and
            len(context.objects_in_mode) == 1 and context.edit_object == obj))

    def execute(self, context):
        obj = protection_target(context)
        if context.mode == 'OBJECT':
            others = [o for o in context.selected_objects if o != obj]
            stored = obj.get(PIN_STAMP)
            reuse = bool(stored) and stored == session.topology.fingerprint(obj.data)
            session.set_active(context, obj)
            bpy.ops.object.mode_set(mode='EDIT')
            for other in others:
                other.select_set(True)
            bpy.ops.mesh.select_mode(type='FACE')
            bpy.ops.mesh.select_all(action='DESELECT')
            mesh = bmesh.from_edit_mesh(obj.data)
            if reuse:
                fixed = set(obj.get(PIN_IDS, ()))
                for face in mesh.faces:
                    if not face.hide and all(v.index in fixed for v in face.verts):
                        face.select_set(True)
                bmesh.update_edit_mesh(obj.data, destructive=False)
        else:
            bpy.ops.object.mode_set(mode='OBJECT')
            fixed = sorted({i for face in obj.data.polygons if face.select and not face.hide for i in face.vertices})
            lining.clear_binding(obj)
            obj[lining.FOLLOW] = bool(fixed and self.follow_shell)
            if fixed:
                obj[PIN_IDS] = fixed
                obj[PIN_STAMP] = session.topology.fingerprint(obj.data)
            else:
                obj.pop(PIN_IDS, None)
                obj.pop(PIN_STAMP, None)
            if context.scene.seamfit.stage == 'FIT':
                context.scene.seamfit.suspects = -1
        return {'FINISHED'}


def protection_controls(layout, context):
    obj = protection_target(context)
    if obj is None:
        return
    editing = context.mode == 'EDIT_MESH'
    count = len(obj.get(PIN_IDS, ()))
    label = "Save lining faces" if editing else "Choose lining faces"
    if context.scene.seamfit.include_selected:
        layout.label(text=obj.name)
    layout.operator("seamfit.protect", text=label, icon='MOD_SOLIDIFY').follow_shell = True
    if editing:
        note(layout, context, "Select the inner layer only, then save. Leave the outside and connecting rim unselected.")
    elif count:
        if obj.get(lining.FOLLOW):
            layout.label(text=f"{count:,} vertices follow the outer fabric")
        else:
            note(layout, context, "Old fixed selection: choose lining faces and save to make it follow.")


class SF_OT_preview(SF_Action, bpy.types.Operator):
    bl_idname = "seamfit.preview"
    bl_label = "Fit clothing"
    bl_description = "Fit evaluated copies of the selected garments in a separate scene"
    stage = 'SETUP'

    def run(self, context):
        session.preview(context)


class SF_OT_check(SF_Action, bpy.types.Operator):
    bl_idname = "seamfit.check"
    bl_label = "Recheck fit"
    bl_description = "Check garment vertices against the nearest body normal. Select flagged vertices for inspection in Edit Mode"
    stage = 'FIT'

    def run(self, context):
        s = context.scene.seamfit
        tree = body_surface(s.body)
        first = None
        for obj, flagged in session.check_clothing(session.clothes(context.scene), tree, s):
            for poly in obj.data.polygons:
                poly.select = False
            for edge in obj.data.edges:
                edge.select = False
            for v in obj.data.vertices:
                v.select = v.index in flagged
            if flagged and first is None:
                first = obj
        if first:
            session.set_active(context, first)
            context.tool_settings.mesh_select_mode = (True, False, False)


class SF_OT_relieve(SF_Action, bpy.types.Operator):
    bl_idname = "seamfit.relieve"
    bl_label = "Fix clipping"
    bl_description = "Apply another outward clearance pass to the current clothing"
    bl_options = {'UNDO'}
    stage = 'FIT'

    def run(self, context):
        s = context.scene.seamfit
        tree = body_surface(s.body, s.region)
        for obj in session.clothes(context.scene):
            adjust(obj, tree, s, tighten=False)
        whole_body = body_surface(s.body) if s.region else tree
        previous = s.suspects
        session.check_clothing(session.clothes(context.scene), whole_body, s)
        remaining = s.suspects
        if remaining and remaining >= previous > 0:
            self.report({'WARNING'}, "Some fabric still crosses the body. Click Recheck fit and enter Edit Mode to adjust the selected area.")


class SF_OT_finish(SF_Action, bpy.types.Operator):
    bl_idname = "seamfit.finish"
    bl_label = "Bind clothing to rig"
    bl_description = "Run Robust Weight Transfer, verify every vertex and build a clean export scene"
    stage = 'FIT'

    def run(self, context):
        session.finish(context)


class SF_OT_source(bpy.types.Operator):
    bl_idname = "seamfit.source"
    bl_label = "Return to source"
    bl_description = "Open the original scene. The current scene remains accessible in the Blender scene selector"

    def execute(self, context):
        source = context.scene.seamfit.origin
        if not source:
            return {'CANCELLED'}
        context.window.scene = source
        return {'FINISHED'}


class SF_OT_export(bpy.types.Operator, ExportHelper):
    bl_idname = "seamfit.export"
    bl_label = "Export clothing FBX"
    bl_description = "Write the fitted clothing and target skeleton for Unity"
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    def invoke(self, context, event):
        self.filepath = bpy.path.clean_name(context.scene.name.replace("Export • ", "")) + ".fbx"
        return super().invoke(context, event)

    def execute(self, context):
        scene = context.scene
        garments = session.clothes(scene)
        rig = scene.seamfit.rig
        if scene.seamfit.stage != 'EXPORT' or not rig or not garments or context.mode != 'OBJECT':
            self.report({'ERROR'}, "Open the export scene in Object Mode.")
            return {'CANCELLED'}
        graph = context.evaluated_depsgraph_get()
        try:
            for obj in garments:
                session.topology.verify(obj, obj.data)
                session.topology.verify(obj, obj.evaluated_get(graph).data)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        items = [rig, *garments]
        hidden = [o.name for o in items if o.name not in context.view_layer.objects
                  or not o.visible_get(view_layer=context.view_layer) or o.hide_select]
        if hidden:
            self.report({'ERROR'}, "Show and unlock all outfit objects before export: " + ", ".join(hidden))
            return {'CANCELLED'}
        selected, active = list(context.selected_objects), context.view_layer.objects.active
        try:
            session.set_active(context, rig)
            for obj in items:
                obj.select_set(True)
            return bpy.ops.export_scene.fbx(filepath=self.filepath, use_selection=True,
                                            object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
                                            use_mesh_modifiers_render=False, use_mesh_modifiers=False,
                                            bake_anim=False, axis_forward='-Z', axis_up='Y',
                                            path_mode='AUTO')
        finally:
            for obj in context.selected_objects:
                obj.select_set(False)
            for obj in selected:
                obj.select_set(True)
            context.view_layer.objects.active = active


def note(layout, context, text, icon='NONE'):
    width = context.region.width / max(0.8, context.preferences.system.ui_scale)
    lines = textwrap.wrap(text, width=max(18, int((width - 50) / 7.5)))
    column = layout.column(align=True)
    for i, line in enumerate(lines):
        column.label(text=line, icon=icon if i == 0 or icon == 'NONE' else 'BLANK1')


def action(layout, identifier, icon, enabled=True):
    row = layout.row()
    row.scale_y = 1.45
    row.enabled = enabled
    row.operator(identifier, icon=icon)


class SF_PT_studio(bpy.types.Panel):
    bl_idname = "SF_PT_clothing_studio"
    bl_label = "Seamfit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Seamfit"

    def draw(self, context):
        layout = self.layout
        s = context.scene.seamfit
        row = layout.row(align=True)
        for key, label in (('SETUP', "1  Setup"), ('FIT', "2  Review"), ('EXPORT', "3  Export")):
            cell = row.row(align=True)
            cell.enabled = s.stage == key
            cell.label(text=label)
        if s.message:
            box = layout.box()
            box.alert = True
            note(box, context, s.message, 'ERROR')
        if context.mode != 'OBJECT' and not (context.mode == 'EDIT_MESH' and SF_OT_protect.poll(context)):
            note(layout, context, "Return to Object Mode to continue.", 'INFO')
        if s.stage == 'SETUP':
            if session.rwt_status(context.scene):
                setup = layout.box()
                note(setup, context, session.rwt_status(context.scene) + " before the weight step.", 'INFO')
                setup.operator("wm.url_open", text="5.1 dependency download", icon='URL').url = RWT_RELEASE
            box = layout.box()
            box.label(text="Choose your meshes", icon='OUTLINER_OB_MESH')
            box.label(text="Avatar body")
            box.prop(s, "body", text="")
            box.label(text="Clothing")
            box.prop(s, "garment", text="")
            protection_controls(box, context)
            action(layout, "seamfit.preview", 'MOD_CLOTH', bool(s.body and s.garment and s.body != s.garment))
            note(layout, context, "Place the clothing around the body first. Fit keeps its original mesh layout.")
            if s.include_selected and not s.advanced:
                note(layout, context, "Extra selected meshes are included. See More fit options for the list.")
            box = layout.box()
            box.prop(s, "advanced", emboss=False, icon='TRIA_DOWN' if s.advanced else 'TRIA_RIGHT')
            if s.advanced:
                box.prop(s, "include_selected")
                if s.include_selected:
                    try:
                        for obj in session.inputs(context):
                            box.label(text=obj.name, icon='MESH_DATA')
                    except ValueError:
                        pass
                box.prop(s, "clearance")
                box.prop(s, "conform", slider=True)
                box.prop(s, "travel")
                if s.body:
                    box.prop_search(s, "region", s.body, "vertex_groups")
                box.prop(s, "show_guides", emboss=False, icon='TRIA_DOWN' if s.show_guides else 'TRIA_RIGHT')
                if s.show_guides:
                    note(box, context, "For different proportions, pair landmarks such as cuffs, hips and hocks. Place guides on both sides.")
                    box.label(text=f"{len(s.guides)} guide pairs")
                    row = box.row(align=True)
                    row.enabled = bool(s.body and s.garment) and context.mode == 'OBJECT'
                    row.operator("seamfit.add_guide", icon='EYEDROPPER')
                    remove = row.row(align=True)
                    remove.enabled = bool(s.guides)
                    remove.operator("seamfit.remove_guide", text="", icon='LOOP_BACK')
        elif s.stage == 'FIT':
            box = layout.box()
            if s.suspects > 0:
                note(box, context, f"Last check flagged {s.suspects:,} vertices inside the body or belonging to crossing faces.", 'ERROR')
                if s.lining_suspects:
                    note(box, context, f"{s.lining_suspects:,} are on the lining. Adjust the outer fit or clearance to give it room.")
                if s.fixed_suspects:
                    note(box, context, f"{s.fixed_suspects:,} flagged vertices are protected and stay in place.")
                action(box, "seamfit.relieve", 'MOD_DISPLACE', s.fixed_suspects < s.suspects)
            elif s.suspects == 0:
                note(box, context, "Last check found no body crossings or inside vertices. Inspect the waistband and hems.", 'CHECKMARK')
            else:
                note(box, context, "Inspect the fit, then check for clipping.")
            box.operator("seamfit.check", icon='VIEWZOOM')
            protection_controls(box, context)
            problem = session.rwt_status(context.scene)
            if problem:
                note(layout, context, problem, 'INFO')
                layout.operator("wm.url_open", text="Get Robust Weight Transfer", icon='URL').url = RWT_RELEASE
            action(layout, "seamfit.finish", 'ARMATURE_DATA', not problem)
            details = layout.box()
            details.prop(s, "advanced", text="Adjust fit or transfer", emboss=False, icon='TRIA_DOWN' if s.advanced else 'TRIA_RIGHT')
            if s.advanced:
                details.prop(s, "clearance")
                if s.suspects <= 0:
                    details.operator("seamfit.relieve", icon='MOD_DISPLACE')
                details.prop(s, "match_distance")
        else:
            garments = session.clothes(context.scene)
            box = layout.box()
            box.label(text="Outfit ready", icon='CHECKMARK')
            for obj in garments:
                box.label(text=obj.name, icon='MESH_DATA')
            if s.rig:
                box.label(text=s.rig.name, icon='ARMATURE_DATA')
            note(box, context, "Weights verified at transfer. Pose the rig to inspect the outfit before exporting.")
            action(layout, "seamfit.export", 'EXPORT', context.mode == 'OBJECT')
        if s.stage != 'SETUP' and s.origin:
            layout.operator("seamfit.source", icon='BACK')


CLASSES = (SF_Guide, SF_Settings, SF_OT_guide, SF_OT_remove_guide, SF_OT_protect, SF_OT_preview,
           SF_OT_check, SF_OT_relieve, SF_OT_finish, SF_OT_source, SF_OT_export, SF_PT_studio)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.seamfit = PointerProperty(type=SF_Settings)
    guides.register()


def unregister():
    guides.unregister()
    del bpy.types.Scene.seamfit
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
