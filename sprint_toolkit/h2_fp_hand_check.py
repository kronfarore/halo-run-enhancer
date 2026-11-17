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
    python h2_fp_hand_check.py palm   <key> <species> <anim> [<anim> ...] [--step 25]
        the left PALM top against the gun's underside, in the gun's frame (the DMR's grip measure).
    python h2_fp_hand_check.py ortho  <key> <species> <anim> <frame> <out.png>
        side / barrel / below views of the left arm + gun in the gun's frame: Halo 2's arms over the
        SOURCE game's own (the config's arms_rm). Write it OUTSIDE the repo.

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


def to_gun(pose, V):
    """Model-space points into the posed GUN's frame (x forward, z up as the gun sits)."""
    gq, gt = pose['gun']
    gi = (gq[0], -gq[1], -gq[2], -gq[3])
    return np.array([qrot(gi, [v[k] - gt[k] for k in range(3)]) for v in V])


def palm(a):
    """The left PALM against the gun, in the gun's frame (the DMR, B1, 2026-11-16: the measure the
    user's grip calls matched where edge counts did not): the palm top (95th percentile of the
    l_hand-weighted vertices' z) against the gun's underside straight above the palm's footprint.
    gap > 0 = the palm hangs below the gun; < 0 = it reaches into the underside (accepted: the
    Chief -0.70, the Arbiter -0.30, JMS units)."""
    import h2_jms
    arms_p, gun_p, adir = paths(a.key, a.species)
    arms, gun = h2_jms.read(arms_p), h2_jms.read(gun_p)
    keys = [key(n.name) for n in arms.nodes]
    sel = [i for i, v in enumerate(arms.verts) if v.influences and keys[max(v.influences, key=lambda t: t[1])[0]] == 'l_hand']
    for an in a.anims:
        pose0, n = read_jma(anim_file(adir, an), 0)
        for f in range(0, n, a.step):
            pose, _n = read_jma(anim_file(adir, an), f)
            pv = to_gun(pose, np.array(posed_verts(arms, pose))[sel])
            gv = to_gun(pose, posed_verts(gun, pose))
            x0, x1 = np.percentile(pv[:, 0], 10), np.percentile(pv[:, 0], 90)
            y0, y1 = np.percentile(pv[:, 1], 10), np.percentile(pv[:, 1], 90)
            over = gv[(gv[:, 0] >= x0) & (gv[:, 0] <= x1) & (gv[:, 1] >= y0 - 0.5) & (gv[:, 1] <= y1 + 0.5)]
            top = np.percentile(pv[:, 2], 95)
            under = over[:, 2].min() if len(over) else float('nan')
            print('%-12s %-14s frame %3d  palm x %5.1f..%5.1f  y %5.1f..%5.1f  top %6.2f  underside %6.2f  gap %6.2f'
                  % (a.species, an, f, x0, x1, y0, y1, top, under, under - top))


def source_arms(k, species):
    """The SOURCE game's own FP arms as a Halo 2 JMS (h2_port_geometry.h3_convert of the config's
    `arms_rm`), cached in %TEMP%."""
    import h2_jms
    import h2_port_geometry
    rm = ports_h2.load(k)['fp_anims']['species'][species]['arms_rm']
    out = os.path.join(os.environ.get('TEMP', '.'), 'h2_hand_src_%s_%s.jms' % (k, species))
    if not os.path.exists(out):
        class Keep(dict):
            def get(self, name, default=None):
                return name
        m = h2_port_geometry.h3_convert({'materials': Keep()}, rm, False)
        h2_jms.write(out, m[0] if isinstance(m, tuple) else m)
    return out


