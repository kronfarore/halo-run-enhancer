r"""MEASURE a coloured scope frame (the Incineration Cannon, C9 2026-10-17: four boots were lost to eyeballed
fits -- user: 'repeating the same mistakes'). Read-only.

Prints the frame's ORANGE BANDS (density profiles) in source screenshots and in a port's four zoom-glyph
quadrants composited the way MCC draws them (1:1 at 1080p: each 480 x 270 quadrant x2 into its screen quarter),
so the two can be compared number by number:
  vertical bands     through x 880-1040 (the frame's top / bottom bands)
  horizontal bands   through y 600-700 (its left / right bands)
Match the port's bands to the screenshot's (scale, then shift), then re-render with h4_polyart_scope.py
`--xform sx,sy,dx,dy --pad 200`.

    python h4_scope_bands.py <screenshot.png> [...] [--quads <folder with tl/tr/bl/br.png>]
"""
import argparse

import numpy as np
from PIL import Image


def runs(p, thr):
    """(start, end) of the runs of p above thr longer than 6 px."""
    on = p > thr
    out, s = [], None
    for i, v in enumerate(on):
        if v and s is None:
            s = i
        if not v and s is not None:
            if i - s > 6:
                out.append((s, i))
            s = None
    if s is not None:
        out.append((s, len(on)))
    return out


def mask_shot(f):
    """The orange of a screenshot, at 1920 x 1080."""
    im = np.asarray(Image.open(f).convert('RGB').resize((1920, 1080))).astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    return (r > 110) & (r > g + 35) & (g > b - 10)


def mask_quads(folder):
    """The port's four glyph quadrants as MCC draws them (h4_polyart_scope's tl / tr / bl / br.png)."""
    full = Image.new('RGBA', (960, 540))
    for q, (x, y) in {'tl': (0, 0), 'tr': (480, 0), 'bl': (0, 270), 'br': (480, 270)}.items():
        full.paste(Image.open(folder.rstrip('/\\') + '/' + q + '.png'), (x, y))
    return np.asarray(full.resize((1920, 1080)).split()[3]) > 40


def bands(o):
    return runs(o[:, 880:1040].mean(axis=1), 0.2), runs(o[600:700, :].mean(axis=0), 0.2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('shots', nargs='*')
    ap.add_argument('--quads', help='folder holding the port quadrants tl / tr / bl / br.png')
    a = ap.parse_args()
    items = [(s.replace('\\', '/').rsplit('/', 1)[-1], mask_shot(s)) for s in a.shots]
    if a.quads:
        items.append(('port quadrants', mask_quads(a.quads)))
    for name, o in items:
        v, h = bands(o)
        print('%-24s vertical bands %s | horizontal bands %s' % (name, v, h))


if __name__ == '__main__':
    main()
