r"""Move or resize one sprite's box inside a Halo 3 / ODST HUD sheet.

WHY A PORT NEEDS THIS. Both sheets a ported weapon draws from -- `ballistic_meters` for
the ammo ticks and `weapon_scematics` for the picture beside the counter -- are fixed
grids of sequences, and a port needs one that nothing else uses. Halo 3 had room: three
of its twenty meter sprites are unreferenced, and one of them is a full three-row box.

**ODST has almost none.** Its `ballistic_meters` has eighteen sequences and exactly ONE
free (#1, and only 307x62, a two-row box); its `weapon_scematics` has twenty-seven and
its three spare ones are 8x8 STUBS. Halo 3's port solved the schematic by taking the
automag's, which is safe there because the automag never appears in Halo 3 -- in ODST it
is a live weapon and that trick is gone.

THE WAY OUT IS THE SHEET ITSELF. Both are 1024x512 and both stop using canvas around
y=400: measured, every row from 400 down is entirely blank in `ballistic_meters`, and
`weapon_scematics` ends its last row of art at y=406. No sequence covers any of it. So a
spare sequence can simply be given a REAL box down there, and the art drawn into it --
no new sequence, no block growth, and nothing taken away from a weapon that is using it.

A sprite's box is six floats (left, right, top, bottom, then a registration point), so
this is an in-place overwrite: no chunk changes length. The record is found by its
EXACT current values, which must occur exactly once -- the same discipline
h3_saw_tag_numbers.py uses, and for the same reason.

    python h3_sprite_box.py --bitmap ballistic_meters --sprite 1
    PORT_EK=odst python h3_sprite_box.py --bitmap ballistic_meters --sprite 1 \
        --box 0,307,410,491 --like 10 --write
"""
import argparse
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                    # noqa: E402
import h3_kit                                                   # noqa: E402

B = os.sep
W, H = 1024, 512
BITMAPS = os.path.join(h3_kit.TAGS, 'ui', 'chud', 'bitmaps')


def sprites(xml):
    """[(left, right, top, bottom, reg x, reg y)] per sequence, as the XML reports."""
    s = open(xml, encoding='utf-8', errors='replace').read()
    seg = s[s.find('<block name="sequences"'):]
    out, parts = [], re.split(r'<element index="(\d+)" name="[^"]*">', seg)
    for k in range(1, len(parts) - 1, 2):
        b = parts[k + 1]
        g = lambda n: (re.search(r'name="%s" value="(-?[\d.]+)"' % n, b) or [None, None])[1]
        if g('left') is None:
            continue
        reg = re.search(r'name="registration point" value="(-?[\d.]+),(-?[\d.]+)"', b)
        out.append(tuple(float(g(n)) for n in ('left', 'right', 'top', 'bottom'))
                   + ((float(reg.group(1)), float(reg.group(2))) if reg else (0.0, 0.0)))
    return out


def exact(box):
    """The four EDGES as the tag really stores them, rebuilt from the sheet's own grid.

    The XML rounds to six decimals, which is not what to search a tag for. But an edge is
    always a pixel count over the sheet size -- 308/1024, 262/512 -- and those are exact
    binary fractions, so multiplying back by the sheet size and dividing again recovers
    the stored float bit for bit.

    ONLY the edges. A REGISTRATION POINT can be a half pixel (weapon_scematics #10 reads
    0.004395, which is 4.5/1024), so reconstructing it this way is wrong and searching
    for it finds nothing -- which is exactly how the first attempt failed. The two
    registration floats are READ OUT of the tag instead, at the offset the edges land on.
    """
    return tuple(round(v * s) / float(s) for v, s in zip(box[:4], (W, W, H, H)))


def find(tag, box):
    """Offsets of the sprite record whose four edges are exactly `box`.

    NOTE THE RECORDS ARE NOT 4-ALIGNED: in `ballistic_meters` the first one starts at
    0x202b95. Stepping by four finds nothing at all, which is what the first attempt did.
    So the packed run is searched as bytes.

    It must be unique. Two sprites sharing a box would make the write ambiguous, and
    silently moving the wrong one is exactly the failure this guards against.
    """
    want = struct.pack('<4f', *exact(box))
    hits, at = [], tag.data.find(want)
    while at >= 0:
        hits.append(at)
        at = tag.data.find(want, at + 1)
    return hits


