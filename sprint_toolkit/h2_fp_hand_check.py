r"""Judge a Halo 2 port's first-person HANDS offline, from the source animations the port wrote
(h2_port_fp_anims: JMA 16394, absolute model-space frames) -- before a boot. The SAW rework
(2026-10-26) settled the Dervish's fingers this way: the user's 'fingers phase into the weapon'
was a count of hand vertices inside the gun, measured against the Chief's count in the same
animation (memory h2-saw-rework).

    python h2_fp_hand_check.py clip   <key> <species> <anim> [<anim> ...] [--hand l|r|both]
                                      [--fingers] [--step 4]
        per animation: the hand (or finger) vertices of the posed FP arms inside the posed FP
        gun (ray parity along +z), summed over every --step'th frame, and the worst frame.
    python h2_fp_hand_check.py render <key> <species> <anim> <frame> <out.png> [--fov 70]
        a flat-shaded picture of arms + gun at one frame: camera at the origin looking +x
        (+y left, +z up), the first-person view. Write it OUTSIDE the repo.

<anim> is the file stem after 'first-person ' (idle, posing var1, melee-strike-1, ...). The arms
are the config's fp_anims species 'arms' JMS, the gun the weapon_dir's render\*.jms. Read-only.
"""
import argparse
import glob
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h2_jms                                                      # noqa: E402
import ports_h2                                                    # noqa: E402
from h2_port_fp_anims import H2EK                                  # noqa: E402

FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')


def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz, aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw)


def qrot(q, v):
    w, x, y, z = q
    return qmul(qmul(q, (0.0,) + tuple(v)), (w, -x, -y, -z))[1:]


def key(name):
    """JMA / JMS node names differ in prefix ('frame gun', 'b_gun'): compare them bare."""
    s = name.lower()
    for p in ('frame ', 'frame_', 'b_'):
        if s.startswith(p):
            s = s[len(p):]
    return s.replace(' ', '_')


def read_jma(path, frame):
    """({node key: (quat wxyz, translation)}, frame count) of one frame of a JMA 16394."""
    L = [x.strip() for x in open(path, encoding='latin-1').read().split('\n')]
    n_frames, nn = int(L[2]), int(L[6])
    names = [L[7 + 2 * i] for i in range(nn)]
    at = 7 + 2 * nn + min(frame, n_frames - 1) * nn * 3
    out = {}
    for i in range(nn):
        t = [float(c) for c in L[at].split('\t')]
        x, y, z, w = [float(c) for c in L[at + 1].split('\t')]
        at += 3
        out[key(names[i])] = ((w, x, y, z), t)
    return out, n_frames


def posed_verts(m, pose, keep=None):
    """World positions of the JMS's vertices posed by `pose`; keep(node key) filters by the
    vertex's main influence."""
    keys = [key(n.name) for n in m.nodes]
    binds = [((n.rot[3], n.rot[0], n.rot[1], n.rot[2]), n.pos) for n in m.nodes]
    out = []
    for v in m.verts:
        if keep and not keep(keys[max(v.influences, key=lambda t: t[1])[0]]):
            out.append(None)
            continue
        acc = np.zeros(3)
        for ni, w in v.influences:
            p = pose.get(keys[ni])
            if p is None:
                acc += w * np.array(v.pos)
                continue
            qb, tb = binds[ni]
            qp, tp = p
            d = qrot(qmul(qp, (qb[0], -qb[1], -qb[2], -qb[3])), [v.pos[k] - tb[k] for k in range(3)])
            acc += w * np.array([tp[k] + d[k] for k in range(3)])
        out.append(acc)
    return out


