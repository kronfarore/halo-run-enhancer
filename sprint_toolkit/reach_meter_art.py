r"""Give the Reach SAW its own ammo meter -- a NEW bitmap, nothing taken from a live weapon.

HOW REACH DRAWS AN AMMO METER. The chud's `meter` bitmap widget reads the raw
`weapon ammo loaded` count and draws `ui\chud\bitmaps\ballistic_meters_2_rows`. That tag
has NO sequences: it is one 320x48 a8r8g8b8 image (plus one 160x24 mip), and it is the
Halo 3 encoding exactly -- the BLUE channel of every tick is its threshold, counting down
column by column (top 40, bottom 39, next column 38 / 37, ...), red and green are the
constants 48 and 2, and alpha is the tick's shape. The gaps between ticks carry their
neighbour's threshold too, so filtering cannot bleed a wrong value in. The mip keeps the
exact thresholds per tick.

It is a 40-round meter. The Spike Rifle (40) uses the whole sheet; the Assault Rifle
(32) uses the same sheet with MANUAL TEXTURE COORDINATES 0,34,24,160 to crop it. The SAW
cloned the Assault Rifle's chud, so it showed the Assault Rifle's cropped strip.

WHAT THIS DOES. It writes `ui\chud\bitmaps\saw_ballistic_meter` -- a clone of the sheet's
tag, so format, size and mip chain are the shipped ones, with its pixels redrawn in place:
72 ticks as 24 columns of 3, thresholds 72 -> 1 in the same column order, the tick shape
taken from the shipped tick and scaled to the smaller cell. Then it points the SAW's chud
meter widget at the new tag and sets its texture coordinates to 0,0,0,0 like the Spike
Rifle's, so the whole meter shows. The shared sheet and every other chud are untouched.

The pixels are stored RAW in the tag's `tgda`: level 0 then the mip, 76,800 bytes, so the
redraw is the same size and is patched in place with no import.

    python reach_meter_art.py              # plan and preview
    python reach_meter_art.py --write
"""
import argparse
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402
import h3_kit                                                   # noqa: E402
from PIL import Image                                           # noqa: E402

B = os.sep
BITMAPS = B.join(['ui', 'chud', 'bitmaps'])
SHEET = BITMAPS + B + 'ballistic_meters_2_rows'
OURS = BITMAPS + B + 'saw_ballistic_meter'
CHUD = B.join(['ui', 'chud', 'saw'])

W, H, MW, MH = 320, 48, 160, 24
PAYLOAD = (W * H + MW * MH) * 4
RED, GREEN = 48, 2                         # the shipped constants on every tick
ROUNDS, COLS, ROWS = 72, 24, 3
X0, PITCH_X, TICK_W = 4, 13, 8             # 24 x 13 = 312 wide, inside 320
Y0, PITCH_Y, TICK_H = 2, 15, 12            # 3 x 15 = 45 tall, inside 48
#: the Assault Rifle's crop, as the cloned chud still carries it -> the Spike Rifle's
TEXCOORDS_OLD, TEXCOORDS_NEW = (0, 34, 24, 160), (0, 0, 0, 0)


def payload_node(tag):
    nodes = [n for n in tag.nodes() if n.marker == 'tgda' and n.length == PAYLOAD]
    if len(nodes) != 1:
        raise SystemExit('expected one %d-byte pixel chunk, found %d' % (PAYLOAD, len(nodes)))
    return nodes[0]


def shipped_tick(data):
    """The alpha shape of the sheet's first tick (9 x 20 at 4,3)."""
    im = Image.frombytes('RGBA', (W, H), data[:W * H * 4], 'raw', 'BGRA')
    return im.split()[3].crop((4, 3, 13, 23))


