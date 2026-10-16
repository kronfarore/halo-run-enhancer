r"""A polyart scope's quadrant PNGs (h4_polyart_scope.py) made SYMMETRIC and EDGE-FADED -- the Incineration Cannon,
C9 (2026-10-16). Writes only the given scope folder (the port's own data).

  * mirror: the right quadrants = the left ones flipped (tr = tl, br = bl; boot 2 'not symmetrical': Halo 4's two
    polyart ring sets are not mirror images in the rasterized frame). The un-mirrored run is kept as <q>_fit.png.
  * fade: the art's alpha ramps to 0 over the OUTER `fade` px of the full screen (each quadrant's outer two edges;
    1 screen px = 2 quadrant px at --down 2) -- a frame drawn smaller than the screen (boot 7: 'make it fit the
    screen') then fades out instead of ending in hard cuts (boot 4: 'cut off'). The crop-pinning corner pixels
    (h4_polyart_scope: alpha 10/255 at each quadrant's corners) are kept.

    python h1_scope_quadrants.py "<scope folder>" --mirror left --fade 120
"""
import argparse
import os
import shutil

import numpy as np
from PIL import Image

QUADS = ('tl', 'tr', 'bl', 'br')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('folder')
    ap.add_argument('--mirror', choices=('left', 'none'), default='left')
    ap.add_argument('--fade', type=int, default=0, help='screen px faded at the outer edges')
    ap.add_argument('--down', type=int, default=2, help='screen px a quadrant px (h4_polyart_scope --down)')
    a = ap.parse_args()
    p = lambda q, s='': os.path.join(a.folder, q + s + '.png')
    for q in QUADS:                                      # the fitted run, kept
        if not os.path.exists(p(q, '_fit')) or os.path.getmtime(p(q)) > os.path.getmtime(p(q, '_fit')):
            shutil.copy2(p(q), p(q, '_fit'))
    imgs = {q: Image.open(p(q, '_fit')).convert('RGBA') for q in QUADS}
    if a.mirror == 'left':
        imgs['tr'] = imgs['tl'].transpose(Image.FLIP_LEFT_RIGHT)
        imgs['br'] = imgs['bl'].transpose(Image.FLIP_LEFT_RIGHT)
    for q, im in imgs.items():
        arr = np.array(im).astype(float)
        h, w = arr.shape[:2]
        corners = [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]
        pins = {c: arr[c][3] for c in corners}
        if a.fade:
            f = a.fade / float(a.down)
            xs, ys = np.arange(w, dtype=float), np.arange(h, dtype=float)
            # the OUTER edges: left for tl / bl, right for tr / br; top for tl / tr, bottom for bl / br
            dx = xs if q[1] == 'l' else (w - 1 - xs)
            dy = ys if q[0] == 't' else (h - 1 - ys)
            rx, ry = np.clip(dx / f, 0, 1), np.clip(dy / f, 0, 1)
            arr[..., 3] *= ry[:, None] * rx[None, :]
        for c, v in pins.items():                         # the crop pins survive the fade
            arr[c][3] = max(arr[c][3], v)
        Image.fromarray(np.clip(np.round(arr), 0, 255).astype(np.uint8), 'RGBA').save(p(q))
        print(q, im.size, 'mirror' if (a.mirror == 'left' and q[1] == 'r') else '', 'fade %d px' % a.fade if a.fade else '')


if __name__ == '__main__':
    main()
