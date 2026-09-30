r"""SUPERSEDED (2026-09-30) by h3_font_repack.py -- this never updated the block index,
the fonts' block ranges or the block count at +0x414. Kept for the record; do not use.

Put a glyph in an EXISTING block that has room, instead of appending a new one.

THE EXPERIMENT THIS IS FOR. `h3_font_grow.py` appends a block, and the first in-game test
of that said something useful and incomplete: Reach's text and every stock icon were
undisturbed, so a grown package does not BREAK anything -- but the port's own new glyph
did not draw either. The obvious suspect is that the engine reads a fixed number of
blocks and simply never looks at the appended one.

That is one experiment away from certain, and the experiment needs no map rebuild,
because the font packages are loose files the game reads at startup.

    put the SAME codepoint in an EXISTING block that has room
      -> if it draws, the engine ignores appended blocks, and REPACKING is the answer
         (bounded: Halo 3 8, ODST 22, Reach 12 more icons)
      -> if it still does not draw, the block is not the problem and the fault is in the
         glyph record or the message, not the package's shape

WHY A LATER BLOCK IS LEGAL. A font is one ascending list read across the blocks in file
order, so a codepoint above everything the font already draws can live in ANY block that
comes after the font's last run -- including one that currently holds only another font.
Reach's x1 block 4 holds only font 5 and has 24,208 bytes free; x2's last block has 5,504;
x3's has 10,680. All three sit after font 3's final run, so the order still reads.

    python h3_font_place.py --cp 0xE150 --font 3 --report
    python h3_font_place.py --cp 0xE150 --font 3 --write
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


def last_run_block(d, font):
    """The base of the last block this font has any entry in."""
    last = None
    for base, count, table, _doff, _dsz in fp.blocks_of(d):
        for k in range(count):
            _cp, fo, _off = struct.unpack_from('<HHI', d, base + table + k * ENTRY)
            if fo == font:
                last = base
                break
    return last


def candidates(d, font, need):
    """Blocks that come at or after the font's last run and have room for `need`."""
    start = last_run_block(d, font)
    out = []
    for base, _count, _table, doff, dsz in fp.blocks_of(d):
        if start is not None and base < start:
            continue
        free = fp.BLOCK - (doff + dsz)
        if free >= need:
            out.append((base, free))
    return out


def place(data, cp, font, payload, box, base=None, advance=None):
    """`data` with the glyph inserted at the END of block `base`'s table."""
    d = bytearray(data)
    if cp in fp.glyphs(bytes(d)):
        raise SystemExit('0x%04X already has a glyph' % cp)
    w, h = box
    record = bytearray(struct.pack('<IIHHHH', advance if advance is not None else w,
                                   len(payload), w, h, 0, 0))
    record += payload
    record += b'\0' * (-len(record) % 16)
    need = len(record) + ENTRY

    if base is None:
        opts = candidates(bytes(d), font, need)
        if not opts:
            raise SystemExit('no existing block at or after font %d\'s last run has %d '
                             'bytes free' % (font, need))
        base = opts[0][0]

    blocks = {b[0]: b for b in fp.blocks_of(bytes(d))}
    if base not in blocks:
        raise SystemExit('%#x is not a block' % base)
    _b, count, table, data_off, data_size = blocks[base]
    if fp.BLOCK - (data_off + data_size) < need:
        raise SystemExit('block %#x has %d bytes free and needs %d'
                         % (base, fp.BLOCK - (data_off + data_size), need))

    entries = [list(struct.unpack_from('<HHI', d, base + table + k * ENTRY))
               for k in range(count)]
    for e in entries:
        e[2] += ENTRY                        # the data moved along by one entry
    entries.append([cp, font, data_off + ENTRY + data_size])

    block = bytearray(fp.BLOCK)
    struct.pack_into('<II', block, 0,
                     ((count + 1) << 16) | table,
                     ((data_size + len(record)) << 16) | (data_off + ENTRY))
    for k, e in enumerate(entries):
        struct.pack_into('<HHI', block, table + k * ENTRY, *e)
    old = bytes(d[base + data_off:base + data_off + data_size])
    at = data_off + ENTRY
    block[at:at + len(old)] = old
    block[at + len(old):at + len(old) + len(record)] = record
    d[base:base + fp.BLOCK] = block

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
    if len(out) != len(data):
        raise SystemExit('the file changed size; this is meant to fit in place')
    if not fa.ordered(out, font):
        raise SystemExit('font %d no longer reads as one ascending list; refusing' % font)
    if cp not in fp.glyphs(out):
        raise SystemExit('the glyph is not readable back out; refusing')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--font', type=int, default=None)
    ap.add_argument('--need', type=int, default=734)
    a = ap.parse_args()
    import h3_kit
    font = a.font if a.font is not None else h3_kit.HUD_FONT
    for name in ('font_package_icon.bin', 'font_package_icon_x2.bin',
                 'font_package_icon_x3.bin'):
        p = os.path.join(fp.FONTS, name)
        if not os.path.exists(p):
            continue
        d = open(p, 'rb').read()
        need = a.need * (1 if '_x' not in name else int(name.split('_x')[1][0]) ** 2) + 8
        print('%-28s last font-%d block %s, usable later blocks: %s'
              % (name, font,
                 '%#x' % (last_run_block(d, font) or 0),
                 ['%#x(%d free)' % c for c in candidates(d, font, need)] or 'NONE'))


if __name__ == '__main__':
    main()