def threshold(x, y, cols, rows, x0, px, y0, py, rounds):
    c = min(cols - 1, max(0, (x - x0 + (px - TICK_W) // 2) // px))
    r = min(rows - 1, max(0, (y - y0 + (py - TICK_H) // 2) // py))
    return rounds - (c * rows + r)


def draw(tick):
    """(level 0, mip) as BGRA bytes."""
    shape = tick.resize((TICK_W, TICK_H), Image.LANCZOS)
    alpha = Image.new('L', (W, H), 0)
    for c in range(COLS):
        for r in range(ROWS):
            alpha.paste(shape, (X0 + c * PITCH_X, Y0 + r * PITCH_Y))
    img = Image.new('RGBA', (W, H))
    px, ap = img.load(), alpha.load()
    for y in range(H):
        for x in range(W):
            t = threshold(x, y, COLS, ROWS, X0, PITCH_X, Y0, PITCH_Y, ROUNDS)
            px[x, y] = (RED, GREEN, t, ap[x, y])
    # the mip keeps exact thresholds (nearest) and averages only the shape
    mip = Image.new('RGBA', (MW, MH))
    mp = mip.load()
    for y in range(MH):
        for x in range(MW):
            r, g, b, _a = px[2 * x, 2 * y]
            a = sum(ap[2 * x + i, 2 * y + j] for i in (0, 1) for j in (0, 1)) // 4
            mp[x, y] = (r, g, b, a)
    return img, mip


def grid(img):
    """The blue value at every tick centre, row by row -- what the engine compares."""
    p = img.load()
    return [[p[X0 + c * PITCH_X + TICK_W // 2, Y0 + r * PITCH_Y + TICK_H // 2][2]
             for c in range(COLS)] for r in range(ROWS)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if not h3_kit.IS_REACH:
        raise SystemExit('Reach only -- refusing to run against %s' % h3_kit.banner())

    src = os.path.join(h3_kit.TAGS, SHEET + '.bitmap')
    dst = os.path.join(h3_kit.TAGS, OURS + '.bitmap')
    sheet = h3tag.Tag(src)
    data = bytes(sheet.data[payload_node(sheet).payload_at:][:PAYLOAD])
    img, mip = draw(shipped_tick(data))
    g = grid(img)
    print('%d ticks as %d columns of %d' % (ROUNDS, COLS, ROWS))
    for r, line in enumerate(g):
        print('   row %d  %s ... %s' % (r, line[:6], line[-3:]))
    flat = sorted(v for line in g for v in line)
    if flat != list(range(1, ROUNDS + 1)):
        raise SystemExit('thresholds are not exactly 1..%d once each' % ROUNDS)

    preview = os.path.join(os.environ.get('TEMP', '.'), 'saw_meter_preview.png')
    show = Image.new('RGBA', (W * 3, H * 3), (20, 22, 26, 255))
    show.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), 235)] * 3
                                     + [img.split()[3]]).resize((W * 3, H * 3), Image.NEAREST))
    show.save(preview)
    print('preview -> %s' % preview)

    if not a.write:
        print('\n(dry run -- pass --write)')
        return

    shutil.copyfile(src, dst)
    ours = h3tag.Tag(dst)
    node = payload_node(ours)
    blob = img.tobytes('raw', 'BGRA') + mip.tobytes('raw', 'BGRA')
    assert len(blob) == PAYLOAD
    ours.data[node.payload_at:node.payload_at + PAYLOAD] = blob
    ok, covered, total = ours.check()
    if not ok:
        raise SystemExit('new bitmap no longer parses -- not saved')
    ours.save(dst)
    print('wrote %s (%d bytes)' % (OURS, len(ours.data)))

    cp = os.path.join(h3_kit.TAGS, CHUD + '.chud_definition')
    chud = h3tag.Tag(cp)
    n = chud.repoint(SHEET, OURS, 'bitm')
    old = struct.pack('<4h', *TEXCOORDS_OLD)
    hits = []
    at = chud.data.find(old)
    while at >= 0:
        hits.append(at)
        at = chud.data.find(old, at + 1)
    if len(hits) > 1:
        raise SystemExit('texture coordinates matched %d times -- refusing to guess' % len(hits))
    for at in hits:
        struct.pack_into('<4h', chud.data, at, *TEXCOORDS_NEW)
    ok, covered, total = chud.check()
    if not ok or n != 1:
        raise SystemExit('chud not saved (repointed %d, tree %s)' % (n, ok))
    chud.save(cp)
    print('chud meter -> %s, texture coordinates %s -> %s'
          % (OURS, TEXCOORDS_OLD, TEXCOORDS_NEW if hits else '(already 0,0,0,0)'))


if __name__ == '__main__':
    main()
