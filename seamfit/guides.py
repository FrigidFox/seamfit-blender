"""Viewport annotations for landmark picking."""
import blf
import bpy
import gpu
from bpy_extras.view3d_utils import location_3d_to_region_2d
from gpu_extras.batch import batch_for_shader

_handle = None


def draw():
    context = bpy.context
    if not context.region_data or not context.scene:
        return
    s = context.scene.seamfit
    if s.stage != 'SETUP' or not s.show_guides:
        return
    def project(point):
        return location_3d_to_region_2d(context.region, context.region_data, point)

    points = []
    segments = []
    for i, guide in enumerate(s.guides, 1):
        a, b = project(guide.start), project(guide.end)
        if a is not None and b is not None:
            segments.extend((a, b))
        for xy, suffix in ((a, "A"), (b, "B")):
            if xy is not None:
                points.append((xy, f"{i}{suffix}"))
    if s.pending and s.picked:
        xy = project(s.picked_point)
        if xy is not None:
            points.append((xy, "A"))
    if not points:
        return
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader.bind()
    shader.uniform_float("color", (0.23, 0.89, 0.73, 1))
    if segments:
        batch_for_shader(shader, 'LINES', {"pos": segments}).draw(shader)
    ticks = []
    for p, label in points:
        x, y = p
        ticks.extend(((x-4, y), (x+4, y), (x, y-4), (x, y+4)))
        blf.position(0, x + 5, y + 4, 0)
        blf.size(0, 12)
        blf.color(0, 0.8, 1, 0.93, 1)
        blf.draw(0, label)
    shader.bind()
    batch_for_shader(shader, 'LINES', {"pos": ticks}).draw(shader)


def register():
    global _handle
    if not bpy.app.background:
        _handle = bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')


def unregister():
    global _handle
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, 'WINDOW')
        _handle = None
