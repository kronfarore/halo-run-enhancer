r"""Runs INSIDE Blender (background) for h1_decimate.py -- never run it directly.

    blender -b --factory-startup -P h1_decimate_blend.py -- <in.json> <out.json>

in.json: {'verts': [[x, y, z, ni, nj, nk, u, v, node0, node1, w1], ...] (JMS units),
          'tris': [[region, shader, v0, v1, v2], ...], 'keep': fraction of all triangles,
          'lock': [shader indices kept whole], 'views': [[eye xyz, forward xyz, up xyz, weight]]
          (model space, JMS units), 'protect': decimate vertex-group factor, 'hfov' / 'vfov' deg}
out.json: the same 'verts' / 'tris' after Blender's collapse decimation.

Positions are welded per (position, node0, node1, w1) -- a moving part touching the body keeps
its own vertices. UVs ride on the corners (Blender's collapse keeps seams), normals are the
source's own, transferred back from the undecimated copy (nearest corner with the best matching
face normal: a thin wall never takes its far side's normal). Node weights are vertex groups.
PROTECTION: a vertex the player sees in first person (in one of the views' frustum, the ray from
the eye not blocked) gets the view's weight in group `protect`; the decimator collapses those
last. Locked shaders (displays, glows, decals: few triangles, exact UV islands) stay untouched.
"""
import json
import math
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

src, dst = sys.argv[sys.argv.index('--') + 1:][:2]
J = json.load(open(src))
V, T = J['verts'], J['tris']
lock = set(J.get('lock', ()))
COS3 = math.cos(math.radians(3.0))


def build(name, tris):
    """A mesh object from JMS triangles: welded positions, corner UVs + normals, node groups."""
    key2v, pos, vkey = {}, [], []
    faces, uvs, nrm, mat, reg = [], [], [], [], []
    for r, s, *vi in tris:
        f, fu, fn = [], [], []
        for i in vi:
            x = V[i]
            k = (x[0], x[1], x[2], x[8], x[9], x[10])
            if k not in key2v:
                key2v[k] = len(pos)
                pos.append(x[:3])
                vkey.append(x)
            f.append(key2v[k])
            fu.append((x[6], x[7]))
            fn.append(Vector(x[3:6]).normalized())
        if len(set(f)) < 3:
            continue
        faces.append(f)
        uvs += fu
        nrm += fn
        mat.append(s)
        reg.append(r)
    me = bpy.data.meshes.new(name)
    me.from_pydata(pos, [], faces)
    me.update()
    uv =me.uv_layers.new(name='uv')
    for li in range(len(me.loops)):
        uv.data[li].uv = uvs[li]
    me.normals_split_custom_set(nrm)
    ma = me.attributes.new('jms_shader', 'INT', 'FACE')
    ra = me.attributes.new('jms_region', 'INT', 'FACE')
    for i in range(len(faces)):
        ma.data[i].value = mat[i]
        ra.data[i].value = reg[i]
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    groups = {}
    for vi, x in enumerate(vkey):
        for n, w in ((int(x[8]), 1.0 - x[10]), (int(x[9]), x[10])):
            if n < 0 or w <= 0:
                continue
            g = groups.get(n)
            if g is None:
                g = groups[n] = ob.vertex_groups.new(name='n%d' % n)
            g.add([vi], w, 'REPLACE')
    return ob


