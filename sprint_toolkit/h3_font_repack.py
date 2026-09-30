r"""Rebuild a font package from its glyphs, so it can hold as many icons as there are
weapons to port -- Halo 3, ODST and Reach.

THE BLOCK INDEX. Right after the font headers, in the header region, sits one pair of u32
KEYS per block -- the first and the last entry that block holds -- where a key is
`font << 16 | codepoint`. Checked against every block of all nine shipped packages
(Halo 3, ODST and Reach, x1/x2/x3): it matches exactly, and nothing follows it. The whole
file is ONE list ascending by that key, cut into 0xC000 blocks, and the index is how the
engine finds which block to search.

This is what the earlier glyph work tripped over without seeing:
  * Reach's 0xE150 in an APPENDED block drew a box -- the index did not list the block.
  * Reach's 0xE150 placed in block 4 drew a box -- block 4's range is font 5 only, so
    font 3's key was outside it. "Stay inside the font's native range" was a coincidence;
    the real rule is that the index must cover the glyph.
  * Halo 3's 0xE06A and ODST's 0xE04A each became the LAST entry of an x2 block without
    the index moving, so at x2 the engine cannot find them. Repacking fixes both.

SO THE PACKAGE CAN GROW. Every entry and its glyph record is read out, the new glyphs
are sorted in, and the list is laid into as many 0xC000 blocks as it needs, first-fit in
key order, then the index is rewritten. The block count is stored nowhere else: the file
length and the index are the whole of it.

PROVEN BEFORE IT IS TRUSTED: `--selftest` rebuilds every shipped package from its own
glyphs with no change and must reproduce each file BYTE FOR BYTE.

    python h3_font_repack.py --selftest
    python h3_font_repack.py --report                 # the live packages, and their index
    python h3_font_repack.py --fix-index --write      # rewrite a stale index in place
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BLOCK = 0xC000
ENTRY = 8
TABLE = 8                     # the table always starts right after the two header u32s
MCC = os.path.dirname(os.path.dirname(HERE))
GAMES = {'halo3': 'h3', 'halo3odst': 'odst', 'haloreach': 'reach'}
PACKAGES = ('font_package_icon.bin', 'font_package_icon_x2.bin', 'font_package_icon_x3.bin')
PRISTINE = r'E:\HaloBackups\%s_live_fonts'


def live(game, name):
    return os.path.join(MCC, game, 'maps', 'fonts', name)


def pristine(game, name):
    return os.path.join(PRISTINE % GAMES[game], name)


def key(cp, font):
    return font << 16 | cp


def _pad(n):
    return n + (-n % 16)


def index_at(d):
    """Where the block index starts: right after the last font header."""
    _magic, n = struct.unpack_from('<II', d, 0)
    return max(o + s for o, s, _i in (struct.unpack_from('<III', d, 8 + i * 12)
                                       for i in range(n)))


def parse(d):
    """(header region, [block]) where a block is [(cp, font, record bytes)] in table order.

    A record is the 16-byte glyph header plus its payload, padded to 16 -- sliced from its
    offset to the NEXT record's offset in data order, so any padding the builder left is
    kept exactly. Several entries may share one record; that is kept as well.
    """
    blocks = []
    for base in range(BLOCK, len(d), BLOCK):
        a, b = struct.unpack_from('<II', d, base)
        count, table = a >> 16, a & 0xFFFF
        data, size = b & 0xFFFF, b >> 16
        if table != TABLE or data != TABLE + count * ENTRY or data + size > BLOCK:
            raise SystemExit('block 0x%X does not read as a block' % base)
        ents = [struct.unpack_from('<HHI', d, base + table + k * ENTRY) for k in range(count)]
        starts = sorted({off for _c, _f, off in ents} | {data + size})
        nxt = dict(zip(starts, starts[1:]))
        blocks.append([(cp, font, bytes(d[base + off:base + nxt[off]]), off)
                       for cp, font, off in ents])
    return bytes(d[:BLOCK]), blocks


def check_index(d):
    """(ok, stored, actual) -- the index against the blocks' real first/last keys."""
    _h, blocks = parse(d)
    actual = []
    for b in blocks:
        actual += [key(b[0][0], b[0][1]), key(b[-1][0], b[-1][1])]
    at = index_at(d)
    stored = list(struct.unpack_from('<%dI' % len(actual), d, at))
    return stored == actual, stored, actual


