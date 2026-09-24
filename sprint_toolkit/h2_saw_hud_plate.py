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

#: How far the drawing may be stretched vertically to fill the box. Bungie's symbols are
#: authored to the plate, not to the weapon's true proportions.
STRETCH = 1.4


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


def solidify(cov):
    """Close the one-pixel holes a thin weapon leaves when it is shrunk to 29 rows.

    Bungie's symbols are CHUNKY: solid blocks with a few deliberate cutouts. A 13836
    triangle gun projected this small breaks into slivers instead, and a sliver with a
    part-lit pixel either side of it reads as a scratch rather than as a gun. So any
    pixel with solid neighbours on both sides, across or down, is filled in.
    """
    out = cov.copy()
    full = cov >= 0.999
    across = np.zeros_like(full)
    down = np.zeros_like(full)
    across[:, 1:-1] = full[:, :-2] & full[:, 2:]
    down[1:-1, :] = full[:-2, :] & full[2:, :]
    out[across | down] = 1.0
    return out


def saw_mask(w, h, ss=4):
    """The SAW drawn side on as coverage and shading, the way the shipped plates are.

    A solid silhouette is the wrong picture. Bungie's symbols are SHADED drawings -- the
    Battle Rifle's runs from (0,151,131) on average up to (0,228,236) at its brightest,
    with interior structure -- so a flat blob at one colour reads as a smudge however
    good the outline is, which is what the first version of this produced.

    So the mesh is rasterised properly: an orthographic side view with a z buffer, at
    four times the final size, shading each triangle by how much its normal faces the
    light. Coverage comes out of the same pass as the fraction of subpixels that were
    hit, which gives the edges their antialiasing for free.

    Returns (coverage 0..1, shade 0..1), both h x w.
    """
    import h3_weapon_glyph as wg
    verts, idx = wg.mesh(MODEL)
    W, H = w * ss, h * ss
    xs = [v[0] for v in verts]
    zs = [v[2] for v in verts]
    # Fit the width, then stretch to fill the height, up to STRETCH. Every shipped symbol
    # spans the box top to bottom; a long thin LMG drawn to a single scale would sit in a
    # band across the middle, and the plate's colour is a GRADIENT down the box, so it
    # would also come out flat green instead of running green to blue like the rest.
    ex, ez = max(xs) - min(xs), max(zs) - min(zs)
    sx = W / ex
    sz = min(H / ez, sx * STRETCH)
    ox, oy = (W - ex * sx) / 2.0, (H - ez * sz) / 2.0
    px = [((ox + (v[0] - min(xs)) * sx), (H - oy - (v[2] - min(zs)) * sz)) for v in verts]

    depth = np.full((H, W), 1e9)
    shade = np.zeros((H, W))
    light = np.array([0.0, -0.80, 0.60])          # from the viewer, a little above
    for t in range(len(idx) - 2):
        i0, i1, i2 = idx[t], idx[t + 1], idx[t + 2]
        if i0 == i1 or i1 == i2 or i0 == i2:
            continue                               # degenerate strip stitch
        p = [px[i0], px[i1], px[i2]]
        x0 = max(int(min(q[0] for q in p)), 0)
        x1 = min(int(max(q[0] for q in p)) + 1, W)
        y0 = max(int(min(q[1] for q in p)), 0)
        y1 = min(int(max(q[1] for q in p)) + 1, H)
        if x1 <= x0 or y1 <= y0:
            continue
        ax, ay = p[0]
        bx, by = p[1]
        cx, cy = p[2]
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-9:
            continue
        # the triangle's own depth and its facing, flat shaded: a weapon symbol at
        # twenty-nine pixels tall gains nothing from interpolating either
        d = (verts[i0][1] + verts[i1][1] + verts[i2][1]) / 3.0
        n = np.cross(np.subtract(verts[i1], verts[i0]), np.subtract(verts[i2], verts[i0]))
        ln = np.linalg.norm(n)
        lit = 0.25 if ln < 1e-9 else 0.25 + 0.75 * abs(float(np.dot(n / ln, light)))
        yy, xx = np.mgrid[y0:y1, x0:x1]
        gx, gy = xx + 0.5, yy + 0.5
        l0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / det
        l1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / det
        inside = (l0 >= 0) & (l1 >= 0) & (l0 + l1 <= 1) & (d < depth[y0:y1, x0:x1])
        if inside.any():
            depth[y0:y1, x0:x1][inside] = d
            shade[y0:y1, x0:x1][inside] = lit

    hit = (depth < 1e9).astype(float)
    cov = solidify(hit.reshape(h, ss, w, ss).mean((1, 3)))
    lit = np.where(cov > 0,
                   (shade * hit).reshape(h, ss, w, ss).sum((1, 3))
                   / np.maximum(hit.reshape(h, ss, w, ss).sum((1, 3)), 1), 0.0)
    return cov, lit


