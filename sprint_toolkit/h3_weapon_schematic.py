r"""Draw a ported weapon's HUD schematic from its own geometry, into `weapon_scematics`.

The schematic is the line drawing beside the ammo counter. A port cloned from the
Assault Rifle points at the Assault Rifle's, so the SAW was drawing an AR while holding
a SAW, and no field on the port fixes that -- the picture has to exist first.

It comes from the same place as the pickup glyph: an orthographic side view of the
port's real render model (see `h3_weapon_glyph`, which explains the compressed positions,
the paired bounds and the triangle strip). Two differences:

  * the schematics face the OTHER WAY. Every shipped one points muzzle LEFT, while the
    font icons point muzzle right, so this mirrors the render and the glyph does not.
  * the art is pure white and carries everything in ALPHA -- 0 background, about 56 for
    the body, 205 for the outline. That is the Assault Rifle's own palette, measured.

WHICH SPRITE. All 26 sequences are referenced by some chud, so there is no free slot;
#24 is the silenced SMG and #25 the automag, both ODST weapons that never appear in the
Halo 3 campaign. #25 is taken because the pickup prompt already hijacked `am_pickup` and
`am_swap`, so every consequence of this port lands on the automag and nowhere else.

WHY THE PIXELS ARE WRITTEN AS DXT5. Unlike `ballistic_meters`, which stores a8r8g8b8 and
can be patched byte for byte, this bitmap is compressed, and `tool export-bitmap-tga`
refuses to decompress it. So the blocks are decoded and re-encoded here. That is cheap
and exact for this art: the colour endpoints are white everywhere, so only the alpha
block carries shape, and its eight interpolated levels are more than the drawing needs.
The sprite is 4-aligned in both axes, so only its own blocks are touched.

The blob is base (1024x512) plus exactly ONE mip (512x256) -- 524288 + 131072 = 655360,
which is the whole blob -- and both are rewritten.

    python h3_weapon_schematic.py                   # render and report, touching nothing
    python h3_weapon_schematic.py --write
"""
import argparse, io, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402
import h3_weapon_glyph as wg                                    # noqa: E402
import h3_meter_art as ma                                       # noqa: E402

B = os.sep
BITMAP = os.path.join(wg.EK, 'tags', 'ui', 'chud', 'bitmaps',
                      'weapon_scematics.bitmap')
W, H = 1024, 512
BASE = W * H                       # DXT5 is one byte per pixel
SPRITE = 25                        # the automag's, an ODST weapon
FILL, EDGE = 56, 205               # measured off the Assault Rifle's schematic


def pixels(tag):
    n = max((x for x in tag.nodes() if x.marker == 'tgda'), key=lambda x: x.length)
    return n.payload_at, n.length


def decode_block(d, o):
    a0, a1 = d[o], d[o + 1]
    bits = int.from_bytes(bytes(d[o + 2:o + 8]), 'little')
    A = [a0, a1]
    if a0 > a1:
        A += [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)]
    else:
        A += [((5 - k) * a0 + k * a1) // 5 for k in range(1, 5)] + [0, 255]
    return [A[(bits >> (3 * k)) & 7] for k in range(16)]


def encode_block(d, o, alphas):
    """White colour endpoints, shape in the alpha block."""
    a0, a1 = max(alphas), min(alphas)
    if a0 == a1:                                  # a flat block still needs a0 > a1
        a1 = max(0, a0 - 1)
    A = [a0, a1] + [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)]
    bits = 0
    for k, v in enumerate(alphas):
        best = min(range(8), key=lambda i: abs(A[i] - v))
        bits |= best << (3 * k)
    d[o] = a0
    d[o + 1] = a1
    d[o + 2:o + 8] = bits.to_bytes(6, 'little')
    struct.pack_into('<HH', d, o + 8, 0xFFFF, 0x0000)     # white, white-ish
    struct.pack_into('<I', d, o + 12, 0)                  # every texel = endpoint 0


