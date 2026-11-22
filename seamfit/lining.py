"""Bind lining vertices to points on the outer garment's rest cage."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

FOLLOW = "_seamfit_follow_shell"
TRIANGLES = "_seamfit_shell_triangles"
WEIGHTS = "_seamfit_shell_weights"


def clear_binding(obj):
    for key in (TRIANGLES, WEIGHTS):
        obj.pop(key, None)


def anchors(obj, points, followers):
    """Pair once per preview; retain triangle indices across repairs and reloads."""
    if TRIANGLES in obj and WEIGHTS in obj:
        return (np.array(obj[TRIANGLES], dtype=int).reshape(-1, 3),
                np.array(obj[WEIGHTS], dtype=float).reshape(-1, 3))
    mesh = obj.data
    mesh.calc_loop_triangles()
    mask = np.zeros(len(points), dtype=bool)
    mask[followers] = True
    triangles = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=int)
    triangles = triangles[~mask[triangles].any(axis=1)]
    a, b, c = points[triangles].transpose(1, 0, 2)
    triangles = triangles[np.linalg.norm(np.cross(b-a, c-a), axis=1) > 1e-16]
    if not len(triangles):
        raise ValueError(f"{obj.name}: leave the outer layer unselected so the lining can follow it.")
    tree = BVHTree.FromPolygons(points.tolist(), triangles.tolist(), all_triangles=True)
    hits = [tree.find_nearest(points[i]) for i in followers]
    indices = triangles[[hit[2] for hit in hits]]
    a, b, c = points[indices].transpose(1, 0, 2)
    e, f = b-a, c-a
    n = np.cross(e, f)
    d = np.array([hit[0] for hit in hits])-a
    norm_sq = (n*n).sum(axis=1)
    v = (np.cross(d, f)*n).sum(axis=1) / norm_sq
    w = (np.cross(e, d)*n).sum(axis=1) / norm_sq
    weights = np.clip(np.column_stack((1-v-w, v, w)), 0, 1)
    weights /= weights.sum(axis=1, keepdims=True)
    obj[TRIANGLES] = indices.ravel().tolist()
    obj[WEIGHTS] = weights.ravel().tolist()
    return indices, weights


def frames(tris):
    x = tris[:, 1] - tris[:, 0]
    z = np.cross(x, tris[:, 2] - tris[:, 0])
    length = np.linalg.norm(z, axis=1)
    valid = length > 1e-16
    z[valid] /= length[valid, None]
    x[valid] /= np.linalg.norm(x[valid], axis=1)[:, None]
    return np.stack((x, np.cross(z, x), z), axis=1), valid


def follow(obj, original, followers, indices, weights):
    # Transport the initial offset in an orthonormal triangle frame. This
    # preserves thickness even when the outer patch tilts or stretches.
    current = np.array([obj.matrix_world @ v.co for v in obj.data.vertices])
    before, after = original[indices], current[indices]
    rest_frame, rest_valid = frames(before)
    frame, valid = frames(after)
    offset = original[followers] - np.einsum("ij,ijk->ik", weights, before)
    local = np.einsum("ijk,ik->ij", rest_frame, offset)
    valid &= rest_valid
    offset[valid] = np.einsum("ij,ijk->ik", local[valid], frame[valid])
    targets = np.einsum("ij,ijk->ik", weights, after) + offset
    inverse = obj.matrix_world.inverted()
    for i, point in zip(followers, targets):
        obj.data.vertices[int(i)].co = inverse @ Vector(point)
    obj.data.update()


def follow_weights(obj, preview, followers):
    indices = np.array(preview[TRIANGLES], dtype=int).reshape(-1, 3)
    weights = np.array(preview[WEIGHTS]).reshape(-1, 3)
    for i, corners, bary in zip(followers, indices, weights):
        blend = {}
        for corner, factor in zip(corners, bary):
            for g in obj.data.vertices[int(corner)].groups:
                blend[g.group] = blend.get(g.group, 0) + factor * g.weight
        for group in [g.group for g in obj.data.vertices[i].groups]:
            obj.vertex_groups[group].remove([i])
        for group, weight in blend.items():
            if weight > 0:
                obj.vertex_groups[group].add([i], weight, 'REPLACE')