def ortho(a):
    """Orthographic views of the LEFT ARM + gun in the gun's frame -- side (along +y), barrel (from
    the muzzle back) and below -- Halo 2's arms over the SOURCE game's own arms, same frame (the DMR,
    B1: the barrel view showed the Arbiter's palm beside the gun, Reach's under it; the long fidget's
    wrist). Orange = arm, blue = gun."""
    import h2_jms
    from PIL import Image, ImageDraw
    arms_p, gun_p, adir = paths(a.key, a.species)
    pose, n = read_jma(anim_file(adir, a.anim), a.frame)
    gun = h2_jms.read(gun_p)
    views = (('side', 0, 2, 1, (-6.0, -6.0), (20.0, 20.0)), ('barrel', 1, 2, 0, (-10.0, -9.0), (10.0, 11.0)),
             ('below', 0, 1, 2, (-6.0, -6.0), (20.0, 20.0)))
    rows = []
    for title, path in (('Halo 2', arms_p), ('source', source_arms(a.key, a.species))):
        arms = h2_jms.read(path)
        keys = [key(nd.name) for nd in arms.nodes]
        meshes = [(to_gun(pose, posed_verts(gun, pose)), [t for _m, t in gun.tris], (90, 180, 230))]
        av = to_gun(pose, posed_verts(arms, pose))
        lt = [t for _m, t in arms.tris if arms.verts[t[0]].influences and
              keys[max(arms.verts[t[0]].influences, key=lambda w: w[1])[0]].startswith('l_') and
              'upperarm' not in keys[max(arms.verts[t[0]].influences, key=lambda w: w[1])[0]]]
        meshes.append((av, lt, (230, 160, 90)))
        panels = []
        for vname, ax, ay, az, lo, hi in views:
            W = H = 420
            sc = (W / (hi[0] - lo[0]), H / (hi[1] - lo[1]))
            depth = np.full((H, W), np.inf)
            img = np.full((H, W, 3), 40.0)
            for V, tris, col in meshes:
                X = (V[:, ax] - lo[0]) * sc[0]
                Y = H - (V[:, ay] - lo[1]) * sc[1]
                Z = -V[:, az] if vname == 'barrel' else V[:, az]
                for i, j, k2 in tris:
                    xs, ys, zs = X[[i, j, k2]], Y[[i, j, k2]], Z[[i, j, k2]]
                    bx0, bx1 = max(0, int(xs.min())), min(W - 1, int(xs.max()) + 1)
                    by0, by1 = max(0, int(ys.min())), min(H - 1, int(ys.max()) + 1)
                    if bx1 < bx0 or by1 < by0:
                        continue
                    d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
                    if abs(d) < 1e-9:
                        continue
                    gx, gy = np.meshgrid(np.arange(bx0, bx1 + 1) + 0.5, np.arange(by0, by1 + 1) + 0.5)
                    w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
                    w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
                    w2 = 1 - w0 - w1
                    z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
                    sub = depth[by0:by1 + 1, bx0:bx1 + 1]
                    win = (w0 >= 0) & (w1 >= 0) & (w2 >= 0) & (z < sub)
                    if not win.any():
                        continue
                    nv = np.cross(V[j] - V[i], V[k2] - V[i])
                    nv = nv / (np.linalg.norm(nv) or 1.0)
                    sub[win] = z[win]
                    img[by0:by1 + 1, bx0:bx1 + 1][win] = np.array(col) * (0.35 + 0.65 * abs(nv[az]))
            pim = Image.fromarray(img.astype(np.uint8))
            ImageDraw.Draw(pim).text((6, 4), '%s %s' % (title, vname), fill=(255, 255, 255))
            panels.append(pim)
        row = Image.new('RGB', (3 * 428, 420), (255, 255, 255))
        for k2, p in enumerate(panels):
            row.paste(p, (k2 * 428, 0))
        rows.append(row)
    out = Image.new('RGB', (rows[0].width, 2 * 428), (255, 255, 255))
    out.paste(rows[0], (0, 0))
    out.paste(rows[1], (0, 428))
    out.save(a.out)
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
    p = sub.add_parser('palm')
    p.add_argument('key')
    p.add_argument('species')
    p.add_argument('anims', nargs='+')
    p.add_argument('--step', type=int, default=25)
    o = sub.add_parser('ortho')
    o.add_argument('key')
    o.add_argument('species')
    o.add_argument('anim')
    o.add_argument('frame', type=int)
    o.add_argument('out')
    a = ap.parse_args()
    {'clip': clip, 'render': render, 'palm': palm, 'ortho': ortho}[a.verb](a)


if __name__ == '__main__':
    main()