def draw(d, at, w, span, x0, y0, sw, sh, alphas):
    """Write `alphas` (sw*sh, row major) into a DXT5 surface of width `w`."""
    for by in range(sh // 4):
        for bx in range(sw // 4):
            o = at + span + (((y0 // 4 + by) * (w // 4)) + (x0 // 4 + bx)) * 16
            blk = [alphas[(by * 4 + k // 4) * sw + (bx * 4 + k % 4)] for k in range(16)]
            encode_block(d, o, blk)


def art(V, idx, sw, sh):
    """Mirrored side view in the shipped palette: white, shape in alpha."""
    from PIL import ImageFilter, ImageOps
    # the same gap closing the pickup glyph gets, so the two stay one drawing
    cov = wg.close_gaps(ImageOps.mirror(wg.silhouette(V, idx, sw, sh, margin=3)), 3)
    solid = cov.point(lambda v: 255 if v > 128 else 0)
    inner = solid.filter(ImageFilter.MinFilter(3))
    c, s, e = cov.load(), solid.load(), inner.load()
    out = []
    for y in range(sh):
        for x in range(sw):
            if s[x, y]:
                out.append(FILL if e[x, y] else EDGE)
            else:
                out.append(int(round(EDGE * c[x, y] / 255.0)))
    return out


def downsample(alphas, w, h):
    """The mip, as a 2x2 box filter of the base -- never re-rendered.

    Rendering the half-size image separately looks equivalent and is not: the inset is a
    fixed number of PIXELS, so at half resolution it eats twice the proportion and the
    art comes out 90% of the width it has in the base, shifted inward about 4.5% on each
    side. A weapon chud has TWO schematic widgets, and if one samples the base while the
    other samples the mip, that shows up in game as two copies of the weapon slightly
    offset from one another. Deriving the mip from the base makes them register by
    construction.
    """
    out = []
    for y in range(h // 2):
        for x in range(w // 2):
            out.append((alphas[(y * 2) * w + x * 2] + alphas[(y * 2) * w + x * 2 + 1]
                        + alphas[(y * 2 + 1) * w + x * 2]
                        + alphas[(y * 2 + 1) * w + x * 2 + 1]) // 4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sprite', type=int, default=SPRITE)
    ap.add_argument('--model', default=wg.MODEL_XML)
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--xml', default=os.path.join(os.environ.get('TEMP', '.'),
                                                  'bm_schem.xml'))
    ap.add_argument('--preview', default=os.path.join(os.environ.get('TEMP', '.'),
                                                      'weapon_schematic.png'))
    a = ap.parse_args()
    if not os.path.exists(a.xml):
        raise SystemExit('need the bitmap xml: tool export-tag-to-xml ... %s' % a.xml)

    tag = h3tag.Tag(BITMAP)
    ok, cov, tot = tag.check()
    print('weapon_scematics parses: %s (%d/%d)' % (ok, cov, tot))
    at, blob = pixels(tag)
    print('blob %d bytes = base %d + one mip %d' % (blob, BASE, blob - BASE))

    x0, x1, y0, y1 = ma.sprite_bounds(a.xml, a.sprite)
    sw, sh = x1 - x0, y1 - y0
    print('sprite #%d at %d,%d  %dx%d  (4-aligned: %s)'
          % (a.sprite, x0, y0, sw, sh,
             all(v % 4 == 0 for v in (x0, y0, sw, sh))))
    if not all(v % 4 == 0 for v in (x0, y0, sw, sh)):
        raise SystemExit('sprite is not block aligned; neighbours would be damaged')

    V, idx = wg.mesh(a.model)
    print('   %d vertices, %d strip indices' % (len(V), len(idx)))
    full = art(V, idx, sw, sh)
    half = downsample(full, sw, sh)

    from PIL import Image
    im = Image.new('RGBA', (sw, sh))
    im.putdata([(255, 255, 255, v) for v in full])
    bg = Image.new('RGBA', (sw, sh), (20, 22, 26, 255))
    bg.alpha_composite(im)
    bg.resize((sw * 2, sh * 2), Image.NEAREST).save(a.preview)
    print('preview -> %s' % a.preview)

    if not a.write:
        print('\n(dry run -- pass --write)')
        return

    draw(tag.data, at, W, 0, x0, y0, sw, sh, full)
    draw(tag.data, at, W // 2, BASE, x0 // 2, y0 // 2, sw // 2, sh // 2, half)
    ok, cov, tot = tag.check()
    print('after: parses %s (%d/%d)' % (ok, cov, tot))
    if not ok:
        raise SystemExit('not saved')
    tag.save(BITMAP)
    print('wrote %s' % BITMAP)


if __name__ == '__main__':
    main()