def build_block(ents):
    """One 0xC000 block from [(cp, font, record, shared-id)] in key order."""
    out = bytearray(BLOCK)
    data = TABLE + len(ents) * ENTRY
    at, placed = data, {}
    for k, (cp, font, rec, sid) in enumerate(ents):
        if sid not in placed:
            placed[sid] = at
            out[at:at + len(rec)] = rec
            at += len(rec)
        struct.pack_into('<HHI', out, TABLE + k * ENTRY, cp, font, placed[sid])
    if at > BLOCK:
        raise SystemExit('block overflow (%d bytes)' % at)
    struct.pack_into('<II', out, 0, len(ents) << 16 | TABLE, (at - data) << 16 | data)
    return bytes(out)


def need(ents):
    seen, n = set(), TABLE + len(ents) * ENTRY
    for _c, _f, rec, sid in ents:
        if sid not in seen:
            seen.add(sid)
            n += len(rec)
    return n


def layout(ents, split=None, reserve=0):
    """Cut the key-ordered list into blocks. `split` = entry counts per block to copy an
    existing layout; otherwise first-fit, leaving `reserve` bytes free in each block."""
    out, i = [], 0
    if split:
        for n in split:
            out.append(ents[i:i + n])
            i += n
        return out
    cur = []
    for e in ents:
        # a shared record belongs with its first user; never split one across blocks
        trial = cur + [e]
        if cur and need(trial) > BLOCK - reserve and e[3] not in {x[3] for x in cur}:
            out.append(cur)
            cur = [e]
        else:
            cur = trial
    if cur:
        out.append(cur)
    return out


def assemble(header, blocks):
    """The package: header region with a fresh index, then the blocks."""
    head = bytearray(header)
    at = index_at(head)
    room = BLOCK - at
    if 8 * len(blocks) > room:
        raise SystemExit('%d blocks need %d index bytes, the header has %d'
                         % (len(blocks), 8 * len(blocks), room))
    head[at:] = bytes(room)
    for k, b in enumerate(blocks):
        struct.pack_into('<II', head, at + 8 * k,
                         key(b[0][0], b[0][1]), key(b[-1][0], b[-1][1]))
    # THE FONT'S OWN BLOCK RANGE. The third u32 of each font's header triple is
    # (blocks it spans << 16) | first block -- matched on every font of all nine shipped
    # packages. The first growth test left it alone and EVERY weapon icon broke at once:
    # the engine searched the HUD font's old blocks.
    nf = struct.unpack_from('<I', head, 4)[0]
    for f in range(nf):
        where = [k for k, b in enumerate(blocks) if any(e[1] == f for e in b)]
        if where:
            struct.pack_into('<I', head, 8 + f * 12 + 8,
                             (where[-1] - where[0] + 1) << 16 | where[0])
    return bytes(head) + b''.join(build_block(b) for b in blocks)


def entries(d):
    """Every entry in key order as (cp, font, record, shared-id), plus the old split."""
    header, blocks = parse(d)
    ents, split = [], []
    for bi, b in enumerate(blocks):
        split.append(len(b))
        for cp, font, rec, off in b:
            ents.append((cp, font, rec, (bi, off)))
    keys = [key(c, f) for c, f, _r, _s in ents]
    if any(a >= b for a, b in zip(keys, keys[1:])):
        raise SystemExit('the package is not one ascending list by (font, codepoint)')
    return header, ents, split