def inside(points, tris):
    """Ray parity along +z of each point against triangles (n, 3, 3)."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    v0, v1 = c[:, :2] - a[:, :2], b[:, :2] - a[:, :2]
    d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    ok = np.abs(den) > 1e-12
    den = np.where(ok, den, 1)
    res = []
    for p in points:
        v2 = p[:2] - a[:, :2]
        d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
        u = np.where(ok, (d11 * d20 - d01 * d21) / den, -1)
        v = np.where(ok, (d00 * d21 - d01 * d20) / den, -1)
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1)
        z = a[:, 2] + u * (c[:, 2] - a[:, 2]) + v * (b[:, 2] - a[:, 2])
        res.append((hit & (z > p[2])).sum() % 2 == 1)
    return np.array(res, bool)


def paths(k, species):
    fa = ports_h2.load(k)['fp_anims']
    sp = fa['species'][species]
    gun = glob.glob(os.path.join(H2EK, 'data', fa['weapon_dir'], 'render', '*.jms'))
    if len(gun) != 1:
        raise SystemExit('%s: expected one FP weapon JMS under %s\\render, found %d'
                         % (k, fa['weapon_dir'], len(gun)))
    return sp['arms'], gun[0], os.path.join(H2EK, 'data', sp['source'], 'animations')


def anim_file(adir, an):
    for ext in ('.jmm', '.jmo', '.jmr'):
        p = os.path.join(adir, 'first-person %s%s' % (an, ext))
        if os.path.exists(p):
            return p
    raise SystemExit('no source animation "first-person %s" in %s' % (an, adir))


def clip(a):
    arms_p, gun_p, adir = paths(a.key, a.species)
    arms, gun = h2_jms.read(arms_p), h2_jms.read(gun_p)
    sides = ('l_', 'r_') if a.hand == 'both' else (a.hand + '_',)

    def keep(k):
        return k.startswith(sides) and (not a.fingers or any(f in k for f in FINGERS))
    what = 'finger' if a.fingers else 'hand'
    for an in a.anims:
        path = anim_file(adir, an)
        n = read_jma(path, 0)[1]
        tot, worst = 0, (0, 0)
        for f in range(0, n, a.step):
            pose = read_jma(path, f)[0]
            hv = [p for p in posed_verts(arms, pose, keep) if p is not None]
            gv = posed_verts(gun, pose)
            tris = np.array([[gv[i] for i in t] for _m, t in gun.tris])
            k = int(inside(hv, tris).sum()) if hv else 0
            tot += k
            worst = max(worst, (k, f))
        print('%-12s %-18s %s verts (%s) inside the gun: total %5d over %d frames, worst %d at frame %d'
              % (a.species, an, what, a.hand, tot, len(range(0, n, a.step)), worst[0], worst[1]))


def render(a):
    from PIL import Image, ImageDraw
    arms_p, gun_p, adir = paths(a.key, a.species)
    pose, n = read_jma(anim_file(adir, a.anim), a.frame)
    W, H = 960, 600
    f = (W / 2.0) / math.tan(math.radians(a.fov) / 2.0)
    light = (0.4, 0.5, 0.75)
    items = []
    for m, col in ((h2_jms.read(arms_p), (200, 170, 120)), (h2_jms.read(gun_p), (110, 200, 230))):
        vs = posed_verts(m, pose)
        for _m, (i, j, k) in m.tris:
            tri = (vs[i], vs[j], vs[k])
            if any(p[0] <= 0.5 for p in tri):
                continue
            pts = [(W / 2.0 - f * p[1] / p[0], H / 2.0 - f * p[2] / p[0]) for p in tri]
            nrm = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            s = 0.35 + 0.65 * abs(float(np.dot(nrm, light)) / (np.linalg.norm(nrm) or 1.0))
            items.append((sum(p[0] for p in tri) / 3.0, pts, tuple(int(c * s) for c in col)))
    img = Image.new('RGB', (W, H), (40, 44, 52))
    dr = ImageDraw.Draw(img)
    for _d, pts, col in sorted(items, key=lambda t: -t[0]):
        dr.polygon(pts, fill=col)
    img.save(a.out)
    print(a.out, 'frame', min(a.frame, n - 1), 'of', n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='verb', required=True)
    c = sub.add_parser('clip')
    c.add_argument('key')
    c.add_argument('species')
    c.add_argument('anims', nargs='+')
    c.add_argument('--hand', choices=('l', 'r', 'both'), default='both')
    c.add_argument('--fingers', action='store_true', help='only the finger vertices')
    c.add_argument('--step', type=int, default=4)
    r = sub.add_parser('render')
    r.add_argument('key')
    r.add_argument('species')
    r.add_argument('anim')
    r.add_argument('frame', type=int)
    r.add_argument('out')
    r.add_argument('--fov', type=float, default=70.0)
    a = ap.parse_args()
    clip(a) if a.verb == 'clip' else render(a)


if __name__ == '__main__':
    main()
