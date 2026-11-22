"""Run in a disposable graphical Blender with --enable-event-simulate and the example open."""

import sys
import traceback
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime import load_addons

sf = load_addons()
if bpy.context.scene.name != "Hock gaiter • Source":
    raise RuntimeError("Open the generated Hock-gaiter.blend example for this check.")
steps = iter(
    ("open", "start", "pick garment", "pick body", "verify", "remove", "finish")
)
events = {}


def tick():
    try:
        phase = next(steps)
        window = bpy.context.window_manager.windows[0]
        area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
        region = next(r for r in area.regions if r.type == "WINDOW")
        sidebar = next(r for r in area.regions if r.type == "UI")
        with bpy.context.temp_override(window=window, area=area, region=region):
            s = bpy.context.scene.seamfit
            if phase == "open":
                area.spaces.active.show_region_ui = True
                sidebar.active_panel_category = "Seamfit"
                s.show_guides = True
            elif phase == "start":
                assert bpy.ops.seamfit.add_guide("INVOKE_DEFAULT") == {"RUNNING_MODAL"}
                for name, height in (("pick garment", 0.46), ("pick body", 0.54)):
                    obj = s.garment if name == "pick garment" else s.body
                    vs = [v for v in obj.data.vertices if abs(v.co.z - height) < 0.005]
                    # Aim through the ring center for a reliable hit at this height.
                    center = sum((v.co for v in vs), vs[0].co.copy() * 0) / len(vs)
                    xy = location_3d_to_region_2d(
                        region, area.spaces.active.region_3d, obj.matrix_world @ center
                    )
                    events[name] = (round(region.x + xy.x), round(region.y + xy.y))
            elif phase in events:
                assert s.pending
                if phase == "pick body":
                    assert s.picked
                x, y = events[phase]
                for value in ("PRESS", "RELEASE"):
                    window.event_simulate(type="LEFTMOUSE", value=value, x=x, y=y)
            elif phase == "verify":
                assert (
                    not s.pending
                    and len(s.guides) == 1
                    and (Vector(s.guides[0].end) - Vector(s.guides[0].start)).length
                    > 0.01
                )
            elif phase == "remove":
                assert bpy.ops.seamfit.remove_guide() == {"FINISHED"} and not s.guides
            elif phase == "finish":
                print(
                    "PASS native viewport raycast pair, overlay redraw and removal",
                    flush=True,
                )
                bpy.ops.wm.quit_blender()
                return None
        return 0.7
    except Exception:
        traceback.print_exc()
        print("FAIL interactive guide test", flush=True)
        bpy.ops.wm.quit_blender()
        return None


bpy.app.timers.register(tick, first_interval=2.0)
