r"""Bring the Halo 4 weapon's own CROSSHAIR across with the port.

The port was wearing the cut GPMG's reticle -- `ui\hud\bitmaps\new_hud\crosshairs\hud_reticles`
sequence 16, a broken circle with four tick marks, which reads as a scope sight the SAW has
no business carrying. (It is only the reticle: the port's HUD does own scope_mask, 2x,
distance_meter and four bracket widgets, but every one of them is gated on `unit is zoomed`
and the weapon's `magnification levels` is 0, so none of them can ever draw.)

**The Halo 4 reticle is fully specified in H4EK's tags, so it can be ported rather than
guessed.** `ui\hud\weapons\human\lmg\lmg.cui_screen` builds it out of:

    img_saw_quarter   96x96   an L-shaped corner bracket, drawn 32x32 at +-4 / +-36,
                              mirrored into all four quadrants (flipx / flipy)
    vertical_tick     24x24   drawn 8x8 at +-5..13 above and below centre, opacity 0.55
    horizontal_tick   24x24   the same to left and right

So the whole reticle is a square bracket frame with four small ticks, and this rebuilds
exactly that: `h4_bitmap.py` decodes the three source bitmaps, the four quadrants are
mirrored and placed at Halo 4's own offsets, and the lot is scaled so it fills the same
footprint the donor's reticle filled -- the widget's box does not change, so anything
smaller would just be a smaller crosshair.

Halo 2's own convention is kept for the colour: its reticles are flat blue with the shape
in the alpha, and the widget's shader tints them (green for a friendly, grey for an
invincible target). So the H4 art supplies coverage and the donor supplies the colour.

The port gets its OWN one-image bitmap rather than a new sequence in the shared sheet,
which keeps every other weapon's reticle exactly as Bungie left it. That moves the
sequence index from 16 to 0 on the three crosshair widgets.

    python h2_saw_reticle.py [--write]
"""
import argparse
import glob
import os
import re
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
H4EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H4EK')
TAGS = os.path.join(H2EK, 'tags')
REL = B.join(['ui', 'hud', 'bitmaps', 'new_hud', 'crosshairs'])
DONOR = B.join([REL, 'hud_reticles'])
NAME = 'saw_reticle'
PORT = B.join([REL, NAME])
HUD = B.join(['ui', 'hud', 'saw'])
TEMP = os.environ.get('TEMP', '.')

DONOR_SEQUENCE = 16                 # the GPMG's, and so the port's

#: How much of the donor's footprint the reticle fills. The donor is a CIRCLE inscribed in
#: its 220x222 image; the SAW's is a square bracket frame, so drawn to the same footprint
#: its corners reach further out than the circle ever does and it reads as much bigger on
#: screen. Reported in game as "huge" at 1.0. The bitmap keeps the donor's size -- only the
#: art inside it shrinks -- so no widget geometry changes.
FOOTPRINT = 0.6
H4_ART = B.join(['ui', 'hud', 'weapons', 'human', 'lmg', 'bitmap'])

#: Halo 4's own layout, in its HUD units: (bitmap, left, top, w, h, flipx, flipy, opacity)
LAYOUT = [
    ('img_saw_quarter', 4, 3, 32, 32, False, False, 1.0),      # bottom right
    ('img_saw_quarter', 4, -35, 32, 32, False, True, 1.0),     # top right
    ('img_saw_quarter', -36, 3, 32, 32, True, False, 1.0),     # bottom left
    ('img_saw_quarter', -36, -35, 32, 32, True, True, 1.0),    # top left
    ('vertical_tick', -4, 5, 8, 8, False, False, 0.55),        # below
    ('vertical_tick', -4, -13, 8, 8, False, False, 0.55),      # above
    ('horizontal_tick', -13, -4, 8, 8, False, False, 0.55),    # left
    ('horizontal_tick', 5, -4, 8, 8, False, False, 0.55),      # right
]


def h4_art(name):
    """One of the Halo 4 reticle bitmaps, decoded to RGBA."""
    out = os.path.join(TEMP, 'h4_%s.png' % name)
    if not os.path.exists(out):
        tag = os.path.join(H4EK, 'tags', H4_ART, name + '.bitmap')
        meta = os.path.join(TEMP, 'h4_%s.xml' % name)
        subprocess.run([os.path.join(H4EK, 'tool.exe'), 'export-tag-to-xml', tag, meta],
                       cwd=H4EK, capture_output=True, text=True)
        x = open(meta, encoding='utf-8', errors='replace').read()
        w = int(re.search(r'name="width" value="(\d+)"', x).group(1))
        h = int(re.search(r'name="height" value="(\d+)"', x).group(1))
        fmt = re.search(r'name="format" value="([^"]+)"', x).group(1)
        mips = int(re.search(r'name="mipmap count" value="(\d+)"', x).group(1))
        subprocess.run([sys.executable, os.path.join(HERE, 'h4_bitmap.py'), tag,
                        str(w), str(h), fmt, str(max(mips, 1)), out],
                       capture_output=True, text=True)
    return Image.open(out).convert('RGBA')


