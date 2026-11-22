"""Check the indexed mesh cage before fitting, transfer, and FBX export."""
from array import array
from hashlib import sha256
import bpy

STAMP = "_seamfit_topology"


def fingerprint(mesh):
    digest = sha256(str(len(mesh.vertices)).encode("ascii"))
    for items, field, width in ((mesh.edges, "vertices", 2),
                                (mesh.loops, "vertex_index", 1),
                                (mesh.loops, "edge_index", 1),
                                (mesh.polygons, "loop_total", 1)):
        values = array("i", [0]) * (len(items) * width)
        items.foreach_get(field, values)
        digest.update(len(values).to_bytes(8, "little"))
        digest.update(values.tobytes())
    return digest.hexdigest()


def verify(obj, mesh):
    expected = obj.get(STAMP)
    if not expected:
        raise ValueError("Create a new fit from the source to verify this garment's topology.")
    if fingerprint(mesh) != expected:
        raise ValueError(f"{obj.name}: mesh connectivity changed. Undo the topology edit or fit again from the original.")


def clothing_mesh(obj, graph, *, output):
    expected = obj.get(STAMP) if output else fingerprint(obj.data)
    if output:
        verify(obj, obj.data)
    tmp = None
    try:
        # Subdivision is a display surface. Evaluate the original cage with its
        # authored shape mix and armature, keeping the source modifier untouched.
        ref = obj
        if not output and any(m.type == 'SUBSURF' and m.show_viewport for m in obj.modifiers):
            tmp = obj.copy()
            graph.scene.collection.objects.link(tmp)
            for mod in tmp.modifiers:
                if mod.type == 'SUBSURF':
                    mod.show_viewport = False
            graph.update()
            ref = tmp
        mesh = bpy.data.meshes.new_from_object(ref.evaluated_get(graph), preserve_all_data_layers=True, depsgraph=graph)
        if fingerprint(mesh) != expected:
            bpy.data.meshes.remove(mesh)
            raise ValueError(f"{obj.name}: an enabled modifier changes the mesh layout. Disable it on the garment, or apply it on a duplicate and fit that mesh.")
        return mesh, expected
    finally:
        if tmp:
            bpy.data.objects.remove(tmp, do_unlink=True)
