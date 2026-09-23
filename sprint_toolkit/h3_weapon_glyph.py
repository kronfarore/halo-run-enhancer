r"""Draw a ported weapon's pickup icon from its own geometry, and splice it into the font.

The pickup prompt's icon is a CHARACTER inside the message string (see
`h3_saw_pickup_icon`), rendered from maps\fonts\font_package_icon*.bin. Pointing the
prompt at a spare codepoint only helps if a glyph is actually there, and every spare one
already holds some other weapon's picture -- so the glyph has to be drawn.

It is not drawn by hand. The port's render model already describes the weapon, and
`tool export-tag-to-xml` writes its raw vertices and indices as plain text, so the icon
is an orthographic side view of the real mesh: correct by construction, no art pass.

Three things about the model XML cost time if they are rediscovered:

  * positions are COMPRESSED to 0..1 and have to be expanded through the compression
    bounds, or the weapon renders as a lens-shaped blob;
  * `position bounds 0` and `position bounds 1` are not min and max. They are six floats
    printed as two point3ds, and they pair up as (x lo, x hi), (y lo, y hi), (z lo, z hi).
    The giveaway is that the middle pair comes out symmetric -- that is the weapon's
    width, and a weapon is symmetric left to right;
  * `raw indices` is a triangle STRIP, not a list. Read as a list it draws 4739 scattered
    triangles instead of 8363 connected ones, and the result looks like a discus.

Style follows the shipped icons: a grey body with a bright outline, all of it white with
only the alpha varying, which is also the cheapest thing the codec can store -- two
pixels per byte. Alphas are snapped to the eight levels the white shorthand expresses so
nothing has to fall back to a literal.

The glyph is written IN PLACE. Payloads are padded to sixteen bytes, so as long as the
new one fits the slot the old one occupied, not a single offset in the package moves.
These packages are the LIVE ones the game reads, so a change shows up without a rebuild.

    python h3_weapon_glyph.py                       # render and report, touching nothing
    python h3_weapon_glyph.py --write
    python h3_weapon_glyph.py --restore             # put the shipped glyphs back
"""
import argparse, io, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_font_package as fp                                    # noqa: E402
import h3_font_codec as fc                                      # noqa: E402

B = os.sep
EK = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK')
MODEL_XML = os.path.join(EK, 'saw_3p_rm.xml')
BACKUP = os.path.join('E:' + B, 'HaloBackups', 'h3_live_fonts')
PACKAGES = ('font_package_icon.bin', 'font_package_icon_x2.bin',
            'font_package_icon_x3.bin')
GLYPH = 0xE128                  # what am_pickup / am_swap point at, for the SAW
FILL, EDGE = 10, 15             # body and outline alpha, both on the level table

#: Geometry to leave out of the silhouette, as world boxes
#: (x lo, x hi, z lo, z hi, |y| limit or None).
#:
#: Under the SAW's barrel sit TWO sub-assemblies that are real on the model and useless
#: on an icon. Side on at 123x39 each is a couple of pixels tall, separated from the body
#: by a one-pixel slot, and reads as a stray line ruled under the weapon:
#:
#:   1. a flat FULL-WIDTH slab, 132 triangles, x 0.078..0.215, z 0.003..0.013;
#:   2. a NARROW CENTRED rail, 94 triangles, x 0.090..0.217, z 0.010..0.021, and only
#:      |y| <= 0.0082 where the weapon is +-0.0375 wide. That lateral limit is what makes
#:      it separable at all: its z band overlaps the barrel, so an x/z box alone would
#:      bite into the barrel, and the rail is told apart by being thin, not by being low.
#:
#: The seam under 1 is real -- there is a band at z 0.0133..0.0150 holding no vertices at
#: all in this x range, which is where the assembly ends and the barrel begins.
#:
#: Dropping both leaves the barrel with a clean underside and costs no other detail.
#: Closing the slots instead was tried and merges the whole barrel into a blob.
#:
#: A triangle goes only when ALL THREE of its vertices are inside one box, so a box can
#: never punch a hole in geometry that merely passes through it.
EXCLUDE = ((0.077, 0.216, 0.0028, 0.0132, None),
           (0.089, 0.218, 0.0100, 0.0210, 0.009))


