r"""Add a NEW codepoint to a Halo 3 font package, instead of overwriting somebody's.

This is the ceiling coming off the port pipeline. Until now a ported weapon took a
shipped icon's codepoint, which is fine exactly once -- the second port fights the first
over the same slot, and there are far more weapons to port than there are icons.

`tool font-package` cannot help: it assigns codepoints from a name table compiled into
tool.exe, alphabetical from 0xE112, and a tif named outside that table aborts the run. So
the package is written directly, which is possible because every part of it is bounded --
see `h3_font_package.py` for the block header and `--bounds` for the proof.

WHAT AN INSERT TOUCHES, all inside one 0xC000 block:

    the table grows by one 8-byte entry, so the glyph data after it shifts 8 bytes on,
    and EVERY offset in that block moves with it -- including the entries of other fonts
    whose glyphs live in the same block;
    the new payload goes on the end of the block's glyph data;
    the block header's two u32s take the new count and the new data offset and size;
    the font header takes its new glyph count, its highest codepoint, its running total
    and, if this glyph is the biggest so far, its decode buffer size.

**A font's entries must read as ONE ascending list across the whole package**, so the new
entry goes in its SORTED position, not merely after a run that happens to have room. That
distinction is not academic: putting 0xE151 after the run ending 0xE069 kept that run
ascending and broke the font, in two packages out of three, because a lookup that assumes
one sorted list stops finding things. `add` refuses to return a package where that no
longer holds.

If the block a codepoint sorts into has no room, the answer is a different CODEPOINT --
one that sorts somewhere roomier -- not a different place.

    python h3_font_add.py <package> --cp 0xE06A --font 2 --payload <glyph.bin> --box 155x44
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import h3_font_package as fp

ENTRY = 8
HEADER = 16                     # a glyph record: advance, size, w, h, x, y, then payload


def _font_header(d, font):
    return struct.unpack_from('<I', d, 8 + font * 12)[0]


def sequence(d, font):
    """Every entry of one font, in file order, as (codepoint, block, index in its table).

    A font's glyphs are spread over many blocks -- fixedsys-hud's over a dozen -- and the
    engine is entitled to assume they read as ONE ascending list. `ordered` is what proves
    it still does.
    """
    out = []
    for base, count, table, _data, _size in fp.blocks_of(d):
        at = 0
        for run in fp.runs_in(d, base, count, table):
            for k, e in enumerate(run):
                if e[1] == font:
                    out.append((e[0], base, at + k))
            at += len(run)
    return out


def ordered(d, font):
    """True when that font's codepoints ascend across the whole package."""
    cps = [c for c, _b, _i in sequence(d, font)]
    return all(a < b for a, b in zip(cps, cps[1:]))


def where(d, cp, font, need):
    """(block, index in its table) that keeps the font's ONE ascending list ascending.

    The first version of this appended after whichever run had room, which keeps that
    run ascending and quietly breaks the font. In the x2 package it put 0xE151 after the
    run ending 0xE069, so the font then read ... 0xE069, 0xE151, 0xE070 ... -- and a
    lookup that assumes one sorted list stops finding things. The x1 package was fine
    because 0xE151 went after the font's highest, so only two of the three broke, which
    is exactly the kind of half-failure that gets shipped.

    So the position is the SORTED one, and if the block it falls in has no room the
    answer is a different codepoint, not a different place.
    """
    seq = sequence(d, font)
    if not seq:
        raise SystemExit('font %d has no entries' % font)
    if any(c == cp for c, _b, _i in seq):
        raise SystemExit('font %d already draws 0x%04X' % (font, cp))
    before = [e for e in seq if e[0] < cp]
    if not before:
        raise SystemExit('0x%04X is below everything font %d draws' % (cp, font))
    _c, base, index = before[-1]
    free = next(fp.BLOCK - data - size
                for b, _count, _table, data, size in fp.blocks_of(d) if b == base)
    if free < need:
        raise SystemExit('0x%04X sorts into block 0x%06X, which has %d bytes free and '
                         'needs %d -- pick a codepoint that sorts somewhere roomier'
                         % (cp, base, free, need))
    return base, index + 1


def add(data, cp, font, payload, box, advance=None):
    """`data` with one more glyph in it. Raises rather than produce a broken package."""
    d = bytearray(data)
    if cp in fp.glyphs(bytes(d)):
        raise SystemExit('0x%04X already has a glyph' % cp)
    w, h = box
    record = bytearray(struct.pack('<IIHHHH', advance if advance is not None else w,
                                   len(payload), w, h, 0, 0))
    record += payload
    record += b'\0' * (-len(record) % 16)           # payloads sit on 16-byte boundaries

    base, index = where(bytes(d), cp, font, len(record) + ENTRY)
    blocks = {b[0]: b for b in fp.blocks_of(bytes(d))}
    _b, count, table, data_off, data_size = blocks[base]

    entries = [list(struct.unpack_from('<HHI', d, base + table + k * ENTRY))
               for k in range(count)]
    for e in entries:
        e[2] += ENTRY                               # the data moved along by one entry
    entries.insert(index, [cp, font, data_off + ENTRY + data_size])

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

    off = _font_header(bytes(d), font)
    struct.pack_into('<I', d, off + 0x13C,
                     struct.unpack_from('<I', d, off + 0x13C)[0] + 1)
    if cp + 1 > struct.unpack_from('<I', d, off + 0x138)[0]:
        struct.pack_into('<I', d, off + 0x138, cp + 1)
    if len(payload) > struct.unpack_from('<I', d, off + 0x150)[0]:
        struct.pack_into('<I', d, off + 0x150, len(payload))   # decode buffer
    if w * h * 2 > struct.unpack_from('<I', d, off + 0x154)[0]:
        struct.pack_into('<I', d, off + 0x154, w * h * 2)      # unpacked buffer
    for field, delta in ((0x144, len(record)), (0x158, len(payload))):
        struct.pack_into('<I', d, off + field,
                         struct.unpack_from('<I', d, off + field)[0] + delta)
    out = bytes(d)
    if not ordered(out, font):
        raise SystemExit('font %d no longer reads as one ascending list; refusing' % font)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('package')
    ap.add_argument('--cp', type=lambda s: int(s, 0), required=True)
    ap.add_argument('--font', type=int, default=2)
    ap.add_argument('--payload', help='the packed glyph bytes')
    ap.add_argument('--box', default='155x44')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    d = open(a.package, 'rb').read()
    box = tuple(int(v) for v in a.box.lower().split('x'))
    payload = open(a.payload, 'rb').read() if a.payload else b'\x01'
    out = add(d, a.cp, a.font, payload, box)
    print('0x%04X added to font %d: %d -> %d bytes' % (a.cp, a.font, len(d), len(out)))
    if len(out) != len(d):
        raise SystemExit('the package changed size, which it must never do')
    if a.write:
        open(a.package, 'wb').write(out)
        print('written')
    ok = fp.bounds(out)
    print('bounds %s' % ('ok' if ok else 'FAILED'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
