r"""A Halo 1 port's FIRST-PERSON retarget (Halo 1 arms + the port's FP gun) drawn through a pinhole
camera matching h4_fp_reference.py (the FP origin, looking +x, +y left, +z up; horizontal FOV 70,
960 x 600) -- so it lines up with Halo 4's own render of the same animation frame. Read-only.

The C2 Suppressor's left hand (2026-10-15): the hand-in-gun COUNT (h1_fp_hand_clip.py) pointed one way,
the LOOK the other; this render beside Halo 4's own decided it. `--try x,y,z` draws a trial
hand_offset (gun space, metres) for one side without touching the config.

    python h1_fp_camera_render.py suppressor first_person:idle 0 out\cam_idle.png
    python h1_fp_camera_render.py suppressor first_person:idle 0 out\cam_try.png --side l --try 0,0.01,0.01
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_render as R            # noqa: E402
import h1_fp_retarget as T       # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('port')
    ap.add_argument('anim', help='source animation name (the config retarget map key)')
    ap.add_argument('frame', type=int)
    ap.add_argument('out')
    ap.add_argument('--side', choices='lr', default='l')
    ap.add_argument('--try', dest='trial', metavar='X,Y,Z')
    ap.add_argument('--fov', type=float, default=70.0)
    a = ap.parse_args()
    nodes, anims, defaults, _ = T.load(a.port)
    names, parents = T.h1_skeleton(a.port, nodes)
    cfg = T.WEAPONS[a.port]
    if a.trial:
        cfg['hand_offset'] = {a.side: tuple(float(x) for x in a.trial.split(','))}
        cfg['hand_offset_anims'] = {}
    _typ, fr = T.retarget(a.port, a.anim, nodes, anims, defaults)
    W = R.compose(names, parents, fr[a.frame])
    Wd, Ht = 960, 600
    f = (Wd / 2) / np.tan(np.radians(a.fov) / 2)
    polys = []
    for model, col in ((R.load_model(T.ensure_model(a.port)), (110, 170, 200)),
                       (R.load_model(R.HANDS), (200, 160, 110))):
        for tri, _c in R.posed_tris(model, W, (0, 0, 0)):
            P = np.array(tri, float)
            if (P[:, 0] <= 0.01).any():
                continue
            x = Wd / 2 - f * P[:, 1] / P[:, 0]
            y = Ht / 2 - f * P[:, 2] / P[:, 0]
            n = np.cross(P[1] - P[0], P[2] - P[0])
            n = n / (np.linalg.norm(n) or 1)
            shade = 0.45 + 0.55 * abs(n[0])
            polys.append((P[:, 0].mean(), list(zip(x, y)), tuple(int(c * shade) for c in col)))
    img = Image.new('RGB', (Wd, Ht), (50, 50, 55))
    d = ImageDraw.Draw(img)
    for _z, pts, c in sorted(polys, key=lambda p: -p[0]):
        d.polygon(pts, fill=c)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    img.save(a.out)
    print(a.out)


if __name__ == '__main__':
    main()