def mesh(path):
    """(vertices in world units, index strip) from a render_model XML."""
    lo = hi = None
    pos, idx, mode = [], [], None
    rp = re.compile(r'name="position" value="([-\d.e,]+)"')
    rw = re.compile(r'name="word" value="(-?\d+)"')
    rb = re.compile(r'name="position bounds [01]" value="([-\d.e,]+)"')
    for line in io.open(path, encoding='utf-8', errors='replace'):
        if hi is None:
            m = rb.search(line)
            if m:
                v = [float(x) for x in m.group(1).split(',')]
                if lo is None:
                    lo = v
                else:
                    f = lo + v          # six floats, paired per axis
                    lo, hi = (f[0], f[2], f[4]), (f[1], f[3], f[5])
                continue
        if 'name="raw vertices"' in line:
            mode = 'v'
            continue
        if 'name="raw indices"' in line:
            mode = 'i'
            continue
        if mode == 'v':
            m = rp.search(line)
            if m:
                pos.append(tuple(float(x) for x in m.group(1).split(',')))
        elif mode == 'i':
            m = rw.search(line)
            if m:
                idx.append(int(m.group(1)))
    V = [tuple(lo[k] + p[k] * (hi[k] - lo[k]) for k in range(3)) for p in pos]
    return V, idx


def dropped(V, exclude):
    """Which vertices sit inside an exclusion box."""
    out = set()
    for i, v in enumerate(V):
        for x0, x1, z0, z1, ymax in exclude:
            if x0 <= v[0] <= x1 and z0 <= v[2] <= z1 and (ymax is None or abs(v[1]) <= ymax):
                out.add(i)
                break
    return out


