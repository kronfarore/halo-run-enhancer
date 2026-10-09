r"""A FOLDED glow (h1_h3_weapon_model `glow_cards` `fold`) as Halo 1 will texture it, BEFORE a boot:
the card material's triangles on one face plane rasterised looking along the fold axis, Halo 3's
illum mask sampled at their interpolated UVs (Halo 1's v convention, 1 - v, and the raw v in a
second image). The Brute Shot (2026-10-09) took four boots to get its drum chevrons right; this
render showed each fix (squashed half, cut chevrons) without one.

    python glow_fold_render.py "<HCEEK data>\weapons\brute shot\models\brute shot.jms"
        objects\weapons\support_low\brute_shot\bitmaps\brute_shot_illum.bitmap out\fold.png
        [--material bs_ring] [--axis y] [--side 1] [--scale 60]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa: E402,F401
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from reclaimer.model.jms.file import read_jms  # noqa: E402
import h3_hud_art  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('jms')
    ap.add_argument('mask', help='the Halo 3 illum bitmap (H3EK path)')
    ap.add_argument('out')
    ap.add_argument('--material', default='bs_ring')
    ap.add_argument('--axis', default='y', choices='xyz')
    ap.add_argument('--side', type=float, default=1.0, help='+1: the face on +axis, -1: the other')
    ap.add_argument('--scale', type=float, default=60.0, help='pixels per JMS unit')
    a = ap.parse_args()
    jm = read_jms(open(a.jms, encoding='utf-8', errors='replace').read())
    mats = [m.name for m in jm.materials]
    img, _ = h3_hud_art.decode(a.mask)
    M = np.array(img)[..., :3].max(2).astype(float) / 255.0
    H, W = M.shape
    ax = 'xyz'.index(a.axis)
    u_ax, v_ax = [k for k in range(3) if k != ax]
    P = np.array([(v.pos_x, v.pos_y, v.pos_z) for v in jm.verts])
    tris = [t for t in jm.tris if mats[t.shader] == a.material]
    if not tris:
        raise SystemExit('no %s triangles' % a.material)
    # the face plane = the axial level most card vertices share on that side (the fold puts a
    # whole ring there; the extreme level can be a side indicator spot)
    lev = np.round(P[[i for t in tris for i in (t.v0, t.v1, t.v2)], ax] * a.side, 2)
    vals, cnt = np.unique(lev[lev > 0], return_counts=True)
    lv = vals[np.argmax(cnt)]
    face = [t for t in tris if np.all(np.abs(P[[t.v0, t.v1, t.v2], ax] * a.side - lv) < 0.05)]
    pts = P[[i for t in face for i in (t.v0, t.v1, t.v2)]]
    x0, z0 = pts[:, u_ax].min() - 0.3, pts[:, v_ax].min() - 0.3
    S = a.scale
    N = int(max(pts[:, u_ax].max() - x0, pts[:, v_ax].max() - z0) * S) + 20
    for flip in (True, False):
        canvas = np.zeros((N, N))
        for t in face:
            ids = (t.v0, t.v1, t.v2)
            X = np.array([(P[i, u_ax] - x0) * S for i in ids])
            Z = np.array([(P[i, v_ax] - z0) * S for i in ids])
            U = np.array([jm.verts[i].tex_u for i in ids])
            V = np.array([jm.verts[i].tex_v for i in ids])
            if flip:
                V = 1 - V
            xa, xb = int(X.min()), int(X.max()) + 1
            za, zb = int(Z.min()), int(Z.max()) + 1
            gx, gz = np.meshgrid(np.arange(xa, xb) + 0.5, np.arange(za, zb) + 0.5)
            d = (Z[1] - Z[2]) * (X[0] - X[2]) + (X[2] - X[1]) * (Z[0] - Z[2])
            if abs(d) < 1e-9:
                continue
            l0 = ((Z[1] - Z[2]) * (gx - X[2]) + (X[2] - X[1]) * (gz - Z[2])) / d
            l1 = ((Z[2] - Z[0]) * (gx - X[2]) + (X[0] - X[2]) * (gz - Z[2])) / d
            l2 = 1 - l0 - l1
            inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
            u = (l0 * U[0] + l1 * U[1] + l2 * U[2]) % 1.0
            v = (l0 * V[0] + l1 * V[1] + l2 * V[2]) % 1.0
            val = M[(v * (H - 1)).astype(int), (u * (W - 1)).astype(int)]
            sub = canvas[za:zb, xa:xb]
            sub[inside] = np.maximum(sub[inside], val[inside])
        out = a.out if flip else a.out.replace('.png', '_rawv.png')
        Image.fromarray((np.clip(canvas[::-1] * 1.6, 0, 1) * 255).astype(np.uint8)).save(out)
        print(out, '(%s)' % ('Halo 1 v = 1 - v' if flip else 'raw v'))
    print('%d face triangle(s) of %s' % (len(face), a.material))


if __name__ == '__main__':
    main()
