r"""A JMS seen along one axis (default: from the side, x right / z up, looking along y), every
triangle flat grey shaded by its facing, one MATERIAL highlighted blue, painter's order. Quick
geometry checks without a boot: where a glow card set sits (the Brute Shot's folded drum ring,
2026-10-09: a half ring hidden behind the body plate on one side), whether a re-rooted world
model lies flat, which side a card set covers. `--side -1` looks from the other side.

    python jms_side_view.py "<HCEEK data>\weapons\brute shot\models\brute shot.jms" out\side.png bs_ring
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'pylibs'))
import env  # noqa: E402,F401
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from reclaimer.model.jms.file import read_jms  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('jms')
    ap.add_argument('out')
    ap.add_argument('material', nargs='?', default='', help='the material drawn blue')
    ap.add_argument('--side', type=float, default=1.0, help='+1: the viewer on +y, -1: on -y')
    ap.add_argument('--width', type=int, default=1800)
    a = ap.parse_args()
    jm = read_jms(open(a.jms, encoding='utf-8', errors='replace').read())
    mats = [m.name for m in jm.materials]
    P = np.array([(v.pos_x, v.pos_y, v.pos_z) for v in jm.verts])
    lo, hi = P.min(0), P.max(0)
    S = a.width / max(hi[0] - lo[0], hi[2] - lo[2])
    W, H = int((hi[0] - lo[0]) * S) + 40, int((hi[2] - lo[2]) * S) + 40
    img = Image.new('RGB', (W, H), (30, 30, 36))
    d = ImageDraw.Draw(img)
    tris = []
    for t in jm.tris:
        q = P[[t.v0, t.v1, t.v2]]
        tris.append((q[:, 1].mean() * a.side, t, q, np.cross(q[1] - q[0], q[2] - q[0])))
    tris.sort(key=lambda x: x[0])
    for _y, t, q, n in tris:
        x = q[:, 0] if a.side > 0 else -q[:, 0]
        x0 = lo[0] if a.side > 0 else -hi[0]
        pts = [((xx - x0) * S + 20, H - ((z - lo[2]) * S + 20)) for xx, z in zip(x, q[:, 2])]
        if mats[t.shader] == a.material:
            d.polygon(pts, fill=(80, 170, 255))
        else:
            shade = int(90 + 80 * abs(n[1]) / (np.linalg.norm(n) or 1))
            d.polygon(pts, fill=(shade, shade, shade))
    img.save(a.out)
    print(a.out, img.size)


if __name__ == '__main__':
    main()
