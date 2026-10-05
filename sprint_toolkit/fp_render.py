r"""Render a Halo 1 first-person pose offline: the FP hands plus the weapon, as the player sees them.

Halo 1's FP view is the animation's own space: the camera sits at the origin looking down
+x, +y is left and +z up. gbxmodel vertices are stored in MODEL space (the bind pose the
node defaults describe), so a vertex is posed by  W_node(pose) * inverse(W_node(bind)).

Poses are dicts {H1 node name: (q (w,x,y,z), t (x,y,z) in world units)} of LOCAL transforms;
`compose` turns them into world transforms with the gbxmodel's parent links. Halo 1 tag
tag quaternions are stored INVERTED: they must be conjugated to compose as rotations
(`QUAT_CONVENTION` = -1). Checked on the Assault Rifle's idle: conjugated gives the familiar
view, gun lower right with its ammo display on top; as stored the gun points up at the
camera. Halo 3 stores the rotations themselves, so H3 -> H1 is a conjugation
(h1_fp_retarget.py).

    python fp_render.py --antr weapons\plasma_cannon\fp\fp --anim "first-person idle" \
                        --model weapons\plasma_cannon\fp\fp --out idle.png [--frame 0]
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.mod2 import mod2_def  # noqa: E402
from reclaimer.hek.defs.antr import antr_def  # noqa: E402
from reclaimer.animation.animation_decompilation import extract_animation  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')
HANDS = 'characters\\cyborg\\fp\\fp'
QUAT_CONVENTION = -1       # Halo 1 tags store the inverse rotation: conjugate to compose


def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw)


def qconj(q):
    return (q[0], -q[1], -q[2], -q[3])


def qrot(q, v):
    return qmul(qmul(q, (0.0,) + tuple(v)), qconj(q))[1:]


def xform(W, v):
    q, t = W
    r = qrot(q, v)
    return (r[0] + t[0], r[1] + t[1], r[2] + t[2])


def inverse(W):
    q, t = W
    qi = qconj(q)
    r = qrot(qi, t)
    return (qi, (-r[0], -r[1], -r[2]))


def compose(names, parents, local):
    """World transforms {name: (q, t)} from LOCAL ones, parents first."""
    out = {}
    for n, p in zip(names, parents):
        q, t = local[n]
        if QUAT_CONVENTION < 0:
            q = qconj(q)
        if p is None:
            out[n] = (q, tuple(t))
        else:
            pq, pt = out[p]
            r = qrot(pq, t)
            out[n] = (qmul(pq, q), (pt[0] + r[0], pt[1] + r[1], pt[2] + r[2]))
    return out


def load_model(rel):
    """(node names, parent names, bind local {name: (q,t)}, triangles [(3 verts, node, shader)])"""
    d = mod2_def.build(filepath=os.path.join(TAGS, rel + '.gbxmodel')).data.tagdata
    nodes = d.nodes.STEPTREE
    names = [n.name for n in nodes]
    parents = [names[n.parent_node] if n.parent_node >= 0 else None for n in nodes]
    bind = {n.name: ((n.rotation.w, n.rotation.i, n.rotation.j, n.rotation.k),
                     (n.translation.x, n.translation.y, n.translation.z)) for n in nodes}
    tris = []
    for g in d.geometries.STEPTREE[:1]:              # highest LOD only
        for p in g.parts.STEPTREE:
            vs = p.uncompressed_vertices.STEPTREE
            # ZONER parts index their vertices' nodes through a per-part table
            local = ([ln for ln in p.local_nodes][:p.local_node_count]
                     if p.flags.ZONER else None)

            def node(i):
                return i if i < 0 or local is None else local[i]
            idx = list(p.triangles.STEPTREE)
            strip = []
            for t in idx:
                strip.extend((t.v0_index, t.v1_index, t.v2_index))
            strip = [i for i in strip if i >= 0]
            for k in range(len(strip) - 2):          # triangle strip
                a, b, c = strip[k], strip[k + 1], strip[k + 2]
                if a == b or b == c or a == c:
                    continue
                if k % 2:
                    a, b = b, a
                tri = []
                for i in (a, b, c):
                    v = vs[i]
                    tri.append(((v.position_x, v.position_y, v.position_z),
                                ((node(v.node_0_index), v.node_0_weight),
                                 (node(v.node_1_index), v.node_1_weight))))
                tris.append((tri, p.shader_index))
    return names, parents, bind, tris


def anim_pose(antr_rel, anim_name, frame):
    """(node names, parent names, {node: (q, t wu)} LOCAL, frame count) from a Halo 1
    animation tag, raw tag quaternions. The hierarchy is the ANIMATION's: a weapon's FP
    model holds only its own nodes, rooted at e.g. `frame gun`, which the animation hangs
    off a wrist."""
    d = antr_def.build(filepath=os.path.join(TAGS, antr_rel + '.model_animations')).data.tagdata
    names = [a.name for a in d.animations.STEPTREE]
    jma = extract_animation(names.index(anim_name), d, write_jma=False)
    f = jma.frames[min(frame, len(jma.frames) - 1)]
    nn = [n.name for n in jma.nodes]
    par = [nn[n.parent_index] if 0 <= n.parent_index != i else None    # root: -1 or self
           for i, n in enumerate(jma.nodes)]
    local = {n.name: ((s.rot_w, s.rot_i, s.rot_j, s.rot_k),
                      (s.pos_x / 100.0, s.pos_y / 100.0, s.pos_z / 100.0))
             for n, s in zip(jma.nodes, f)}
    return nn, par, local, len(jma.frames)


def posed_tris(model, world, colour):
    """The model's triangles, skinned by WORLD node transforms {name: (q, t)}."""
    names, parents, bind, tris = model
    Wb = compose(names, parents, bind)
    M = {n: (world.get(n, Wb[n]), inverse(Wb[n])) for n in names}
    out = []
    for tri, shader in tris:
        pts = []
        for v, skin in tri:
            acc = [0.0, 0.0, 0.0]
            tot = 0.0
            for node, w in skin:
                if node < 0 or w <= 0.0:
                    continue
                wp, ib = M[names[node]]
                q = xform(wp, xform(ib, v))
                acc = [a + w * c for a, c in zip(acc, q)]
                tot += w
            pts.append(tuple(c / (tot or 1.0) for c in acc))
        out.append((pts, colour))
    return out