bpy.ops.wm.read_factory_settings(use_empty=True)
free = [t for t in T if t[1] not in lock]
held = [t for t in T if t[1] in lock]
obs = []
if free:
    ob = build('free', free)
    nf = len(ob.data.polygons)
    want = J['keep'] * len(T) - len(held)
    ratio = max(0.02, min(1.0, want / float(nf)))
    if ratio < 1.0:
        ref = ob.copy()
        ref.data = ob.data.copy()
        bpy.context.scene.collection.objects.link(ref)
        # visibility from the first-person views (every triangle of the model blocks rays)
        me = ob.data
        P = [v.co.copy() for v in me.vertices]
        tree = BVHTree.FromPolygons(P, [list(p.vertices) for p in me.polygons])
        hh = math.tan(math.radians(J.get('hfov', 70.0) + 10) / 2)
        vh = math.tan(math.radians(J.get('vfov', 42.0) + 10) / 2)
        floor = J.get('floor', 0.0)
        wts = [floor] * len(P)
        for eye, fwd, up, w in J.get('views', ()):
            e, f, u = Vector(eye), Vector(fwd).normalized(), Vector(up).normalized()
            l = u.cross(f)
            for i, p in enumerate(P):
                if wts[i] >= w:
                    continue
                d = p - e
                z = d.dot(f)
                if z <= 0 or abs(d.dot(l)) / z > hh or abs(d.dot(u)) / z > vh:
                    continue
                dist = d.length
                hit = tree.ray_cast(e, d / dist, dist * 0.999)
                if hit[0] is None or (hit[0] - p).length < dist * 0.002:
                    wts[i] = w
        g = ob.vertex_groups.new(name='protect')
        for i, w in enumerate(wts):
            if w > 0:
                g.add([i], w, 'REPLACE')
        print('protected vertices: %d of %d' % (sum(1 for w in wts if w > floor), len(P)))
        m = ob.modifiers.new('dec', 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = ratio
        m.use_collapse_triangulate = True
        if any(wts):
            m.vertex_group = 'protect'
            m.invert_vertex_group = True
            m.vertex_group_factor = J.get('protect', 1.0)
        t = ob.modifiers.new('nrm', 'DATA_TRANSFER')
        t.object = ref
        t.use_loop_data = True
        t.data_types_loops = {'CUSTOM_NORMAL'}
        t.loop_mapping = 'NEAREST_POLYNOR'
    obs.append(ob)
if held:
    obs.append(build('held', held))

dg = bpy.context.evaluated_depsgraph_get()
outV, outT, index = [], [], {}
for ob in obs:
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    me.calc_loop_triangles()
    uv = me.uv_layers.active.data
    cn = me.corner_normals
    sha = me.attributes['jms_shader'].data
    rga = me.attributes['jms_region'].data
    gname = {g.index: g.name for g in oe.vertex_groups}
    for lt in me.loop_triangles:
        vs = []
        for li in lt.loops:
            vi = me.loops[li].vertex_index
            v = me.vertices[vi]
            nodes = sorted(((ge.weight, int(gname[ge.group][1:])) for ge in v.groups
                            if gname[ge.group].startswith('n') and ge.weight > 0), reverse=True)[:2]
            if not nodes:
                nodes = [(1.0, 0)]
            tot = sum(w for w, _n in nodes)
            n0 = nodes[0][1]
            n1, w1 = (nodes[1][1], nodes[1][0] / tot) if len(nodes) > 1 else (-1, 0.0)
            nv = Vector(cn[li].vector).normalized()
            u = (round(uv[li].uv[0], 6), round(uv[li].uv[1], 6))
            # one Halo 1 vertex per (vertex, uv, normal within 3 deg): corners of one smooth vertex
            # get slightly different transferred normals -- merged, their normals averaged below
            reps = index.setdefault((ob.name, vi), [])
            for r in reps:
                if r[0] == u and r[1].dot(nv) > COS3:
                    r[3].append(nv)
                    vs.append(r[2])
                    break
            else:
                outV.append([round(v.co.x, 5), round(v.co.y, 5), round(v.co.z, 5), 0.0, 0.0, 0.0,
                             u[0], u[1], n0, n1, round(w1, 5)])
                reps.append((u, nv, len(outV) - 1, [nv]))
                vs.append(len(outV) - 1)
        if len(set(vs)) == 3:
            outT.append((rga[lt.polygon_index].value, sha[lt.polygon_index].value, *vs))
for reps in index.values():
    for _u, _n, i, ns in reps:
        s = Vector((0.0, 0.0, 0.0))
        for n in ns:
            s += n
        s.normalize()
        outV[i][3:6] = [round(s.x, 5), round(s.y, 5), round(s.z, 5)]
json.dump({'verts': outV, 'tris': outT}, open(dst, 'w'))
print('h1_decimate_blend: %d -> %d triangles, %d -> %d corners' % (len(T), len(outT), len(V), len(outV)))
