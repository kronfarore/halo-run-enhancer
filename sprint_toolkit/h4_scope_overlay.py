r"""Check a POLYART SCOPE FIT (read-only): h4_polyart_scope.py's `full.png` (the fitted frame, L = alpha)
drawn in cyan over the source screenshot it was fitted to, half size -- the Binary Rifle's zoom 1 / 2
fits (C6, 2026-10-16) were judged this way before a boot.

    python h4_scope_overlay.py <screenshot.png> <full.png> <out.png>
"""
import sys

import numpy as np
from PIL import Image


def main(shot, full, out):
    s = np.asarray(Image.open(shot).convert('RGB').resize((1920, 1080))).astype(float)
    a = np.asarray(Image.open(full).convert('L').resize((1920, 1080))).astype(float)[..., None] / 255.0
    o = s * 0.6 * (1 - a) + np.array([0, 255, 255]) * a
    Image.fromarray(o.clip(0, 255).astype(np.uint8)).resize((960, 540)).save(out)
    print('wrote', out)


if __name__ == '__main__':
    main(*sys.argv[1:4])