def render(groups, out, size=(960, 540), hfov=70.0, title='', eye=(0.0, 0.0, 0.0)):
    W, H = size
    f = (W / 2) / math.tan(math.radians(hfov) / 2)
    img = Image.new('RGB', size, (28, 30, 34))
    d = ImageDraw.Draw(img)
    light = (0.5, 0.3, 0.8)
    polys = []
    for tris in groups:
        for pts, col in tris:
            pts = [tuple(p[i] - eye[i] for i in range(3)) for p in pts]
            if any(p[0] <= 0.01 for p in pts):
                continue
            scr = [(W / 2 - f * p[1] / p[0], H / 2 - f * p[2] / p[0]) for p in pts]
            ux, uy, uz = (pts[1][i] - pts[0][i] for i in range(3))
            vx, vy, vz = (pts[2][i] - pts[0][i] for i in range(3))
            n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
            ln = math.sqrt(sum(c * c for c in n)) or 1.0
            sh = abs(sum(a * b for a, b in zip(n, light))) / ln
            depth = sum(p[0] for p in pts) / 3
            c = tuple(int(k * (0.35 + 0.65 * sh)) for k in col)
            polys.append((depth, scr, c))
    for depth, scr, c in sorted(polys, key=lambda x: -x[0]):
        d.polygon(scr, fill=c)
    if title:
        d.text((8, 8), title, fill=(230, 230, 230))
    img.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--antr', required=True)
    ap.add_argument('--anim', required=True)
    ap.add_argument('--model', help='weapon FP gbxmodel (tag path, no extension)')
    ap.add_argument('--frame', type=int, default=0)
    ap.add_argument('--out', required=True)
    ap.add_argument('--raw', action='store_true', help='compose the quaternions as stored')
    ap.add_argument('--eye', default='0,0,0', help='camera position, wu (e.g. -0.5,0,0.1)')
    ap.add_argument('--fov', type=float, default=70.0)
    a = ap.parse_args()
    global QUAT_CONVENTION
    if a.raw:
        QUAT_CONVENTION = 1
    nn, par, local, n = anim_pose(a.antr, a.anim, a.frame)
    world = compose(nn, par, local)
    groups = [posed_tris(load_model(HANDS), world, (200, 170, 120))]
    if a.model:
        groups.append(posed_tris(load_model(a.model), world, (110, 160, 230)))
    render(groups, a.out, hfov=a.fov, eye=tuple(float(c) for c in a.eye.split(',')), title='%s  %s  frame %d/%d' % (a.antr, a.anim, a.frame, n))
    print(a.out)


if __name__ == '__main__':
    main()