def repack(d, add=(), reserve=0, split=None):
    """`d` rebuilt, with `add` = [(cp, font, record)] sorted in. Refuses duplicates."""
    header, ents, old_split = entries(d)
    have = {key(c, f) for c, f, _r, _s in ents}
    for n, (cp, font, rec) in enumerate(add):
        if key(cp, font) in have:
            raise SystemExit('font %d already has 0x%04X' % (font, cp))
        ents.append((cp, font, rec + b'\0' * (-len(rec) % 16), ('new', n)))
    ents.sort(key=lambda e: key(e[0], e[1]))
    return assemble(header, layout(ents, split=split if split is not None
                                   else None, reserve=reserve))


def record(payload, box, advance=None):
    w, h = box
    rec = struct.pack('<IIHHHH', advance if advance is not None else w, len(payload),
                      w, h, 0, 0) + payload
    return rec + b'\0' * (-len(rec) % 16)


def font_header_add(d, cp, font, payload, box):
    """The font header's own bookkeeping for one more glyph, as h3_font_add does it."""
    d = bytearray(d)
    off = struct.unpack_from('<I', d, 8 + font * 12)[0]
    w, h = box
    rec = record(payload, box)
    struct.pack_into('<I', d, off + 0x13C, struct.unpack_from('<I', d, off + 0x13C)[0] + 1)
    if cp + 1 > struct.unpack_from('<I', d, off + 0x138)[0]:
        struct.pack_into('<I', d, off + 0x138, cp + 1)
    if len(payload) > struct.unpack_from('<I', d, off + 0x150)[0]:
        struct.pack_into('<I', d, off + 0x150, len(payload))
    if w * h * 2 > struct.unpack_from('<I', d, off + 0x154)[0]:
        struct.pack_into('<I', d, off + 0x154, w * h * 2)
    for field, delta in ((0x144, len(rec)), (0x158, len(payload))):
        struct.pack_into('<I', d, off + field, struct.unpack_from('<I', d, off + field)[0] + delta)
    return bytes(d)


def add_glyph(d, cp, font, payload, box, reserve=0):
    """Add one glyph ANYWHERE in the key order: the package is rebuilt around it and grows
    by whole blocks if it has to. The replacement for h3_font_add/place/grow."""
    out = repack(d, add=[(cp, font, record(payload, box))], reserve=reserve)
    out = font_header_add(out, cp, font, payload, box)
    ok, _s, _a = check_index(out)
    if not ok:
        raise SystemExit('the rebuilt index does not match its blocks; refusing')
    return out


