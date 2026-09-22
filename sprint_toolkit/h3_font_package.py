r"""Read Halo 3's icon font package, so a ported weapon's pickup icon can be chosen.

Halo 3 stores a weapon's pickup symbol as a Unicode Private Use codepoint in the WEAPON
tag (`Private Use Font Icon`), rendered from maps\fonts\font_package_icon.bin. Pointing a
port at a free codepoint is one field -- but only if a glyph is actually THERE, and a
blank one is a silent regression. This reads the package and says which codepoints the
font draws.

Format, as far as it is needed here:
  0x00  u32 magic 0xC0000004, u32 font count, then (u32 offset, u32 size, u32 id) triples
  each font header is 0x168 bytes, laid end to end from the first triple's offset:
    +0x04 name (e.g. "icon\fixedsys-hud"), +0x138 highest codepoint, +0x13c glyph count
  the character map is a set of TABLES of 8-byte entries -- u16 codepoint, u16 font index,
  u32 glyph data offset -- scattered through the file rather than one sorted array, which
  is why a single sorted-run search misses most of them.

    python h3_font_package.py                  # what the package contains
    python h3_font_package.py --free           # codepoints no Halo 3 tag claims
"""
import argparse, io, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MCC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(os.path.dirname(MCC), 'halo3', 'maps', 'fonts')
PKG = 'font_package_icon.bin'
ENTRY = 8


def fonts_in(d):
    """(name, glyph count, highest codepoint) per font in the package header."""
    magic, count = struct.unpack_from('<II', d, 0)
    out = []
    for i in range(count):
        off = struct.unpack_from('<I', d, 8 + i * 12)[0]
        name = d[off + 4:off + 0x24].split(b'\0')[0].decode('latin1', 'replace')
        top, n = struct.unpack_from('<II', d, off + 0x138)
        out.append((name, n, top))
    return magic, out


def _plausible(cp, font, off, size):
    # Codepoints are Basic Latin or Private Use; the font index is one of the handful the
    # package declares; the offset is inside the glyph data. Pixel data satisfies a loose
    # test for long stretches, which is what makes a tight one worth having.
    return ((0x20 <= cp < 0x3000 or 0xE000 <= cp < 0xF000)
            and font < 8 and 0 < off < size)


def tables(d, min_entries=8):
    """Every run of plausible 8-byte character-map entries, as (start, [(cp, font, off)]).

    Linear: each byte is examined once. A run is never rescanned from a later start, and
    is capped, because a naive scan is quadratic -- the glyph bitmaps pass a loose entry
    test for thousands of bytes at a time.
    """
    found, at, scanned, cap = [], 0, 0, 8192
    size = len(d)
    while at + ENTRY <= size:
        if at < scanned:
            at += 4
            continue
        cp, font, off = struct.unpack_from('<HHI', d, at)
        if not _plausible(cp, font, off, size):
            at += 4
            continue
        run, a = [], at
        while a + ENTRY <= size and len(run) < cap:
            cp, font, off = struct.unpack_from('<HHI', d, a)
            if not _plausible(cp, font, off, size):
                break
            run.append((cp, font, off))
            a += ENTRY
        scanned = a
        if len(run) >= min_entries:
            found.append((at, run))
        at += 4
    return found


def charmap(d):
    """{codepoint: (font index, glyph offset)} across every table."""
    out = {}
    for _start, run in tables(d):
        for cp, font, off in run:
            out.setdefault(cp, (font, off))
    return out


def blocks(d, step=0xC000):
    """The character-map blocks. Each is `step`-aligned and holds a small header
    (marker, entry count, where the glyph data starts, total size), then the table,
    then the glyph payloads -- offsets in the table are relative to the BLOCK."""
    out = []
    for base in range(0, len(d), step):
        if base + 8 > len(d):
            break
        mark, n, first, total = struct.unpack_from('<4H', d, base)
        if mark == 8 and 0 < n < 4096 and first == 8 + n * ENTRY:
            out.append((base, n, first, total))
    return out


def glyphs(d):
    """{codepoint: (font, width, height, payload size, absolute offset)}.

    A glyph is a 16-byte header -- u32, u32 payload size, u16 width, u16 height,
    u16 x, u16 y -- then the payload, padded to a 16-byte boundary. The payload's
    encoding is NOT decoded here: it is a custom codec, not zlib/bz2/lzma, and its
    size runs from a fifth of a byte per pixel to well over four, so it is neither a
    plain raster nor a simple run length. The DIMENSIONS are what this is for --
    they separate a wide weapon silhouette from a small square marker.
    """
    out = {}
    for base, n, _first, _total in blocks(d):
        for i in range(n):
            cp, font, off = struct.unpack_from('<HHI', d, base + 8 + i * ENTRY)
            a = base + off
            if a + 16 > len(d):
                continue
            _f0, size, w, h, _x, _y = struct.unpack_from('<IIHHHH', d, a)
            if w and h and size and cp not in out:
                out[cp] = (font, w, h, size, a)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', default=PKG)
    ap.add_argument('--free', action='store_true',
                    help='cross-check against what the Halo 3 campaign claims')
    a = ap.parse_args()

    path = os.path.join(FONTS, a.package)
    if not os.path.exists(path):
        raise SystemExit('no %s' % path)
    d = io.open(path, 'rb').read()
    magic, fl = fonts_in(d)
    print('%s  %d bytes  magic %#x' % (a.package, len(d), magic))
    for name, n, top in fl:
        print('   %-24s %4d glyphs, highest %#06x' % (name, n, top))

    tabs = tables(d)
    cm = charmap(d)
    print('\n%d table(s), %d distinct codepoints' % (len(tabs), len(cm)))
    for start, run in tabs:
        cps = [c for c, _f, _o in run]
        print('   @%#08x %3d entries  %#06x..%#06x' % (start, len(run), min(cps), max(cps)))

    pua = sorted(c for c in cm if 0xE000 <= c < 0xE200)
    print('\n%d private-use codepoints with a glyph:' % len(pua))
    for i in range(0, len(pua), 12):
        print('   ' + ' '.join('%04x' % c for c in pua[i:i + 12]))

    if not a.free:
        return

    # Which unclaimed glyph could carry a ported weapon. Halo 3's weapon icons are WIDE
    # silhouettes, ~93..156 across; the small squares in the same block are markers
    # (a bomb, a flag) and would look wrong on a rifle. ODST claims three that Halo 3
    # does not, which is how 0xE145 turns out to be the golf club rather than a spare.
    g = glyphs(d)
    claimed = {
        0xE115: 'assault bomb (ODST)', 0xE11C: 'flag (ODST)',
        0xE145: 'golf club (ODST)',
    }
    h3_used = set(range(0xE112, 0xE133)) | set(range(0xE146, 0xE151))
    h3_used -= {0xE115, 0xE118, 0xE11B, 0xE11C, 0xE11E, 0xE121, 0xE127, 0xE128}
    print('\nunclaimed glyphs, widest first -- a weapon needs a weapon-shaped one:')
    free = [(cp, g[cp]) for cp in sorted(g)
            if 0xE112 <= cp <= 0xE151 and cp not in h3_used]
    for cp, (_font, w, h, size, at) in sorted(free, key=lambda r: -r[1][1]):
        note = claimed.get(cp, '')
        shape = 'weapon-shaped' if w >= 60 else 'small square, a marker not a weapon'
        print('   %#06x  %3dx%-3d %5db  %-36s %s' % (cp, w, h, size, shape, note))


if __name__ == '__main__':
    main()
