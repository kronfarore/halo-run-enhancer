r"""A Halo 4 polyart SCOPE (a .cui_screen's zoom-only 3D vector frame) as Halo 1 zoom-glyph quadrant
PNGs (the LightRifle, C4 2026-10-15; user: 'orange overlays'). Halo 1's zoom mask can only darken, so
the coloured frame is drawn as zoom-type crosshair overlays (h1_pickable_weapons `zoom_glyphs`
`image`), one per screen quadrant.

  1. every polyart piece rasterized through its own camera at 1920 x 1080 (h4_polyart): WIRES at
     `wire_alpha`, HOLO fills (translucent panels) at `fill_alpha`
  2. the fit to the source screenshot (the CUI's parallax / zoom-in animation moves the frame): scale
     x / y about the screen centre, then (dx, dy) px -- found by maximising the overlap with the
     screenshot's saturated orange (`--fit <screenshot>`), or given
  3. four quadrants, each downsampled by `down` (a sheet px = `down` screen px), registered at the
     screen centre (their inner corner)

    python h4_polyart_scope.py <out dir> <polyart folder> --wires a,b,.. --fills c,d,.. [--fit shot.png]
        [--xform sx,sy,dx,dy] [--down 2]
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_polyart  # noqa: E402

W, H = 1920, 1080


def render(folder, names):
    acc = np.zeros((H, W), np.float32)
    for n in names:
        acc = np.maximum(acc, h4_polyart.raster(h4_polyart.load(folder + '\\' + n), W, H))
    return acc


def place(img, sx, sy, dx, dy):
    """img scaled about the screen centre, then shifted (dx, dy) px."""
    W2, H2 = int(W * sx), int(H * sy)
    r = np.array(Image.fromarray(img.astype(np.float32)).resize((W2, H2), Image.BILINEAR))
    canvas = np.zeros((H + 2 * 400, W + 2 * 400), np.float32)
    ox, oy = 400 + (W - W2) // 2, 400 + (H - H2) // 2
    canvas[oy:oy + H2, ox:ox + W2] = r
    return canvas[400 - dy:400 - dy + H, 400 - dx:400 - dx + W]


def fit(img, shot):
    s = np.array(Image.open(shot).convert('RGB').resize((W, H))).astype(float)
    R, G, B = s[..., 0], s[..., 1], s[..., 2]
    mask = ((R > 220) & (G > 70) & (G < 190) & (B < 110) & (R - G > 60)).astype(float)
    best = None
    for sx in np.arange(0.85, 1.2, 0.025):
        for sy in np.arange(0.85, 1.25, 0.025):
            for dy in range(-200, 41, 8):
                for dx in (-16, -8, 0, 8, 16):
                    c = place(img, sx, sy, dx, dy)[::4, ::4]
                    v = (c * mask[::4, ::4]).sum() / (c.sum() + 1e-6)
                    if best is None or v > best[0]:
                        best = (v, round(sx, 3), round(sy, 3), dx, dy)
    print('fit: overlap %.3f -> scale x %s y %s, shift %d %d px' % best)
    return best[1:]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out')
    ap.add_argument('folder')
    ap.add_argument('--wires', required=True)
    ap.add_argument('--fills', default='')
    ap.add_argument('--wire-alpha', type=float, default=1.0)
    ap.add_argument('--fill-alpha', type=float, default=0.35)
    ap.add_argument('--fit')
    ap.add_argument('--xform')
    ap.add_argument('--down', type=int, default=2)
    a = ap.parse_args()
    wires = render(a.folder, a.wires.split(','))
    fills = render(a.folder, [x for x in a.fills.split(',') if x])
    img = np.maximum(wires * a.wire_alpha, fills * a.fill_alpha)
    sx, sy, dx, dy = (fit(np.maximum(wires, fills), a.fit) if a.fit else
                      [float(x) for x in a.xform.split(',')])
    img = place(img, sx, sy, int(dx), int(dy))
    os.makedirs(a.out, exist_ok=True)
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(os.path.join(a.out, 'full.png'))
    cx, cy = W // 2, H // 2
    for name, (x0, y0) in (('tl', (0, 0)), ('tr', (cx, 0)), ('bl', (0, cy)), ('br', (cx, cy))):
        q = img[y0:y0 + cy, x0:x0 + cx]
        q = np.array(Image.fromarray(q.astype(np.float32)).resize((cx // a.down, cy // a.down), Image.BOX))
        A = (np.clip(q, 0, 1) * 255).astype(np.uint8)
        # a 1/255 alpha pixel in each corner: the glyph's crop (h1_pickable_weapons: the content's
        # bounding box) is then the WHOLE quadrant -- MCC draws a zoom overlay centred on its sprite
        # (the registration point is ignored: the LightRifle's boot 3), so the offsets need a known crop
        for yy, xx in ((0, 0), (0, -1), (-1, 0), (-1, -1)):
            A[yy, xx] = max(A[yy, xx], 1)
        white = np.full_like(A, 255)
        Image.fromarray(np.dstack([white, white, white, A]), 'RGBA').save(os.path.join(a.out, name + '.png'))
        print('%s: %d x %d, registration at the screen centre (%s)' % (
            name, cx // a.down, cy // a.down, 'inner corner'))


if __name__ == '__main__':
    main()
