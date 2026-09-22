r"""Draw a Halo 3 ammo meter for a magazine Halo 3 never shipped one for.

`ui\chud\bitmaps\ballistic_meters` is a 1024x512 sheet of 20 sprites, and each is a GRID
OF TICKS whose columns times rows equals exactly the magazine it serves. The BLUE channel
of a tick is its threshold -- it counts down from the magazine size to 1, left to right
then top to bottom -- and the alpha channel carries the artwork. Red is 0 and green is 5
on every tick, so a tick is (0, 5, threshold) masked by a shape.

    sprite  grid    ticks   weapon
    #2      6 x 2      12   shotgun
    #11     16 x 2     32   assault rifle
    #7      18 x 2     36   battle rifle
    #10     20 x 3     60   smg          <- the largest Halo 3 ships

A 72-round port has nothing to point at, which is why the SAW's meter could not show 72
bullets: cloning the Assault Rifle's HUD gave it a 32-tick grid. So one is drawn.

WHERE IT GOES. Sprites #1, #18 and #19 are used by none of the 66 chud tags in the
campaign, and #19 is 309x81 -- the same three-row footprint as the SMG's, holding 16x3.
Redrawing it as 24x3 needs no new sequence, no bounds change and no structural edit to
the tag: only pixels, and one Sequence Index on the weapon's own chud.

The tag stores its pixels RAW: the `tgda` blob's first 1024*512*4 bytes are byte-identical
to what `tool export-bitmap-tga` writes, so they can be patched in place, exactly as the
Halo 1 tick sheet was.

    python h3_meter_art.py                    # measure and show the plan
    python h3_meter_art.py --write [--rounds 72] [--sprite 19]
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                   # noqa: E402

B = os.sep
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
BITMAP = os.path.join(EK, 'tags', 'ui', 'chud', 'bitmaps', 'ballistic_meters.bitmap')
W, H = 1024, 512
BASE = W * H * 4
DONOR_SPRITE = 10          # the SMG's 20x3, whose tick shape is copied
TICK_RGB = (0, 5)          # red, green -- blue is the threshold


def pixels(tag):
    n = max((x for x in tag.nodes() if x.marker == 'tgda'), key=lambda x: x.length)
    return n.payload_at, n.length


def get(data, at, x, y):
    i = at + (y * W + x) * 4
    return data[i + 2], data[i + 1], data[i], data[i + 3]      # R, G, B, A


def put(data, at, x, y, r, g, b, a):
    i = at + (y * W + x) * 4
    data[i], data[i + 1], data[i + 2], data[i + 3] = b, g, r, a


def sprite_bounds(xml, index):
    import re
    s = open(xml, encoding='utf-8', errors='replace').read()
    seg = s[s.find('<block name="sequences"'):]
    parts = re.split(r'<element index="(\d+)" name="[^"]*">', seg)
    out = []
    for k in range(1, len(parts) - 1, 2):
        b = parts[k + 1]
        g = lambda n: (re.search(r'name="%s" value="(-?[\d.]+)"' % n, b) or [None, None])[1]
        if g('left') is None:
            continue
        out.append(tuple(float(g(n)) for n in ('left', 'right', 'top', 'bottom')))
    l, r, t, bo = out[index]
    return int(l * W), int(r * W), int(t * H), int(bo * H)


def groups(vals, thr=80):
    out, s = [], None
    for k, v in enumerate(vals):
        if v > thr and s is None:
            s = k
        elif v <= thr and s is not None:
            out.append((s, k))
            s = None
    if s is not None:
        out.append((s, len(vals)))
    return out


def read_stamp(data, at, x0, x1, y0, y1):
    """One tick's full RGBA, taken from the donor sprite's first column.

    The whole pixel, not just its alpha. The shipped ticks PREMULTIPLY the colour
    channels by coverage -- an edge pixel reads (0, 2, 60, 70) and a fully covered one
    (0, 5, 60, 255) -- so synthesising a flat (0, 5, threshold) over a copied alpha
    gets the interior right and every antialiased edge wrong. Copying the donor's
    pixels and overriding only the BLUE channel keeps the edges exactly as Bungie drew
    them; blue is the threshold and is NOT premultiplied (it reads 60 even at alpha 8).
    """
    cols = groups([max(get(data, at, cx, cy)[3] for cy in range(y0, y1))
                   for cx in range(x0, x1)])
    rows = groups([max(get(data, at, cx, cy)[3] for cx in range(x0, x1))
                   for cy in range(y0, y1)])
    ca, cb = cols[0]
    ra, rb = rows[0]
    stamp = [[get(data, at, x0 + cx, y0 + cy) for cx in range(ca, cb)]
             for cy in range(ra, rb)]
    return stamp, rows, len(cols)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--rounds', type=int, default=72)
    ap.add_argument('--sprite', type=int, default=19)
    ap.add_argument('--cols', type=int, default=24)
    ap.add_argument('--xml', default=os.path.join(os.environ.get('TEMP', '.'),
                                                  'bm_ball.xml'))
    a = ap.parse_args()
    if not os.path.exists(a.xml):
        raise SystemExit('need the bitmap xml: tool export-tag-to-xml ... %s' % a.xml)

    tag = h3tag.Tag(BITMAP)
    ok, cov, tot = tag.check()
    print('%s parses: %s (%d/%d)' % (os.path.basename(BITMAP), ok, cov, tot))
    at, blob_len = pixels(tag)
    print('pixel blob %d bytes, base image %d' % (blob_len, BASE))

    dx0, dx1, dy0, dy1 = sprite_bounds(a.xml, DONOR_SPRITE)
    stamp, drows, dcols = read_stamp(tag.data, at, dx0, dx1, dy0, dy1)
    sw, sh = len(stamp[0]), len(stamp)
    print('donor sprite #%d: %dx%d, %d cols x %d rows, tick stamp %dx%d'
          % (DONOR_SPRITE, dx1 - dx0, dy1 - dy0, dcols, len(drows), sw, sh))

    x0, x1, y0, y1 = sprite_bounds(a.xml, a.sprite)
    rows = a.rounds // a.cols
    if rows * a.cols != a.rounds:
        raise SystemExit('%d does not divide into %d columns' % (a.rounds, a.cols))
    print('target sprite #%d: %d,%d %dx%d -> %d cols x %d rows = %d ticks'
          % (a.sprite, x0, y0, x1 - x0, y1 - y0, a.cols, rows, a.rounds))
    pitch = (x1 - x0) / float(a.cols)
    print('   pitch %.1f px (donor %.1f), tick %d px wide' % (pitch, (dx1 - dx0) / float(dcols), sw))
    if pitch < sw:
        print('   tick is wider than the pitch; it will be narrowed to %d px' % int(pitch) - 1)

    if not a.write:
        print('\n(dry run -- pass --write)')
        return

    # The donor's own row positions, not evenly divided ones: its rows sit at fixed
    # offsets inside the sprite and matching them keeps the meter where the eye expects.
    if len(drows) >= rows:
        row_y = [drows[i][0] for i in range(rows)]
    else:
        step = (y1 - y0) // rows
        row_y = [i * step + max(0, (step - sh) // 2) for i in range(rows)]
    use_w = min(sw, max(3, int(pitch) - 2))
    for y in range(y0, y1):
        for x in range(x0, x1):
            put(tag.data, at, x, y, 0, 0, 0, 0)
    drawn = 0
    for r in range(rows):
        for c in range(a.cols):
            thr = a.rounds - (r * a.cols + c)
            cx = x0 + int(round(c * pitch + (pitch - use_w) / 2.0))
            cy = y0 + row_y[r]
            for sy in range(sh):
                for sx in range(use_w):
                    pr, pg, _pb, al = stamp[sy][int(sx * sw / float(use_w))]
                    if not al:
                        continue
                    px, py = cx + sx, cy + sy
                    if x0 <= px < x1 and y0 <= py < y1:
                        # the donor's own colour and coverage; only the threshold moves
                        put(tag.data, at, px, py, pr, pg, thr, al)
            drawn += 1
    print('drew %d ticks, blue %d..1, rows at y+%s'
          % (drawn, a.rounds, row_y))

    # the mip that follows the base image, so the art matches if it is ever sampled
    if blob_len >= BASE + (W // 2) * (H // 2) * 4:
        mat = at + BASE
        for y in range(y0 // 2, (y1 + 1) // 2):
            for x in range(x0 // 2, (x1 + 1) // 2):
                acc = [0, 0, 0, 0]
                for dy in (0, 1):
                    for dx in (0, 1):
                        r_, g_, b_, al = get(tag.data, at, min(x * 2 + dx, W - 1),
                                             min(y * 2 + dy, H - 1))
                        acc[0] += r_; acc[1] += g_; acc[2] += b_; acc[3] += al
                i = mat + (y * (W // 2) + x) * 4
                tag.data[i] = acc[2] // 4
                tag.data[i + 1] = acc[1] // 4
                tag.data[i + 2] = acc[0] // 4
                tag.data[i + 3] = acc[3] // 4
        print('mip level updated')

    ok, cov, tot = tag.check()
    print('tag parses: %s (%d/%d)' % (ok, cov, tot))
    if not ok:
        raise SystemExit('not saved')
    tag.save(BITMAP)
    print('wrote %s' % BITMAP)


if __name__ == '__main__':
    main()
