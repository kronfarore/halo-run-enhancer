r"""Where a port's LIT texels sit in 3D (JMS units of the FP model): one line per glow spot
(the clusters h1_h3_weapon_model.glow_spots finds) with its centre, its face NORMAL and the
3D extent of its lit texels -- what `glow_spots` / `glow_cards` filters need (`skip_normals`
+ `skip_dot`, `highest`, `strip`).

Written for the Mauler (2026-10-09): the drum windows face back / forward TILTED (dot with x
0.84..0.99), the barrel ends exactly +-x (1.0) -> skip_dot 0.995; the body slit is a LINE
along the gun (x 3.55..4.33, 0.2 tall) on a sideways face.

    python glow_spot_list.py brute_mauler excavator_metal [--world] [--threshold 64]
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h1_h3_weapon_model as M  # noqa: E402
import h3_rm_to_jms  # noqa: E402
import ports_h1  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('port')
    ap.add_argument('material')
    ap.add_argument('--world', action='store_true', help='the world model instead of the FP one')
    ap.add_argument('--threshold', type=int, default=16)
    ap.add_argument('--merge', type=float, default=1.0)
    a = ap.parse_args()
    w = ports_h1.load(a.port)['model']
    illum = next(il for _b, il in w['shaders'].values() if il)
    jm, _ = h3_rm_to_jms.convert(w['world' if a.world else 'fp'], markers=w.get('markers'))
    S = {'material': a.material, 'illum': illum, 'threshold': a.threshold, 'merge': a.merge}
    for C, N, _T, _node, pts in M.glow_spots(jm, S):
        q = np.concatenate(pts)
        r = lambda v: tuple(round(float(x), 2) for x in v)  # noqa: E731
        print('centre %-22s normal %-22s extent %s .. %s  (%d lit texels)'
              % (r(C), r(N), r(q.min(0)), r(q.max(0)), len(q)))


if __name__ == '__main__':
    main()
