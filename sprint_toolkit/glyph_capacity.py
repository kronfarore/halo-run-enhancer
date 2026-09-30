r"""SUPERSEDED (2026-09-30) by h3_font_repack.py -- this never updated the block index,
the fonts' block ranges or the block count at +0x414. Kept for the record; do not use.

How many more weapon icons each game can actually take -- the porting ceiling.

A ported weapon needs a pickup glyph, and from Halo 3 on that glyph goes into
`maps\fonts\font_package_icon*.bin`. Those packages are FIXED SIZE, so the question
"how many weapons can this game accept" has a hard answer, and it is much smaller than
the number of weapons there are to port.

THE SPACE IS NOT WHERE IT LOOKS. A package is a series of 0xC000 blocks; each holds a
character table and a run of glyph payloads, and each font's glyphs are spread across
several blocks as ascending RUNS. A new glyph sorts into the run its codepoint extends,
so the only free space it can use is the tail of THAT block -- not the package's total.
Reach's x1 has 25,616 free bytes and only 1,408 of them are reachable by the HUD font,
which is the difference between twelve more icons and one.

ALL THREE (or four) RESOLUTIONS MUST TAKE IT, so the ceiling is the smallest of them.
The x1 package is usually the tightest because it is the smallest file.

HALO 1 HAS NO CEILING. It has no font package at all: the pickup icon is a sequence in
the shared `hud_msg_icons` BITMAP, and `add_msg_icon.py` APPENDS a bitmap and a sequence,
growing the tag. That is the model that scales, and it is worth remembering when the
later games' ceilings start to bite.

    python glyph_capacity.py
    python glyph_capacity.py --glyph 400      # if the icon art were smaller
"""
import argparse
import os
import struct

BLOCK = 0xC000
MCC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GAMES = ['halo3', 'halo3odst', 'haloreach', 'halo4']
NO_PACKAGE = {'halo1': 'no font package: the icon is a sequence in the hud_msg_icons '
                       'BITMAP, which add_msg_icon.py grows -- no ceiling',
              'halo2': 'fonts are edited in place under h2_fonts (h2_font_add.py); '
                       'measured separately'}
#: what one weapon icon costs, measured from the SAW at each resolution, plus the
#: 8 bytes its character-table entry adds to the same block
COST = {'font_package_icon.bin': 726 + 8, 'font_package_icon_x2.bin': 1732 + 8,
        'font_package_icon_x3.bin': 2844 + 8, 'font_package_icon_x4.bin': 4000 + 8}


def fonts(d):
    """[(name, index)] from the package header, which NAMES its fonts."""
    n = struct.unpack_from('<I', d, 4)[0]
    out = []
    for i in range(n):
        off = struct.unpack_from('<I', d, 8 + i * 12)[0]
        raw = d[off + 4:off + 0x104]      # the name starts 4 bytes into the header
        name = raw.split(b'\0', 1)[0].decode('latin1', 'replace')
        out.append((name, i))
    return out


def hud_index(d):
    """The font that draws the pickup prompt, by NAME rather than by a guessed index."""
    for name, i in fonts(d):
        low = name.lower()
        if 'hud' in low and 'number' not in low:
            return i, name
    return None, None


def survey(path, cost):
    d = open(path, 'rb').read()
    # Halo 4's packages are NOT 0xC000-blocked -- 327680 is not a multiple of it --
    # so the walk below would read off the end. Its layout is its own job; say so
    # rather than printing a number that means nothing.
    if len(d) % BLOCK:
        return None
    hud, hname = hud_index(d)
    total = usable = 0
    blocks = 0
    for base in range(BLOCK, len(d), BLOCK):
        blocks += 1
        a, b = struct.unpack_from('<II', d, base)
        cnt, tbl, doff, dsz = a >> 16, a & 0xFFFF, b & 0xFFFF, b >> 16
        free = BLOCK - (doff + dsz)
        total += free
        if any(struct.unpack_from('<HHI', d, base + tbl + k * 8)[1] == hud
               for k in range(cnt)):
            usable += free
    now = sum((BLOCK - ((struct.unpack_from('<II', d, base)[1] & 0xFFFF)
                        + (struct.unpack_from('<II', d, base)[1] >> 16))) // cost
              for base in range(BLOCK, len(d), BLOCK)
              if any(struct.unpack_from('<HHI', d, base
                                        + (struct.unpack_from('<II', d, base)[0] & 0xFFFF)
                                        + k * 8)[1] == hud
                     for k in range(struct.unpack_from('<II', d, base)[0] >> 16)))
    return dict(blocks=blocks, size=len(d), hud=hud, hname=hname,
                total=total, usable=usable, now=now,
                repacked=total // cost)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glyph', type=int,
                    help='override the x1 icon cost in bytes (x2/x3 scale with it)')
    a = ap.parse_args()
    cost = dict(COST)
    if a.glyph:
        cost = {k: int(a.glyph * (1 if '_x' not in k else int(k.split('_x')[1][0]) ** 2)) + 8
                for k in COST}

    for game, why in NO_PACKAGE.items():
        print('%-11s %s' % (game, why))
    print()
    print('%-11s %-26s %6s %8s %8s %6s %9s'
          % ('game', 'package', 'blocks', 'free', 'reachable', 'fits', 'if repacked'))
    ceilings = {}
    for game in GAMES:
        folder = os.path.join(MCC, game, 'maps', 'fonts')
        if not os.path.isdir(folder):
            continue
        low = []
        for f in sorted(cost):
            p = os.path.join(folder, f)
            if not os.path.exists(p):
                continue
            try:
                r = survey(p, cost[f])
            except Exception:
                r = None            # H4 again: the tables do not sit where these do
            if r is None:
                print('%-11s %-26s   not 0xC000-blocked -- needs its own reader'
                      % (game, f))
                continue
            low.append((r['now'], r['repacked']))
            print('%-11s %-26s %6d %8d %8d %6d %9d'
                  % (game, f, r['blocks'], r['total'], r['usable'], r['now'],
                     r['repacked']))
        if low:
            ceilings[game] = (min(x for x, _ in low), min(y for _, y in low))
        print()
    print('CEILING per game -- the smallest resolution wins, because all of them need it:')
    for g, (now, rep) in ceilings.items():
        print('   %-11s %3d more icon(s) today, %3d if the blocks were repacked'
              % (g, now, rep))


if __name__ == '__main__':
    main()
