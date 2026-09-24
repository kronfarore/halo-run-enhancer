r"""Step 7: an ammo meter that counts the SAW's 72 rounds instead of the donor's 36.

The cut GPMG's HUD is a Battle Rifle HUD -- its background, its scope mask and its ammo
meter all come from `battle_rifle_*`. The Battle Rifle holds 36 rounds and its meter is
drawn as 36 ticks, which is exactly what the first look in game showed with 72 rounds
loaded: every tick worth two.

Halo 2 draws this as one bitmap of tick art, revealed as the magazine empties, so the
count is purely a property of the ART. Bungie's own two, measured:

    battle_rifle_meter  197x34   2 rows of 18 = 36   tick 6px wide, row pitch 17
    smg_meter           198x42   3 rows of 20 = 60   tick 6px wide, row pitch 14

The tick is **6 pixels wide in both**; what changes with the magazine is how many rows
there are and how tightly they are spaced. So 72 goes in as **3 rows of 24**, keeping the
6px tick and the Battle Rifle's 197x34 canvas so the widget it sits in does not move.
Only the row pitch tightens, from 17 to 11.

The tick sprite and the colour ramp are lifted from the Battle Rifle's own meter rather
than drawn: cyan at the first round through to green at the last, which is Bungie's, and
it then reads as the same HUD with more ammunition in it.

    python h2_saw_meter.py [--rounds 72] [--show]
"""
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
DONOR_METER = B.join(['ui', 'hud', 'bitmaps', 'new_hud', 'meters', 'battle_rifle_meter'])
REL = B.join(['ui', 'hud', 'bitmaps', 'new_hud', 'meters'])
DATA = os.path.join(H2EK, 'data', REL)
NAME = 'saw_meter'
DONOR_HUD = B.join(['ui', 'hud', 'gpmg'])
PORT_HUD = B.join(['ui', 'hud', 'saw'])
WEAPON = os.path.join(TAGS, 'objects', 'weapons', 'rifle', 'saw', 'saw.weapon')

#: The HUD's own weapon symbol, the one outside the text prompts. It is NOT a glyph:
#: the `backpack` widget draws a sequence of the new_hud backpack_weapons bitmap,
#: which is not a sprite sheet but a stack of separate 62x30 interface bitmaps, one
#: per weapon. So the port gets its own one-bitmap version and the widget points at
#: that -- nothing shared, and the sequence index stays 0.
BACKPACK = B.join(['ui', 'hud', 'bitmaps', 'new_hud', 'backpack_weapons'])
BACKPACK_PORT = B.join(['ui', 'hud', 'bitmaps', 'new_hud', 'saw_backpack'])
BACKPACK_SIZE = (62, 30)

ROUNDS = 72
CANVAS = (197, 34)          # the Battle Rifle's, so the HUD widget is untouched
TICK_W = 6                  # 6 in both of Bungie's meters, whatever the magazine


def donor_art():
    """The Battle Rifle's meter as an image, exported straight out of the tag."""
    out = os.path.join(os.environ.get('TEMP', '.'), '_h2meter')
    subprocess.run([os.path.join(H2EK, 'tool.exe'), 'export-bitmap-tga', DONOR_METER, out],
                   cwd=H2EK, capture_output=True, text=True)
    path = out + os.path.basename(DONOR_METER) + '_00_00.tga'
    if not os.path.exists(path):
        raise SystemExit('could not export %s' % DONOR_METER)
    return Image.open(path).convert('RGBA')


