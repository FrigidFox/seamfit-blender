"""World-space garment fitting. Geometry is evaluated in bind pose."""
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np


def body_surface(body, region=""):
    mesh = body.data
    matrix = body.matrix_world
    coords = [matrix @ v.co for v in mesh.vertices]
    mesh.calc_loop_triangles()
    faces = [tuple(t.vertices) for t in mesh.loop_triangles]
    if region:
        group = body.vertex_groups.get(region)
        if group is None:
            raise ValueError("Choose an existing body vertex group or clear Fit region.")
        allowed = {v.index for v in mesh.vertices
                   if any(g.group == group.index and g.weight >= 0.25 for g in v.groups)}
        faces = [face for face in faces if all(i in allowed for i in face)]
    if not faces:
        raise ValueError("The fit region has no faces. Choose a larger region or clear it.")
    if matrix.to_3x3().determinant() < 0:
        faces = [tuple(reversed(face)) for face in faces]
    return Surface(coords, faces)


class Surface:
    def __init__(self, coords, faces):
        self.coords = coords
        self.faces = faces
        self.tree = BVHTree.FromPolygons(coords, faces)


def guide_positions(points, guides):
    """Interpolate artist-supplied displacements in the garment's original space."""
    if not guides:
        return points
    origins = np.array([g.start[:] for g in guides])
    moves = np.array([g.end[:] for g in guides]) - origins
    result = points.copy()
    for start in range(0, len(points), 2048):
        p = points[start:start + 2048]
        delta = p[:, None, :] - origins
        distance_sq = np.einsum("ijk,ijk->ij", delta, delta)
        weights = 1.0 / np.maximum(distance_sq, 1e-14)
        result[start:start + len(p)] += weights @ moves / weights.sum(axis=1)[:, None]
    return result


def signed_gap(point, tree):
    contact, normal, _, distance = tree.tree.find_nearest(point)
    if contact is None:
        raise ValueError("The body has no usable surface near the garment.")
    along_normal = (point - contact).dot(normal)
    return along_normal, normal


def adjust(obj, tree, settings, guides=(), tighten=True):
    matrix = obj.matrix_world
    inverse = matrix.inverted()
    mesh = obj.data
    original = np.array([matrix @ v.co for v in mesh.vertices])
    positions = guide_positions(original, guides)
    offsets = np.empty_like(positions)
    for i, p in enumerate(positions):
        gap, normal = signed_gap(Vector(p), tree)
        travel = settings.clearance - gap
        if travel < 0:
            travel *= settings.conform if tighten else 0
        offsets[i] = np.asarray(normal) * np.clip(travel, -settings.travel, settings.travel)
    # Smooth the displacement field, retaining seams and modeled wrinkles.
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edges)
    left, right = edges[::2], edges[1::2]
    counts = np.bincount(edges, minlength=len(positions))
    for _ in range(3):
        summed = np.zeros_like(offsets)
        np.add.at(summed, left, offsets[right])
        np.add.at(summed, right, offsets[left])
        linked = counts > 0
        offsets[linked] = 0.6 * offsets[linked] + 0.4 * summed[linked] / counts[linked, None]
    for i, vert in enumerate(mesh.vertices):
        p = Vector(positions[i] + offsets[i])
        gap, normal = signed_gap(p, tree)
        budget = max(0, settings.travel - float(np.linalg.norm(offsets[i])))
        p += normal * min(budget, max(0, settings.clearance - gap))
        vert.co = inverse @ p
    mesh.update()
    repair_crossings(obj, tree, positions, settings)


def crossings(obj, surface):
    mesh = obj.data
    mesh.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
    return points, triangles, tree.overlap(surface.tree)


def repair_crossings(obj, surface, origins, settings):
    # A coarse face can cut the body even when every corner is outside.
    # Translate its corners together so the patch keeps its local shape.
    inverse = obj.matrix_world.inverted()
    points, triangles, hits = crossings(obj, surface)
    for _ in range(4):
        if not hits:
            break
        shifts = {}
        for ti, bi in hits:
            ids = triangles[ti]
            a, b, c = (points[i] for i in ids)
            normal = (b - a).cross(c - a).normalized()
            body = [surface.coords[i] for i in surface.faces[bi]]
            bn = (body[1] - body[0]).cross(body[2] - body[0])
            if normal.dot(bn) < 0:
                normal.negate()
            depth = max((q - a).dot(normal) for q in body)
            step = min(max(0, depth) + max(settings.clearance, 1e-5),
                       0.3 * max((b-a).length, (c-a).length))
            for i in ids:
                if i not in shifts or step > shifts[i][0]:
                    shifts[i] = step, normal
        old = {i: obj.data.vertices[i].co.copy() for i in shifts}
        for i, (step, normal) in shifts.items():
            origin = Vector(origins[i])
            delta = points[i] + normal * step - origin
            if delta.length > settings.travel:
                delta = delta.normalized() * settings.travel
            obj.data.vertices[i].co = inverse @ (origin + delta)
        obj.data.update()
        points, triangles, next_hits = crossings(obj, surface)
        if len(next_hits) >= len(hits):
            for i, co in old.items():
                obj.data.vertices[i].co = co
            obj.data.update()
            break
        hits = next_hits


def suspect_vertices(obj, tree):
    points, triangles, hits = crossings(obj, tree)
    flagged = {i for i, point in enumerate(points) if signed_gap(point, tree)[0] < -1e-5}
    for ti, _ in hits:
        flagged.update(triangles[ti])
    return sorted(flagged)