def donor_image(index=DONOR_SEQUENCE):
    """The reticle the port is replacing, for its size and its colour."""
    pre = os.path.join(TEMP, '_ret_')
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-bitmap-tga', DONOR, pre],
                   cwd=H2EK, capture_output=True, text=True)
    files = sorted(glob.glob(pre + 'hud_reticles_*.tga'))
    return Image.open(files[index]).convert('RGBA')


def compose(donor):
    """Halo 4's reticle, at the size and in the colour Halo 2 draws the donor's."""
    w, h = donor.size
    a = np.asarray(donor)
    ink = a[:, :, 3] > 0
    colour = a[:, :, :3][ink].mean(0) if ink.any() else np.array([0, 0, 202.0])

    # Halo 4 lays the reticle out in a box 72 units across (-36..+36). Scale that to the
    # donor's own footprint so the crosshair is the same size on screen as the one it
    # replaces -- the widget's box is not changing.
    scale = w * FOOTPRINT / 72.0
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    cx, cy = w / 2.0, h / 2.0
    for name, left, top, bw, bh, fx, fy, opacity in LAYOUT:
        art = h4_art(name)
        if fx:
            art = art.transpose(Image.FLIP_LEFT_RIGHT)
        if fy:
            art = art.transpose(Image.FLIP_TOP_BOTTOM)
        art = art.resize((max(int(round(bw * scale)), 1), max(int(round(bh * scale)), 1)),
                         Image.LANCZOS)
        # Halo 4's art is white with the shape in the alpha; Halo 2's is flat blue with
        # the shape in the alpha. Keep the coverage, take the donor's colour.
        px = np.asarray(art).astype(float)
        px[:, :, 0], px[:, :, 1], px[:, :, 2] = colour[0], colour[1], colour[2]
        px[:, :, 3] *= opacity
        piece = Image.fromarray(px.astype('uint8'), 'RGBA')
        out.alpha_composite(piece, (int(round(cx + left * scale)),
                                    int(round(cy + top * scale))))
    return out


def sequence_indices(tag):
    """Every crosshair widget's three sequence index fields, as tool.exe reports them."""
    out = os.path.join(TEMP, '_hud_seq.xml')
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-tag-to-xml',
                    os.path.abspath(tag), out], cwd=H2EK, capture_output=True, text=True)
    x = open(out, encoding='utf-8', errors='replace').read()
    seg = x[x.index('<block name="bitmap widgets"'):]
    if '<block name="text widgets"' in seg:
        seg = seg[:seg.index('<block name="text widgets"')]
    rows = []
    for part in re.split(r'<element index="(\d+)"[^>]*>', seg)[1:]:
        nm = re.search(r'string id">([^<]+)<', part)
        ref = re.search(r'type="bitm">([^<]+)<', part)
        sq = re.findall(r'name="(fullscreen|halfscreen|quarterscreen) sequence index"'
                        r'[^>]*>(-?\d+)', part)
        if nm and ref and sq:
            rows.append((nm.group(1), ref.group(1), [int(v) for _k, v in sq]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    donor = donor_image()
    art = compose(donor)
    d = np.asarray(donor)
    n = np.asarray(art)
    print('donor reticle %dx%d, %d ink pixels; the port\'s %d'
          % (donor.width, donor.height, int((d[:, :, 3] > 0).sum()),
             int((n[:, :, 3] > 0).sum())))

    data = os.path.join(H2EK, 'data', REL)
    os.makedirs(data, exist_ok=True)
    tif = os.path.join(data, NAME + '.tif')
    art.save(tif, compression=None)
    print('   wrote %s' % tif)
    png = os.path.join(TEMP, 'saw_reticle_preview.png')
    Image.alpha_composite(Image.new('RGBA', art.size, (20, 20, 24, 255)), art).save(png)
    print('   preview %s' % png)
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
        if NAME in line or 'bitmap created' in line:
            print('   | %s' % line)

    hud = os.path.join(TAGS, HUD + '.new_hud_definition')
    have = h2_tagref.references(hud)
    if ('bitm', PORT) in have:
        print('   the HUD already points at the port reticle')
    else:
        h2_tagref.set_reference(hud, 'bitm', DONOR, PORT, every=True)
    print('the crosshair widgets now read:')
    for name, ref, seq in sequence_indices(hud):
        if 'reticle' in ref or 'crosshair' in name:
            print('   %-22s %-46s %s' % (name, ref.split(B)[-1], seq))


if __name__ == '__main__':
    main()