def capacity(d, glyph_bytes, reserve=0):
    """How many more glyphs of `glyph_bytes` fit WITHOUT growing, after a repack."""
    _h, ents, split = entries(d)
    used = sum(len(r) for _c, _f, r, s in {e[3]: e for e in ents}.values()) + ENTRY * len(ents)
    blocks = len(split)
    free = blocks * (BLOCK - TABLE - reserve) - used
    return max(0, free // (glyph_bytes + ENTRY)), blocks


def growth_test_layout(d, hud_font):
    """Fonts below `hud_font` spread over the SHIPPED block count, so the whole HUD font
    and everything after it lands in blocks the package never had. One boot then answers
    whether the engine reads a grown package: every weapon icon draws, or none does."""
    header, ents, split = entries(d)
    shipped = len(split)
    low = [e for e in ents if e[1] < hud_font]
    rest = [e for e in ents if e[1] >= hud_font]
    if len(low) < shipped:
        raise SystemExit('only %d entries below font %d to spread over %d blocks'
                         % (len(low), hud_font, shipped))
    per, extra = divmod(len(low), shipped)
    blocks, i = [], 0
    for k in range(shipped):
        n = per + (1 if k < extra else 0)
        blocks.append(low[i:i + n])
        i += n
    blocks += layout(rest)
    out = assemble(header, blocks)
    if not check_index(out)[0]:
        raise SystemExit('growth-test package has a bad index; refusing')
    first_hud = next(k for k, b in enumerate(blocks) if any(e[1] >= hud_font for e in b))
    return out, shipped, len(blocks), first_hud


def shift_test_layout(d):
    """Same block COUNT as shipped, every boundary moved: first-fit with the largest
    per-block reserve that still fits. Separates a block-count cap (this works) from a
    layout field not yet understood (this breaks too)."""
    header, ents, split = entries(d)
    n, best = len(split), 0
    for r in range(0, 0x4000, 16):
        if len(layout(ents, reserve=r)) == n:
            best = r
    out = assemble(header, layout(ents, reserve=best))
    if not check_index(out)[0] or len(out) != len(d):
        raise SystemExit('shift-test package is bad; refusing')
    return out, n, best


def selftest():
    ok = True
    for game in GAMES:
        for name in PACKAGES:
            p = pristine(game, name)
            if not os.path.exists(p):
                print('%-10s %-26s no pristine copy' % (game, name))
                continue
            d = open(p, 'rb').read()
            idx, _s, _a = check_index(d)
            same = repack(d, split=entries(d)[2]) == d
            first_fit = repack(d)
            ff_same = first_fit == d
            ok &= same and idx
            print('%-10s %-26s index %-5s  same-split rebuild %s  first-fit %s (%d blocks)'
                  % (game, name, idx, 'IDENTICAL' if same else 'DIFFERS',
                     'identical' if ff_same else 'differs',
                     (len(first_fit) // BLOCK) - 1))
    print('\nselftest %s' % ('PASSED' if ok else 'FAILED'))
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--fix-index', action='store_true',
                    help='rebuild every live package whose index is stale')
    ap.add_argument('--growth-test', metavar='GAME',
                    help='write the one-boot growth test into the live packages of GAME')
    ap.add_argument('--undo-growth-test', metavar='GAME')
    ap.add_argument('--shift', action='store_true',
                    help='with --growth-test: keep the block count, move the boundaries')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if a.growth_test or a.undo_growth_test:
        game = a.growth_test or a.undo_growth_test
        keep = os.path.join(PRISTINE % GAMES[game], 'before_growth_test')
        hud = {'halo3': 2, 'halo3odst': 3, 'haloreach': 3}[game]
        for name in PACKAGES:
            p, k = live(game, name), os.path.join(keep, name)
            if a.undo_growth_test:
                open(p, 'wb').write(open(k, 'rb').read())
                print('restored', name)
                continue
            d = open(p, 'rb').read()
            if os.path.exists(k):
                d = open(k, 'rb').read()          # always build from the pre-test file
            if a.shift:
                out, shipped, res = shift_test_layout(d)
                print('%-26s %2d blocks kept, every boundary moved (reserve %d)'
                      % (name, shipped, res))
                if a.write:
                    os.makedirs(keep, exist_ok=True)
                    if not os.path.exists(k):
                        open(k, 'wb').write(d)
                    open(p, 'wb').write(out)
                continue
            out, shipped, now, first = growth_test_layout(d, hud)
            print('%-26s %2d -> %2d blocks; the HUD font starts in block %d (0-based), '
                  'past the shipped %d' % (name, shipped, now, first, shipped))
            if a.write:
                os.makedirs(keep, exist_ok=True)
                if not os.path.exists(k):
                    open(k, 'wb').write(d)
                open(p, 'wb').write(out)
        print('written' if a.write or a.undo_growth_test else '(dry run -- pass --write)')
        return
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    for game in GAMES:
        for name in PACKAGES:
            p = live(game, name)
            d = open(p, 'rb').read()
            ok, stored, actual = check_index(d)
            n, blocks = capacity(d, 1400)
            print('%-10s %-26s %2d blocks  index %s  ~%d more 1.4 KB icons after a repack'
                  % (game, name, blocks, 'ok' if ok else 'STALE', n))
            if not ok:
                for i, (s, t) in enumerate(zip(stored, actual)):
                    if s != t:
                        print('      block %d %s: index %#x, holds %#x'
                              % (i // 2, 'first' if i % 2 == 0 else 'last', s, t))
                if a.fix_index:
                    out = repack(d, split=entries(d)[2])
                    if not check_index(out)[0] or len(out) != len(d):
                        raise SystemExit('fix produced a bad package; refusing')
                    if a.write:
                        open(p, 'wb').write(out)
                        print('      index rewritten')
                    else:
                        print('      (would rewrite -- pass --write)')


if __name__ == '__main__':
    main()
