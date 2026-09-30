r"""SUPERSEDED (2026-09-30) by h3_font_repack.py -- this never updated the block index,
the fonts' block ranges or the block count at +0x414. Kept for the record; do not use.

Append a BLOCK to a font package, so a game can take more weapon icons than it ships
room for.

THE CEILING THIS EXISTS TO REMOVE. `glyph_capacity.py` measures how many more icons each
game can physically hold: Halo 3 four, ODST one, Reach one -- against 19, 23 and 22
weapons missing from those games. A package is a fixed-size file of 0xC000 blocks, each
font's glyphs are spread across them as ascending runs, and a new glyph can only use the
tail of the block its codepoint sorts into. Repacking and smaller art buy a dozen or so;
only growing the file removes the limit.

WHY THIS SHOULD WORK. The block count is stored NOWHERE. Every reader derives it by
walking the file in 0xC000 steps and accepting whatever validates as a block header
(marker 8, a plausible entry count, and a data offset that equals 8 + count * 8). The
shipped packages already range from four blocks to twenty-two, so the walk is the format,
not a fixed expectation. Appending one more block is therefore invisible to anything that
reads it correctly.

WHY IT STILL NEEDS A TEST IN GAME. Nothing here proves the ENGINE sizes it the same way.
It may hold the block count elsewhere, cap it, or map the file at a fixed length. That is
one boot to answer and cannot be answered from the bytes.

THE CODEPOINT MUST BE ABOVE THE FONT'S HIGHEST. A font's glyphs are ONE ascending list
read across the blocks in file order, so a block appended at the END can only carry
codepoints that sort after everything already there. `h3_font_add.ordered` checks it, and
this refuses rather than write a font that no longer reads in order.

    python h3_font_grow.py --report                  # what each package would take
    python h3_font_grow.py --cp 0xE150 --font 3 ...  # driven by h3_weapon_glyph
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_font_package as fp                                    # noqa: E402
import h3_font_add as fa                                        # noqa: E402

ENTRY = 8
MARK = 8


def block_count(d):
    return len(fp.blocks_of(d))


def highest(d, font):
    """The highest codepoint this font draws, across every block."""
    top = -1
    for base, count, table, _doff, _dsz in fp.blocks_of(d):
        for k in range(count):
            cp, fo, _off = struct.unpack_from('<HHI', d, base + table + k * ENTRY)
            if fo == font:
                top = max(top, cp)
    return top


def grow(data, cp, font, payload, box, advance=None):
    """`data` with a NEW BLOCK appended, carrying one glyph.

    Refuses unless `cp` sorts after everything the font already draws, because the block
    goes at the end of the file and a font is one ascending list across the blocks.
    """
    d = bytearray(data)
    if cp in fp.glyphs(bytes(d)):
        raise SystemExit('0x%04X already has a glyph' % cp)
    top = highest(bytes(d), font)
    if top < 0:
        raise SystemExit('font %d has no entries to append after' % font)
    if cp <= top:
        raise SystemExit(
            '0x%04X is not above font %d\'s highest, 0x%04X. A new block goes at the END '
            'of the\nfile, so it can only carry codepoints that sort after everything '
            'already there.' % (cp, font, top))

    w, h = box
    record = bytearray(struct.pack('<IIHHHH', advance if advance is not None else w,
                                   len(payload), w, h, 0, 0))
    record += payload
    record += b'\0' * (-len(record) % 16)
    data_off = 8 + ENTRY                    # header, then this block's single entry
    if data_off + len(record) > fp.BLOCK:
        raise SystemExit('the glyph is %d bytes and a block holds %d'
                         % (len(record), fp.BLOCK - data_off))

    block = bytearray(fp.BLOCK)
    struct.pack_into('<4H', block, 0, MARK, 1, data_off, len(record))
    struct.pack_into('<HHI', block, 8, cp, font, data_off)
    block[data_off:data_off + len(record)] = record
    d += block

    off = fa._font_header(bytes(d), font)
    struct.pack_into('<I', d, off + 0x13C,
                     struct.unpack_from('<I', d, off + 0x13C)[0] + 1)
    if cp + 1 > struct.unpack_from('<I', d, off + 0x138)[0]:
        struct.pack_into('<I', d, off + 0x138, cp + 1)
    if len(payload) > struct.unpack_from('<I', d, off + 0x150)[0]:
        struct.pack_into('<I', d, off + 0x150, len(payload))
    if w * h * 2 > struct.unpack_from('<I', d, off + 0x154)[0]:
        struct.pack_into('<I', d, off + 0x154, w * h * 2)
    for field, delta in ((0x144, len(record)), (0x158, len(payload))):
        struct.pack_into('<I', d, off + field,
                         struct.unpack_from('<I', d, off + field)[0] + delta)

    out = bytes(d)
    if len(fp.blocks_of(out)) != len(fp.blocks_of(bytes(data))) + 1:
        raise SystemExit('the appended block does not validate as one; refusing')
    if not fa.ordered(out, font):
        raise SystemExit('font %d no longer reads as one ascending list; refusing' % font)
    if cp not in fp.glyphs(out):
        raise SystemExit('the glyph is not readable back out of the new block; refusing')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--font', type=int, default=None)
    a = ap.parse_args()
    if not a.report:
        raise SystemExit('this is a library for h3_weapon_glyph; --report to inspect')
    import h3_kit
    for name in ('font_package_icon.bin', 'font_package_icon_x2.bin',
                 'font_package_icon_x3.bin'):
        p = os.path.join(fp.FONTS, name)
        if not os.path.exists(p):
            continue
        d = open(p, 'rb').read()
        font = a.font if a.font is not None else h3_kit.HUD_FONT
        print('%-28s %2d blocks, %d bytes, font %d highest 0x%04X'
              % (name, block_count(d), len(d), font, highest(d, font)))
    print('\nA grown package takes one more block per glyph: %d bytes each.' % fp.BLOCK)


if __name__ == '__main__':
    main()
