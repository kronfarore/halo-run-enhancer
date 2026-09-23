r"""Read a Halo 2 font file. The container is decoded; the pixels are not, quite.

Halo 2 keeps one font per file in `halo2\h2_fonts\`, with no package around them -- the
opposite of Halo 3, where `font_package_icon.bin` holds four fonts and their character
maps together. This is what a Halo 2 port needs before it can own a pickup icon the way
the Halo 3 one now does (`h3_font_add.py`).

LAYOUT, the same in all twenty of them:

    0x000   512 bytes of zeroes
    0x200   header: magic 0xF0000001, then +0x0C glyph count, +0x20 kerning pair count
    0x224   the kerning table, 4 bytes each: char, char, signed 16-bit delta
    0x400   THE CHARACTER MAP: one u32 per codepoint, indexed by the codepoint itself,
            0x10000 of them. The value is a glyph index; the one that FILLS the map
            means "nothing here" and is per font -- 314 in conduit-12, 268 in MSLCD-14
    0x40400 the glyph table, 16 bytes each:
            u16 advance, u16 payload size, u16 width, u16 height, u16 x, u16 y,
            u32 absolute file offset of the payload
    then    the payloads, in index order

A codepoint-indexed map is a quarter of a megabyte of mostly nothing, which is why the
file opens with a long stretch of one repeated value and why none of this was obvious. It
also makes adding an icon far EASIER than in Halo 3: there is no table to insert into and
no offsets to shift, because every codepoint already has its slot -- pointing one at a new
glyph is a single u32.

**What is NOT settled: how the pixels are laid out.** Four things about the payload are
now certain, and they rule out the obvious answers:

* the format is ARGB4444 as in Halo 3 -- rendering the R, G and B channels of any glyph
  gives solid white and the ALPHA carries the shape, exactly as the Halo 3 icons do;
* the opcode pixel COUNTS are Halo 3's. Sweeping the alternatives (a literal worth two
  pixels, a single worth two, a pair worth one or three) against all 416 glyphs, Halo 3's
  own reading is the only one with ZERO overflows and it gives 409 of them a sane count;
* the space glyph decodes exactly: 1x38, one opcode 0x26, 38 transparent pixels, nothing
  left over;
* so the glyph table's width and height are right too.

And yet no row length produces a legible letter. Strides from 11 to 24 were rendered for
H, A and M and none of them reads; autocorrelating the stream peaks four or five pixels
BELOW the declared width for every icon and never settles. Counts right, format right,
size right, order wrong -- so the question is not the stride at all. The pixels are not
laid down as a plain left-to-right raster, and what they are laid down as is the next
thing to find.

Nothing here writes a payload. A font is not a thing to guess at: it draws every word in
the game.

    python h2_font.py <font>                 the header, the map and the glyph table
    python h2_font.py <font> --render <out.png> --cp 0xE112 0xE113
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h3_font_codec as fc

B = os.sep
MCC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(os.path.dirname(MCC), 'halo2', 'h2_fonts')

MAGIC = 0xF0000001
HEADER = 0x200
CHARMAP = 0x400
CODEPOINTS = 0x10000
GLYPHS = CHARMAP + CODEPOINTS * 4       # 0x40400
RECORD = 16


def header(d):
    """(glyph count, kerning pairs) -- and it checks the magic before believing either."""
    if struct.unpack_from('<I', d, HEADER)[0] != MAGIC:
        raise ValueError('no 0xF0000001 at 0x200; this is not a Halo 2 font')
    return (struct.unpack_from('<I', d, HEADER + 0x0C)[0],
            struct.unpack_from('<I', d, HEADER + 0x20)[0])


def blank(d):
    """The glyph index that means "nothing here".

    It is NOT a constant. conduit-12 fills its map with 314 and MSLCD-14 with something
    else -- each font points its unmapped codepoints at its own notdef glyph. So it is
    read off the map as the value that fills it, which for a font of a few hundred glyphs
    is tens of thousands of slots and unmistakable.
    """
    counts = {}
    for cp in range(0, CODEPOINTS, 7):          # a seventh of them settles it
        at = CHARMAP + cp * 4
        if at + 4 > len(d):
            break
        v = struct.unpack_from('<I', d, at)[0]
        counts[v] = counts.get(v, 0) + 1
    return max(counts, key=counts.get) if counts else None


def glyph_of(d, cp, none=None):
    """The glyph index a codepoint draws, or None when it draws nothing."""
    at = CHARMAP + cp * 4
    if at + 4 > len(d):
        return None
    i = struct.unpack_from('<I', d, at)[0]
    return None if i == (blank(d) if none is None else none) else i


def record(d, index):
    """(advance, payload size, width, height, x, y, payload offset)."""
    return struct.unpack_from('<6HI', d, GLYPHS + index * RECORD)


def payload(d, index):
    r = record(d, index)
    return d[r[6]:r[6] + r[1]]


def mapped(d):
    """{codepoint: glyph index} for everything the font actually draws."""
    none = blank(d)
    out = {}
    for cp in range(CODEPOINTS):
        i = glyph_of(d, cp, none)
        if i is not None:
            out[cp] = i
    return out


def report(path):
    d = open(path, 'rb').read()
    count, kerns = header(d)
    cm = mapped(d)
    icons = sorted(cp for cp in cm if 0xE000 <= cp < 0xF000)
    print('%-26s %8d bytes  %5d glyphs  %4d kerning pairs  %5d codepoints mapped'
          '  (blank = %s)'
          % (os.path.basename(path), len(d), count, kerns, len(cm), blank(d)))
    if icons:
        print('   private use: 0x%04X..0x%04X (%d of them)'
              % (icons[0], icons[-1], len(icons)))
        free = [cp for cp in range(icons[0], icons[-1] + 0x20) if cp not in cm]
        print('   free in that range: %s%s'
              % (' '.join('%04X' % c for c in free[:12]), ' ...' if len(free) > 12 else ''))
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('font', nargs='?', default=os.path.join(FONTS, 'conduit-12'))
    ap.add_argument('--all', action='store_true', help='every font in the folder')
    ap.add_argument('--cp', nargs='*', type=lambda s: int(s, 0),
                    default=[0x41, 0xE112, 0xE113])
    ap.add_argument('--render')
    a = ap.parse_args()

    if a.all:
        for name in sorted(os.listdir(FONTS)):
            path = os.path.join(FONTS, name)
            if name.endswith('.txt') or not os.path.isfile(path):
                continue
            try:
                report(path)
            except ValueError as exc:
                print('%-26s %s' % (name, exc))
        return

    d = report(a.font)
    for cp in a.cp:
        i = glyph_of(d, cp)
        if i is None:
            print('   cp 0x%04X  nothing' % cp)
            continue
        adv, size, w, h, x, y = record(d, i)[:6]
        print('   cp 0x%04X  glyph %4d  advance %3d  %3dx%-3d at %d,%d  %5d bytes'
              % (cp, i, adv, w, h, x, y, size))

    if a.render:
        from PIL import Image
        tiles = []
        for cp in a.cp:
            i = glyph_of(d, cp)
            if i is None:
                continue
            _adv, _size, w, h = record(d, i)[:4]
            px = fc.decode(payload(d, i), w, h)
            im = Image.new('RGBA', (w, h))
            im.putdata([(r * 17, g * 17, b * 17, al * 17) for al, r, g, b in px])
            tiles.append(im)
        if tiles:
            W = sum(t.width + 4 for t in tiles)
            H = max(t.height for t in tiles)
            sheet = Image.new('RGBA', (W, H), (18, 18, 22, 255))
            at = 0
            for t in tiles:
                sheet.alpha_composite(t, (at, 0))
                at += t.width + 4
            sheet.save(a.render)
            print('   %s  -- SHEARED: the stride is not the declared width' % a.render)


if __name__ == '__main__':
    main()
