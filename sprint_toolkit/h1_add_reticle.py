r"""Bring a Halo 3 reticle into Halo 1's `ui\hud\bitmaps\combined\hud_reticles` (HCEEK tag).

Halo 1 keeps every reticle as its own 256x256 a8y8 bitmap (luminance 255 = white, alpha =
the shape) behind one sequence, registered at (128, 125). A new reticle is APPENDED as a
bitmap + sequence copied from the PC fuel rod's (#15), so no stock index moves; a name
already present is replaced in place.

SCALE. The same weapon's reticle in both games fixes it: the PC fuel rod's Halo 1 reticle
(#15) reaches 123 px from its centre, Halo 3's fuel rod reticle (hud_reticles #19) 97 px,
so Halo 3 art is drawn x123/97 = x1.27 in Halo 1's sheet (measured 2026-10-06). A weapon
HUD's crosshair element then points its overlay at the new sequence.

    python h1_add_reticle.py hud_reticles 13 "energy sword"
"""
import copy
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import port_env  # noqa: E402,F401
from reclaimer.hek.defs.bitm import bitm_def  # noqa: E402
import h3_hud_art  # noqa: E402

TAG = os.path.join('F:' + os.sep, 'SteamLibrary', 'steamapps', 'common', 'HCEEK', 'tags',
                   'ui', 'hud', 'bitmaps', 'combined', 'hud_reticles.bitmap')
TEMPLATE_SEQ = 15            # the PC fuel rod's reticle
SIZE, CENTRE = 256, (128, 125)
SCALE = 123.0 / 97.0


def add(h3_sheet, h3_index, name):
    if not os.path.exists(TAG + '.before_pickable'):
        shutil.copy2(TAG, TAG + '.before_pickable')
    art, (rx, ry) = h3_hud_art.sprite(h3_sheet, h3_index)
    w, h = round(art.width * SCALE), round(art.height * SCALE)
    alpha = art.split()[3].resize((w, h), Image.LANCZOS)
    canvas = Image.new('L', (SIZE, SIZE), 0)
    canvas.paste(alpha, (round(CENTRE[0] - rx * SCALE), round(CENTRE[1] - ry * SCALE)))
    a = np.array(canvas)
    la = np.stack([np.full_like(a, 255), a], axis=-1).astype(np.uint8)
    raw = la.tobytes()

    t = bitm_def.build(filepath=TAG)
    d = t.data.tagdata
    bms, seqs = d.bitmaps.STEPTREE, d.sequences.STEPTREE
    pix = bytearray(d.processed_pixel_data.data)
    have = [i for i, q in enumerate(seqs) if q.sequence_name == name[:31]]
    if have:
        si = have[0]
        nb = bms[seqs[si].sprites.STEPTREE[0].bitmap_index]
        pix[nb.pixels_offset:nb.pixels_offset + len(raw)] = raw
    else:
        tmpl_seq = seqs[TEMPLATE_SEQ]
        tb = bms[tmpl_seq.sprites.STEPTREE[0].bitmap_index]
        bms.append(copy.deepcopy(tb))
        nb = bms[len(bms) - 1]
        nb.width = nb.height = SIZE
        nb.mipmaps = 0
        nb.pixels_offset = len(pix)
        pix += raw
        seqs.append(copy.deepcopy(tmpl_seq))
        si = len(seqs) - 1
        seqs[si].sequence_name = name[:31]
        seqs[si].first_bitmap_index = len(bms) - 1
        for sp in seqs[si].sprites.STEPTREE:
            sp.bitmap_index = len(bms) - 1
    d.processed_pixel_data.data = bytes(pix)
    t.filepath = TAG
    t.serialize(temp=False, backup=False)
    Image.fromarray(a).save(os.path.join(HERE, 'out', 'reticle_%s.png' % name.replace(' ', '_')))
    return si


if __name__ == '__main__':
    print('sequence', add(sys.argv[1], int(sys.argv[2]), sys.argv[3]))
