r"""A STAND-IN diffuse for a Halo 4 weapon whose colour map H4EK does not ship (the Suppressor, C2,
2026-10-14: storm_forerunner_smg_default_diff is referenced by its metal material and missing from
the kit; the control / normal / cube maps are there). Grey = Halo 4's `albedo_tint` x a lightness
from the control map's channels (same UV layout: panel shapes, edges, recesses), scaled so the
mean sits at `mean`. Written into the port's own data folder; a config names it (an absolute
image path, h3_hud_art.decode).

    python h4_standin_diffuse.py <h4 control .bitmap> <out .png> [--tint 0.431] [--mean 150]
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_tags  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('control')
    ap.add_argument('out')
    ap.add_argument('--tint', type=float, default=0.431)     # the metal material's albedo_tint
    ap.add_argument('--mean', type=float, default=150.0)
    a = ap.parse_args()
    c = np.asarray(h4_tags.bitmap_images(a.control)[0].convert('RGB')).astype(np.float64) / 255.0
    light = 0.35 + 0.65 * c.mean(axis=2)                     # recesses / unlit channels darker
    g = light * a.tint
    g = np.clip(g * (a.mean / 255.0) / g.mean(), 0.0, 1.0)
    rgb = np.repeat(np.round(g * 255.0).astype(np.uint8)[..., None], 3, axis=2)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    Image.fromarray(rgb).save(a.out)
    print('wrote %s %s mean %.0f' % (a.out, rgb.shape[1::-1], rgb.mean()))


if __name__ == '__main__':
    main()