def registration(tag, box):
    """The two registration floats the tag stores for this sprite, read not rebuilt."""
    hits = find(tag, box)
    if len(hits) != 1:
        return None
    return struct.unpack_from('<2f', tag.data, hits[0] + 16)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bitmap', default='ballistic_meters')
    ap.add_argument('--sprite', type=int, required=True)
    ap.add_argument('--box', help='x0,x1,y0,y1 in PIXELS of the 1024x512 sheet')
    ap.add_argument('--like', type=int,
                    help="take the registration point's offsets from this sprite, so the "
                         "new box sits in the HUD the way a box of that size is meant to")
    ap.add_argument('--xml', help='tool export-tag-to-xml of the bitmap (required)')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    print(h3_kit.banner())

    xml = a.xml or os.path.join(os.environ.get('TEMP', '.'), a.bitmap + '_seq.xml')
    if not os.path.exists(xml):
        raise SystemExit('need the bitmap xml:\n   tool export-tag-to-xml '
                         '%s %s' % (os.path.join(BITMAPS, a.bitmap + '.bitmap'), xml))
    got = sprites(xml)
    cur = got[a.sprite]
    px = lambda b: (int(b[0] * W), int(b[1] * W), int(b[2] * H), int(b[3] * H))
    x0, x1, y0, y1 = px(cur)
    print('   #%d is %d,%d %dx%d  reg %.6f,%.6f'
          % (a.sprite, x0, y0, x1 - x0, y1 - y0, cur[4], cur[5]))

    p = os.path.join(BITMAPS, a.bitmap + '.bitmap')
    tag = h3tag.Tag(p)
    ok, cov, tot = tag.check()
    print('   %s parses %s (%d/%d)' % (a.bitmap, ok, cov, tot))
    hits = find(tag, cur)
    print('   sprite record: %s' % (', '.join('%#x' % h for h in hits) or 'NOT FOUND'))
    if len(hits) != 1:
        raise SystemExit('the box must occur exactly once in the tag; found %d' % len(hits))

    if not a.box:
        print('\n(no --box: nothing to change)')
        return
    nx0, nx1, ny0, ny1 = (int(v) for v in a.box.split(','))
    for other in range(len(got)):
        if other == a.sprite:
            continue
        ox0, ox1, oy0, oy1 = px(got[other])
        if nx0 < ox1 and ox0 < nx1 and ny0 < oy1 and oy0 < ny1:
            raise SystemExit('the new box overlaps sprite #%d (%d,%d %dx%d)'
                             % (other, ox0, oy0, ox1 - ox0, oy1 - oy0))
    if a.like is not None:
        ref = got[a.like]
        rx0, rx1, ry0, ry1 = px(ref)
        # read the reference's registration from the TAG, not from the rounded XML: at a
        # half pixel the XML's six decimals are not the stored value
        rreg = registration(tag, ref) or (ref[4], ref[5])
        reg = (rreg[0] * (nx1 - nx0) / float(rx1 - rx0),
               rreg[1] * (ny1 - ny0) / float(ry1 - ry0))
        print('   registration from #%d, scaled to the new size: %.6f,%.6f'
              % (a.like, reg[0], reg[1]))
    else:
        reg = registration(tag, cur) or (cur[4], cur[5])
    new = (nx0 / float(W), nx1 / float(W), ny0 / float(H), ny1 / float(H), reg[0], reg[1])
    print('   -> %d,%d %dx%d   (overlaps nothing)'
          % (nx0, ny0, nx1 - nx0, ny1 - ny0))

    if not a.write:
        print('\n(dry run -- pass --write)')
        return
    before = len(tag.data)
    struct.pack_into('<6f', tag.data, hits[0], *new)
    ok, cov, tot = tag.check()
    if len(tag.data) != before or not ok:
        raise SystemExit('not saved: size %d -> %d, parses %s'
                         % (before, len(tag.data), ok))
    tag.save(p)
    print('   wrote %s (unchanged size, still parses)' % os.path.basename(p))
    print('   RE-EXPORT the xml before drawing into it -- the art tools read bounds '
          'from there, not from the tag.')


if __name__ == '__main__':
    main()
