r"""Give a Halo 2 font a codepoint it did not have, so a port can own its pickup icon.

The Halo 3 side of this needed the glyph payload written by hand, because `tool
font-package` will only emit the icon names compiled into it. Halo 2 needs no such thing:
H2EK ships **`tool replace-font-char <font> <tiff> <utf16>`**, which rewrites a character's
bitmap from a TIFF, resizing the glyph and the file as it goes. Bungie's own encoder does
the pixels, so nothing here has to understand them -- which matters, because the SHIPPED
payloads do not decode with the Halo 3 codec even though that tool WRITES with it (see
`h2_font.py`). The 2004 data is in some older form; what the tool writes today is what the
engine reads today, and that is enough.

What the tool will not do is ADD a codepoint. An unmapped one resolves to the font's notdef
glyph, and `replace-font-char` then cheerfully replaces THAT -- one command and every
unmapped character in the game is a SAW. So the entry has to exist first, and that is this:

    append a 16-byte record to the glyph table, which pushes every payload along by 16,
    so every record's absolute payload offset moves with it;
    append a placeholder payload at the end of the file;
    point the codepoint's slot in the character map at the new index;
    bump the glyph count in the header.

Then `replace-font-char` fills it in. The character map being indexed by codepoint is what
makes this easy: there is no table to insert into and no order to keep, unlike Halo 3.

    python h2_font_add.py <font> --cp 0xE13D [--write]
    tool replace-font-char h2_fonts\<font> <tiff> 0xE13D
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h2_font as hf

#: a payload that draws nothing: one opcode, one transparent pixel
PLACEHOLDER = b'\x01'


def add(data, cp, box=(1, 1), advance=1):
    """`data` with `cp` mapped to a new, blank glyph at the end of the table."""
    count, _kerns = hf.header(data)
    if hf.glyph_of(data, cp) is not None:
        raise SystemExit('0x%04X already draws glyph %d' % (cp, hf.glyph_of(data, cp)))

    table_end = hf.GLYPHS + count * hf.RECORD
    first = struct.unpack_from('<I', data, hf.GLYPHS + 12)[0]
    if first != table_end:
        raise SystemExit('the payloads do not start where the table ends (0x%X vs 0x%X)'
                         % (first, table_end))

    out = bytearray(data[:table_end])
    w, h = box
    out += struct.pack('<6HI', advance, len(PLACEHOLDER), w, h, 0,
                       struct.unpack_from('<H', data, hf.GLYPHS + 10)[0],
                       len(data) + hf.RECORD)
    out += data[table_end:]
    out += PLACEHOLDER

    # every payload moved along by one record, so every offset does too
    for i in range(count):
        at = hf.GLYPHS + i * hf.RECORD + 12
        struct.pack_into('<I', out, at, struct.unpack_from('<I', out, at)[0] + hf.RECORD)

    struct.pack_into('<I', out, hf.CHARMAP + cp * 4, count)
    struct.pack_into('<I', out, hf.HEADER + 0x0C, count + 1)
    return bytes(out)


def verify(before, after, cp):
    """Nothing but the new codepoint may have changed where it points or what it draws."""
    count, _k = hf.header(before)
    none_b, none_a = hf.blank(before), hf.blank(after)
    if none_a != none_b:
        return 'the blank glyph changed, %s -> %s' % (none_b, none_a)
    if hf.glyph_of(after, cp) != count:
        return '0x%04X does not point at the new glyph' % cp
    for i in range(count):
        rb, ra = hf.record(before, i), hf.record(after, i)
        if rb[:6] != ra[:6]:
            return 'glyph %d changed shape' % i
        if hf.payload(before, i) != hf.payload(after, i):
            return 'glyph %d changed pixels' % i
    moved = [c for c in range(hf.CODEPOINTS)
             if c != cp and hf.glyph_of(before, c, none_b) != hf.glyph_of(after, c, none_a)]
    if moved:
        return '%d other codepoint(s) moved, e.g. 0x%04X' % (len(moved), moved[0])
    return ''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('font')
    ap.add_argument('--cp', type=lambda s: int(s, 0), required=True)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    before = open(a.font, 'rb').read()
    after = add(before, a.cp)
    count, _k = hf.header(before)
    problem = verify(before, after, a.cp)
    print('%-22s %d -> %d glyphs, %d -> %d bytes   %s'
          % (os.path.basename(a.font), count, count + 1, len(before), len(after),
             problem or 'nothing else moved'))
    if problem:
        raise SystemExit(1)
    if a.write:
        open(a.font, 'wb').write(after)
        print('   written; now run  tool replace-font-char  to fill it in')


if __name__ == '__main__':
    main()
