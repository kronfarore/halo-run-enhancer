r"""A Halo 1 DIFFUSE for a Halo 4 Forerunner material that has NO colour map (the Suppressor, C2,
2026-10-14). Halo 4's `srf_char_forerunner_andrew` takes its diffuse from a CONTROL MAP channel
(`control_map_spdfgl`: R specular, G diffuse, B gloss) x the material's `albedo_tint`; the colour map
an H4EK .material may still name (storm_forerunner_smg_default_diff) is not shipped and not used. The
SHIPPED Suppressor default material = H4EK's storm_forerunner_smg_shatter_metal (specular 100, mix
0.9, reflection gamma 0.42, fresnel power 0.5936: read from m020.map) on the SHATTER control map --
H4EK's _default_metal.material is not what the game draws.

Output (RGBA): RGB = albedo_tint x the diffuse channel x `gain` (grey), A = the specular channel (Halo
1's shader_model reads the base map's alpha as its reflection mask: h1_h3_weapon_model.bitmaps).
`--mode lightness` keeps the first stand-in (a lightness from the channels' mean, scaled to `mean`).

    python h4_standin_diffuse.py <h4 control .bitmap> <out .png> [--tint 0.494] [--gain 1.0]
    python h4_standin_diffuse.py <h4 control .bitmap> <out .png> --mode lightness [--tint 0.431] [--mean 150]
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4_tags  # noqa: E402

CH = {'R': 0, 'G': 1, 'B': 2, 'A': 3}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('control')
    ap.add_argument('out')
    ap.add_argument('--mode', choices=('channel', 'lightness'), default='channel')
    ap.add_argument('--tint', type=float, default=0.494)     # the material's albedo_tint (grey)
    ap.add_argument('--diffuse', default='G')                # control_map_spdfgl: df = G
    ap.add_argument('--specular', default='R')               # sp = R -> alpha (reflection mask)
    ap.add_argument('--gain', type=float, default=1.0)
    ap.add_argument('--mean', type=float, default=150.0)     # lightness mode only
    a = ap.parse_args()
    c = np.asarray(h4_tags.bitmap_images(a.control)[0].convert('RGBA')).astype(np.float64) / 255.0
    if a.mode == 'lightness':
        g = (0.35 + 0.65 * c[..., :3].mean(axis=2)) * a.tint
        g = np.clip(g * (a.mean / 255.0) / g.mean(), 0.0, 1.0)
        alpha = np.ones(g.shape)
    else:
        g = np.clip(c[..., CH[a.diffuse]] * a.tint * a.gain, 0.0, 1.0)
        alpha = c[..., CH[a.specular]]
    out = np.zeros(g.shape + (4,), np.uint8)
    out[..., :3] = np.round(g * 255.0)[..., None]
    out[..., 3] = np.round(alpha * 255.0)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    Image.fromarray(out).save(a.out)
    print('wrote %s %s rgb mean %.1f, alpha mean %.1f' % (a.out, out.shape[1::-1], out[..., 0].mean(),
                                                          out[..., 3].mean()))


if __name__ == '__main__':
    main()