def silhouette(V, idx, W, H, ss=8, margin=2, exclude=EXCLUDE):
    """Coverage of an orthographic side view -- x across, z up -- antialiased."""
    from PIL import Image, ImageDraw
    skip = dropped(V, exclude) if exclude else set()
    a = [v[0] for v in V]
    b = [v[2] for v in V]
    ea, eb = max(a) - min(a), max(b) - min(b)
    s = min((W - 2 * margin) / ea, (H - 2 * margin) / eb)
    ox, oy = (W - ea * s) / 2.0, (H - eb * s) / 2.0
    im = Image.new('L', (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    P = [((ox + (a[i] - min(a)) * s) * ss, (H - oy - (b[i] - min(b)) * s) * ss)
         for i in range(len(V))]
    for t in range(len(idx) - 2):
        i0, i1, i2 = idx[t], idx[t + 1], idx[t + 2]
        if i0 == i1 or i1 == i2 or i0 == i2:
            continue                                   # degenerate strip stitch
        if i0 in skip and i1 in skip and i2 in skip:
            continue                                   # wholly inside an exclusion box
        d.polygon([P[i0], P[i1], P[i2]], fill=255)
    return im.resize((W, H), Image.LANCZOS)


def stylise(cov):
    """Coverage -> the shipped look: grey body, bright outline, white throughout."""
    from PIL import ImageFilter
    W, H = cov.size
    solid = cov.point(lambda v: 255 if v > 128 else 0)
    inner = solid.filter(ImageFilter.MinFilter(3))
    c, s, e = cov.load(), solid.load(), inner.load()
    out = []
    for y in range(H):
        for x in range(W):
            if s[x, y]:
                a = FILL if e[x, y] else EDGE
            else:
                a = min(fc.LEVELS, key=lambda v: abs(v - c[x, y] / 255.0 * 15))
            out.append((a, 15, 15, 15) if a else fc.CLEAR)
    return out


def slot_of(d, g, at):
    """How many payload bytes the glyph at `at` may take without moving anything."""
    starts = sorted(v[4] for v in g.values())
    nxt = min([s for s in starts if s > at] or [len(d)])
    return nxt - at - 16


def splice(path, cp, payload):
    d = bytearray(io.open(path, 'rb').read())
    g = fp.glyphs(bytes(d))
    font, w, h, old, at = g[cp]
    room = slot_of(bytes(d), g, at)
    if len(payload) > room:
        raise SystemExit('%s: %d bytes will not fit the %d byte slot'
                         % (os.path.basename(path), len(payload), room))
    struct.pack_into('<I', d, at + 4, len(payload))
    d[at + 16:at + 16 + len(payload)] = payload
    for i in range(len(payload), room):                 # scrub the old tail
        d[at + 16 + i] = 0
    # the font header's own bookkeeping: the engine sizes a decode buffer from max packed
    off = struct.unpack_from('<I', d, 8 + font * 12)[0]
    if len(payload) > struct.unpack_from('<I', d, off + 0x150)[0]:
        struct.pack_into('<I', d, off + 0x150, len(payload))
    tot = struct.unpack_from('<I', d, off + 0x158)[0]
    struct.pack_into('<I', d, off + 0x158, tot - old + len(payload))
    io.open(path, 'wb').write(bytes(d))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glyph', type=lambda s: int(s, 0), default=GLYPH)
    ap.add_argument('--model', default=MODEL_XML)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--preview', default=os.path.join(os.environ.get('TEMP', '.'),
                                                      'weapon_glyph.png'))
    a = ap.parse_args()

    if a.restore:
        import shutil
        for name in PACKAGES:
            src = os.path.join(BACKUP, name)
            if not os.path.exists(src):
                raise SystemExit('no backup at %s' % src)
            shutil.copyfile(src, os.path.join(fp.FONTS, name))
            print('restored %s' % name)
        return

    print('reading %s' % os.path.basename(a.model))
    V, idx = mesh(a.model)
    xs = [v[0] for v in V]
    zs = [v[2] for v in V]
    print('   %d vertices, %d strip indices' % (len(V), len(idx)))
    print('   side view %.3f x %.3f world units, %.2f m long'
          % (max(xs) - min(xs), max(zs) - min(zs), (max(xs) - min(xs)) * 3.048))

    from PIL import Image
    shots = []
    for name in PACKAGES:
        path = os.path.join(fp.FONTS, name)
        d = io.open(path, 'rb').read()
        g = fp.glyphs(d)
        if a.glyph not in g:
            raise SystemExit('%s has no %04X' % (name, a.glyph))
        font, w, h, old, at = g[a.glyph]
        px = stylise(silhouette(V, idx, w, h))
        pay = fc.encode(px)
        if fc.decode(pay, w, h) != px:
            raise SystemExit('%s: the glyph does not survive its own codec' % name)
        room = slot_of(d, g, at)
        print('%-26s %04X %3dx%-3d  was %5d b, now %5d b, slot %5d  %s'
              % (name, a.glyph, w, h, old, len(pay), room,
                 'fits' if len(pay) <= room else 'TOO BIG'))
        im = Image.new('RGBA', (w, h))
        im.putdata([(r * 17, gg * 17, b * 17, al * 17) for al, r, gg, b in px])
        shots.append(im)
        if a.write:
            splice(path, a.glyph, pay)

    sheet = Image.new('RGBA', (max(s.width for s in shots),
                               sum(s.height + 6 for s in shots)), (20, 22, 26, 255))
    y = 0
    for s in shots:
        sheet.alpha_composite(s, (0, y))
        y += s.height + 6
    sheet.save(a.preview)
    print('\npreview -> %s' % a.preview)
    print('written into the LIVE packages; no map rebuild needed' if a.write
          else '(dry run -- pass --write)')


if __name__ == '__main__':
    main()