def symbol_ramp(donor, box):
    """The two ends of the gradient the donor's symbol is drawn with.

    Measured across the battle rifle, the SMG and the shotgun, and they agree. A symbol
    is BLUE at a near constant 215, and its GREEN is a ramp -- but the ramp belongs to
    the SYMBOL, not to the plate: it runs from about 225 at whatever row the weapon
    starts on down to about 7 at the row it ends on, whichever rows those are. The
    shotgun's drawing spans rows 4..24 and ramps 218..14 over exactly that span, while
    the plate underneath is running 189..22 there. So it is stretched to fit the weapon.

    That is also why the gradient reads as "slow, then sudden": green only overtakes
    blue in the last few rows at the top, so the shape is blue almost all the way up and
    then turns cyan and white right at the end.

    Sampling the donor row by row, which is what this did before, gets the top wrong:
    the plate's own green is 222 up there, so every background pixel passes for symbol
    and the port's top comes out plate coloured and faded.
    """
    reg = donor[box[2]:box[3], box[0]:box[1]].astype(float)
    rows = []
    for y in range(reg.shape[0]):
        bg = np.median(donor[box[2] + y, 10:100], 0)
        # BLUE above this ROW's background blue: the plate has none, the symbol has 215
        ink = reg[y][reg[y][:, 2] > bg[2] + 60]
        rows.append(ink.mean(0) if len(ink) >= 3 else None)
    lit = [y for y, r in enumerate(rows) if r is not None]
    if not lit:
        return np.array([0, 225, 215, 250.0]), np.array([0, 7, 215, 250.0])
    return rows[lit[0]], rows[lit[-1]]


def repaint(donor, box, mask):
    """The donor plate with its weapon erased and the port's drawn in its place.

    The plate behind the weapon is a smooth gradient, so it is rebuilt by interpolating
    each row between the pixels either side of the box -- both of which are plate, never
    weapon. That is steadier than averaging other weapons' plates together, which leaves
    the seams of whatever they happened to cover.

    The port's drawing is then composited over that, its own gradient stretched over its
    own vertical extent the way every shipped symbol's is, with coverage doing the
    blending so the edges are antialiased against the real background rather than cut out
    of it.
    """
    cov, _lit = mask
    x0, x1, y0, y1 = box
    out = donor.copy()
    for y in range(y0, y1):
        left = donor[y, max(x0 - 1, 0)].astype(float)
        right = donor[y, min(x1, donor.shape[1] - 1)].astype(float)
        span = max(x1 - x0, 1)
        for x in range(x0, x1):
            t = (x - x0 + 1) / (span + 1)
            out[y, x] = (left * (1 - t) + right * t).astype(np.int16)

    top, bottom = symbol_ramp(donor, box)
    drawn = [y for y in range(y1 - y0) if cov[y].max() > 0]
    first, last = (drawn[0], drawn[-1]) if drawn else (0, y1 - y0 - 1)
    span = max(last - first, 1)
    for y in range(y1 - y0):
        t = min(max((y - first) / float(span), 0.0), 1.0)
        colour = top + (bottom - top) * t
        for x in range(x1 - x0):
            c = cov[y][x]
            if c <= 0:
                continue
            base = out[y0 + y, x0 + x].astype(float)
            out[y0 + y, x0 + x] = (base * (1 - c) + colour * c).astype(np.int16)
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