def tick_sprite(img):
    """One tick, cut out of the donor at full size, alpha and all."""
    a = np.asarray(img)
    alpha = a[:, :, 3]
    cols = [i for i in range(a.shape[1]) if alpha[:, i].sum() > 0]
    rows = [i for i in range(a.shape[0]) if alpha[i, :].sum() > 0]
    x0 = cols[0]
    y0, y1 = rows[0], rows[0] + (a.shape[0] // 2) - 2
    return img.crop((x0, y0, x0 + TICK_W, y1))


def thresholds(n):
    """The blue staircase: 254 down to 4, spread over however many ticks there are.

    Measured off both shipped meters. The Battle Rifle runs 254..4 across its 36 ticks
    and the SMG 254..4 across its 60, so the SPAN is fixed whatever the magazine holds
    and only the step changes -- 7.1 for the Battle Rifle, 4.2 for the SMG, 3.5 here.
    """
    return [int(round(254 - i * 250.0 / max(n - 1, 1))) for i in range(n)]


def build(rounds=ROUNDS, rows=3):
    donor = donor_art()
    sprite = tick_sprite(donor)
    per_row = -(-rounds // rows)
    w, h = CANVAS
    pitch = w / float(per_row)
    row_pitch = h / float(rows)
    tick_h = int(row_pitch) - 1
    small = np.asarray(sprite.resize((TICK_W, tick_h), Image.LANCZOS)).astype(np.uint8)

    sheet = np.zeros((h, w, 4), dtype=np.uint8)
    thr = thresholds(rounds)
    edges = [int(round(c * pitch)) for c in range(per_row)] + [w]
    bands = [int(round(r * row_pitch)) for r in range(rows)] + [h]

    # THE THRESHOLD FIELD FIRST, AND IT COVERS EVERY PIXEL.
    #
    # Blue is the threshold and it is a property of the CELL, not of the tick -- exactly
    # as in Halo 3, and measurable here: `battle_rifle_meter` has ZERO zero-blue pixels,
    # its blue running 11 columns of 254, 11 of 246, 11 of 238 with no gap anywhere, and
    # 17 rows then 17 rows down. The blank space between two ticks carries the same
    # threshold as the tick beside it.
    #
    # Painting blue only where a tick is opaque leaves 0 in every gap, and 0 means "still
    # loaded". The HUD samples the meter filtered, so each tick's outer rim mixes its own
    # threshold with the 0 beside it and keeps drawing after the tick itself has emptied:
    # an OUTLINE around every spent tick, travelling with the full/empty boundary. That
    # is the complaint, in both games, and it is not an alpha problem -- Bungie's own
    # ticks are softly antialiased (alpha 9..137), so hard-edging them fixes nothing.
    for r in range(rows):
        for c in range(per_row):
            i = min(r * per_row + c, rounds - 1)
            sheet[bands[r]:bands[r + 1], edges[c]:edges[c + 1], 2] = thr[i]

    # then the tick art over it: red, green and alpha, and blue is not touched
    for i in range(rounds):
        r, c = divmod(i, per_row)
        x = edges[c] + max((edges[c + 1] - edges[c] - TICK_W) // 2, 0)
        y = bands[r] + max((bands[r + 1] - bands[r] - tick_h) // 2, 0)
        if x + TICK_W > w or y + tick_h > h:
            continue
        for k in (0, 1, 3):
            sheet[y:y + tick_h, x:x + TICK_W, k] = small[:, :, k]
    print('   %d ticks, %d rows of %d, pitch %.2f x %.2f, tick %dx%d on a %dx%d sheet, '
          'blue %d..%d' % (rounds, rows, per_row, pitch, row_pitch, TICK_W, tick_h, w, h,
                           thr[-1], thr[0]))
    return Image.fromarray(sheet, 'RGBA')


def point(tag, cls, old, new):
    """Repoint unless it already points there, so a re-run is harmless."""
    have = h2_tagref.references(tag)
    if (cls, new) in have and (cls, old) not in have:
        print('   %-28s already points at the port' % os.path.basename(tag))
        return
    h2_tagref.set_reference(tag, cls, old, new)


def run_lines(p):
    """tool's output, one tidy line at a time."""
    text = (p.stdout or '') + (p.stderr or '')
    return text.replace(chr(13), chr(10)).split(chr(10))


def backpack():
    """The SAW drawn at the size the HUD's weapon symbol is, as its own bitmap."""
    import h3_weapon_glyph as wg
    from PIL import Image
    verts, idx = wg.mesh(os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common',
                                      'H3EK', 'saw_3p_rm.xml'))
    w, h = BACKPACK_SIZE
    cov = wg.close_gaps(wg.silhouette(verts, idx, w, h, margin=0), 3)
    px = wg.stylise(cov)
    im = Image.new('RGBA', (w, h))
    im.putdata([(r * 17, g * 17, b * 17, a * 17) for a, r, g, b in px])
    data = os.path.join(H2EK, 'data', os.path.dirname(BACKPACK_PORT))
    os.makedirs(data, exist_ok=True)
    tif = os.path.join(data, os.path.basename(BACKPACK_PORT) + '.tif')
    im.save(tif, compression=None)
    print('   %s  %dx%d, %d ink' % (os.path.basename(tif), w, h,
                                    sum(1 for q in px if q[0])))
    dest = os.path.join(TAGS, BACKPACK_PORT + '.bitmap')
    if not os.path.exists(dest):
        shutil.copy(os.path.join(TAGS, BACKPACK + '.bitmap'), dest)
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'bitmaps',
                        os.path.dirname(BACKPACK_PORT)],
                       cwd=H2EK, capture_output=True, text=True)
    for line in run_lines(p):
        line = ' '.join(line.split())
        if 'saw_backpack' in line or 'bitmap created' in line:
            print('   | %s' % line)
    hud = os.path.join(TAGS, PORT_HUD + '.new_hud_definition')
    point(hud, 'bitm', BACKPACK, BACKPACK_PORT)


def main():
    rounds = ROUNDS
    if '--rounds' in sys.argv:
        rounds = int(sys.argv[sys.argv.index('--rounds') + 1])
    art = build(rounds)
    os.makedirs(DATA, exist_ok=True)
    tif = os.path.join(DATA, NAME + '.tif')
    art.save(tif, compression=None)
    print('   wrote %s' % tif)
    if '--show' in sys.argv:
        png = os.path.join(os.environ.get('TEMP', '.'), 'saw_meter_preview.png')
        art.resize((art.size[0] * 3, art.size[1] * 3), Image.NEAREST).save(png)
        print('   preview %s' % png)
        return

    dest = os.path.join(TAGS, REL, NAME + '.bitmap')
    if not os.path.exists(dest):
        # seeded from the Battle Rifle's so the import keeps its settings, the same rule
        # the port's other bitmaps follow
        shutil.copy(os.path.join(TAGS, DONOR_METER + '.bitmap'), dest)
        print('   %s.bitmap seeded from battle_rifle_meter' % NAME)
    p = subprocess.run([os.path.join(H2EK, 'tool.exe'), 'bitmaps', REL],
                       cwd=H2EK, capture_output=True, text=True)
    for line in ((p.stdout or '') + (p.stderr or '')).replace('\r', '\n').split('\n'):
        line = ' '.join(line.split())
        if NAME in line or 'bitmap created' in line:
            print('   | %s' % line)

    hud = os.path.join(TAGS, PORT_HUD + '.new_hud_definition')
    if not os.path.exists(hud):
        shutil.copy(os.path.join(TAGS, DONOR_HUD + '.new_hud_definition'), hud)
        print('   %s cloned from the GPMG HUD' % PORT_HUD)
    point(hud, 'bitm', DONOR_METER, B.join([REL, NAME]))
    point(WEAPON, 'nhdt', DONOR_HUD, PORT_HUD)
    print('the HUD weapon symbol:')
    backpack()


if __name__ == '__main__':
    main()
