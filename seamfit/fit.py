"""World-space garment fitting. Geometry is evaluated in bind pose."""
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np


def body_surface(body, region=""):
    mesh = body.data
    matrix = body.matrix_world
    coords = [matrix @ v.co for v in mesh.vertices]
    faces = [tuple(p.vertices) for p in mesh.polygons]
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
    return BVHTree.FromPolygons(coords, faces)


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
    contact, normal, _, distance = tree.find_nearest(point)
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


def suspect_vertices(obj, tree):
    matrix = obj.matrix_world
    return [v.index for v in obj.data.vertices
            if signed_gap(matrix @ v.co, tree)[0] < -1e-5]
