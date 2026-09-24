r"""The weapon symbol on the Halo 2 HUD, which is painted into the BACKGROUND plate.

The first guess was the `backpack` widget, and it was wrong: that draws the small stowed
weapon icon at the left of the group. The big symbol beside the ammo is part of
`ui\hud\bitmaps\new_hud\backgrounds\<weapon>_bkd` -- each weapon has its own 206x38 plate
with its silhouette painted onto it, which is why a port wearing the donor's plate shows
the donor's weapon no matter what else is fixed.

**Reconstructing the empty plate.** There is no blank one to start from; every plate has a
weapon on it. But there are seventeen of them and they differ ONLY where the weapon is, so
the per-pixel MEDIAN across all of them is the plate with no weapon at all -- at any given
pixel most weapons leave it alone. Diffing two plates puts the silhouette in x 105..190,
y 5..33, and the median is only taken there, so nothing else can drift.

The silhouette's own colours are sampled from the donor's, row by row, so the port's
symbol is lit the same way as every other weapon's rather than flat.

    python h2_saw_hud_plate.py [--write]
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_tagref
import numpy as np
from PIL import Image

B = os.sep
H2EK = h2_tagref.H2EK
TAGS = os.path.join(H2EK, 'tags')
REL = B.join(['ui', 'hud', 'bitmaps', 'new_hud', 'backgrounds'])
DONOR = B.join([REL, 'battle_rifle_bkd'])
PORT = B.join([REL, 'saw_bkd'])
HUD = B.join(['ui', 'hud', 'saw'])
MODEL = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK',
                     'saw_3p_rm.xml')
TEMP = os.environ.get('TEMP', '.')

#: Where the silhouette sits, measured by diffing the battle rifle's plate against the
#: SMG's. Used when a diff comes back covering the whole plate, which means those two
#: images differ in more than the weapon.
FALLBACK_BOX = (105, 191, 5, 34)


def export(tag, prefix):
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-bitmap-tga', tag, prefix],
                   cwd=H2EK, capture_output=True, text=True)
    return sorted(glob.glob(prefix + os.path.basename(tag) + '_*.tga'))


def donor_images():
    """The donor plate's images, in order."""
    out = []
    for path in export(DONOR, os.path.join(TEMP, '_donor_')):
        out.append(np.asarray(Image.open(path).convert('RGBA')).astype(np.int16))
    return out


def weapon_box(donor, other):
    """Where the donor's plate differs from another weapon's: the silhouette."""
    d = np.abs(donor - other).sum(2)
    ys, xs = np.nonzero(d > 12)
    if not len(xs):
        return None
    return int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1


def saw_mask(w, h):
    """The SAW as a solid mask at that size, from the same geometry as the glyph."""
    import h3_weapon_glyph as wg
    verts, idx = wg.mesh(MODEL)
    cov = wg.close_gaps(wg.silhouette(verts, idx, w, h, margin=0), 3)
    px = wg.stylise(cov)
    return np.array([[1 if px[y * w + x][0] else 0 for x in range(w)]
                     for y in range(h)])


def repaint(donor, box, mask):
    """The donor plate with its weapon erased and the port's drawn in its place.

    The plate behind the weapon is a smooth gradient, so it is rebuilt by interpolating
    each row between the pixels either side of the box -- both of which are plate, never
    weapon. That is steadier than averaging other weapons' plates together, which leaves
    the seams of whatever they happened to cover.
    """
    x0, x1, y0, y1 = box
    out = donor.copy()
    for y in range(y0, y1):
        left = donor[y, max(x0 - 1, 0)].astype(float)
        right = donor[y, min(x1, donor.shape[1] - 1)].astype(float)
        span = max(x1 - x0, 1)
        for x in range(x0, x1):
            t = (x - x0 + 1) / (span + 1)
            out[y, x] = (left * (1 - t) + right * t).astype(np.int16)

    ink = donor[y0:y1, x0:x1, 3] > 0
    region = donor[y0:y1, x0:x1]
    for y in range(y1 - y0):
        row = region[y][ink[y]] if ink[y].any() else None
        colour = (row.mean(0) if row is not None and len(row)
                  else np.array([40, 190, 255, 255], dtype=float))
        for x in range(x1 - x0):
            if mask[y][x]:
                out[y0 + y, x0 + x] = colour.astype(np.int16)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    donor = donor_images()
    other = [np.asarray(Image.open(p).convert('RGBA')).astype(np.int16)
             for p in export(B.join([REL, 'smg_bkd']), os.path.join(TEMP, '_other_'))]
    print('%d image(s) in the donor plate' % len(donor))

    sheets = []
    for idx, img in enumerate(donor):
        box = (weapon_box(img, other[idx])
               if idx < len(other) and other[idx].shape == img.shape else None)
        # images past the first pair are the half and quarter screen variants, whose
        # weapon sits in the same place; a box covering the whole plate means the two
        # differ in more than the weapon and is not one
        if not box or (box[1] - box[0]) > img.shape[1] * 0.8:
            box = FALLBACK_BOX
        mask = saw_mask(box[1] - box[0], box[3] - box[2])
        sheets.append(Image.fromarray(
            np.clip(repaint(img, box, mask), 0, 255).astype('uint8'), 'RGBA'))
        print('   image %d: weapon box x %d..%d y %d..%d' % ((idx,) + box))

    # ONLY the first image. Stacking all four into one colour plate makes tool import a
    # single 206x152 bitmap, because a multi-image interface bitmap is split by separator
    # colours this does not write -- and the widget asks for sequence 0 at every screen
    # size anyway, so the other three were never drawn.
    sheet = sheets[0]
    data = os.path.join(H2EK, 'data', REL)
    os.makedirs(data, exist_ok=True)
    tif = os.path.join(data, 'saw_bkd.tif')
    sheet.save(tif, compression=None)
    print('   wrote %s (%dx%d)' % (tif, sheet.width, sheet.height))
    if not a.write:
        print('(dry run -- pass --write)')
        return

    dest = os.path.join(TAGS, PORT + '.bitmap')
    if not os.path.exists(dest):
        shutil.copy(os.path.join(TAGS, DONOR + '.bitmap'), dest)
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'bitmaps', REL],
                       cwd=H2EK, capture_output=True, text=True)
    for line in ((p.stdout or '') + (p.stderr or '')).replace(chr(13), chr(10)).split(chr(10)):
        line = ' '.join(line.split())
        if 'saw_bkd' in line or 'bitmap created' in line:
            print('   | %s' % line)
    hud = os.path.join(TAGS, HUD + '.new_hud_definition')
    have = h2_tagref.references(hud)
    if ('bitm', PORT) in have and ('bitm', DONOR) not in have:
        print('   the HUD already points at the port plate')
    else:
        h2_tagref.set_reference(hud, 'bitm', DONOR, PORT)


if __name__ == '__main__':
    main()
