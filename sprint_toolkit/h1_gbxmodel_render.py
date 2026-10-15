r"""Orthographic render of a BUILT Halo 1 gbxmodel (HCEEK tags, bind pose, model space) from the side
or the top, its parts coloured by shader name -- to check added glow geometry (glow_cards /
glow_spots) before a boot: highlighted shaders are drawn ON TOP, so a card standing off the gun or
running through it shows. Read-only. The C2 Suppressor's halo cards (boots 6-7): a card floating off the
top plate and ring cards tilted out of their rings were seen here first.

    python h1_gbxmodel_render.py "weapons\suppressor\suppressor" out\gbx_left.png --view left ^
        --highlight su_halo=255,220,40 --highlight su_glow=255,120,0
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.mod2 import mod2_def  # noqa: E402

TAGS = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('model', help='gbxmodel path under HCEEK\\tags, no extension')
    ap.add_argument('out')
    ap.add_argument('--view', choices=('left', 'top'), default='left')
    ap.add_argument('--highlight', action='append', default=[], metavar='SHADER=R,G,B')
    a = ap.parse_args()
    col = {}
    for h in a.highlight:
        k, v = h.split('=')
        col[k] = tuple(int(x) for x in v.split(','))
    d = mod2_def.build(filepath=os.path.join(TAGS, a.model + '.gbxmodel')).data.tagdata
    shaders = [s.shader.filepath.rsplit('\\', 1)[-1] for s in d.shaders.STEPTREE]
    tris = []
    for g in d.geometries.STEPTREE:
        for p in g.parts.STEPTREE:
            P = np.array([(v.position_x, v.position_y, v.position_z) for v in p.uncompressed_vertices.STEPTREE])
            strip = [i for t in p.triangles.STEPTREE for i in t if i != -1]
            c = col.get(shaders[p.shader_index], (150, 150, 160))
            for k in range(len(strip) - 2):
                ids = strip[k:k + 3]
                if len(set(ids)) == 3:
                    tris.append((P[ids], c, shaders[p.shader_index] in col))
    if a.view == 'left':                       # from +y: x right, z up, depth y
        proj = lambda Q: (Q[:, 0], Q[:, 2], Q[:, 1])      # noqa: E731
    else:                                      # from +z: x right, -y up, depth z
        proj = lambda Q: (Q[:, 0], -Q[:, 1], Q[:, 2])     # noqa: E731
    U, V, _ = proj(np.concatenate([t[0] for t in tris]))
    W, H = 1400, 600
    s = min((W - 40) / (U.max() - U.min()), (H - 40) / (V.max() - V.min()))
    img = Image.new('RGB', (W, H), (40, 40, 45))
    dr = ImageDraw.Draw(img)
    items = []
    for Q, c, hi in tris:
        x, y, z = proj(Q)
        pts = [(20 + (p - U.min()) * s, H - 20 - (q - V.min()) * s) for p, q in zip(x, y)]
        items.append((hi, z.mean(), pts, c))
    for _hi, _z, pts, c in sorted(items, key=lambda i: (i[0], i[1])):
        dr.polygon(pts, fill=c)
    img.save(a.out)
    print(a.out)


if __name__ == '__main__':
    main()
