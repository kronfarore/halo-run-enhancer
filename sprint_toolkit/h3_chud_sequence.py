r"""Read and set which sprite a Halo 3 HUD bitmap widget draws, in the Editing Kit tag.

This has to be a TAG edit rather than a patcher row. The map's chdt plugin does describe
Sequence Index, but `apply_field`'s `index` addresses the outermost block: a chud has
several Widget Collections and the meter lives in a later one, so index 4 comes back
"empty block in this tag" while index 0 quietly rewrites the wrong widget.

In the tag each bitmap widget is a `tgst` whose parent `tgbl` is its block, and the
widget's field data sits in that BLOCK's payload, not the struct's -- the struct has no
own-data at all. A block can hold SEVERAL widgets, laid out end to end, so

    Sequence Index = block payload + 0x58 + (element index * 84)

The base offset was found by cross-referencing two weapons whose values are known from
the map (the Assault Rifle's meter reads 11, the SMG's 10) rather than by trusting the
plugin's cache-side offset of 0x50; the 84-byte stride reproduces the Assault Rifle's
last block as [11, 0, 0] and the SMG's as [10, 12, 0], which is what the map reports.

    python h3_chud_sequence.py --chud assault_rifle          # show every widget
    python h3_chud_sequence.py --chud saw --bitmap ballistic_meters --set 19 --write
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3tag                                                   # noqa: E402

B = os.sep
CHUD = os.path.join('F:' + B, 'SteamLibrary', 'steamapps', 'common', 'H3EK',
                    'tags', 'ui', 'chud')
SEQ_OFF = 0x58
ELEM = 84          # one Bitmap Widgets element


def widgets(tag):
    """[(bitmap name, offset of the Sequence Index byte)] for widgets under `tag!`.

    Only the `tag!` section: a chud also carries a `want` section that repeats every
    widget, and editing those would be editing the wrong copy.
    """
    root = [n for n in tag.nodes() if n.parent is None and n.marker == 'tag!']
    if not root:
        return []
    root = root[0]

    def under(x):
        p = x.parent
        while p is not None:
            if p is root:
                return True
            p = p.parent
        return False

    out, seen = [], {}
    for x in tag.nodes():
        if x.marker != 'tgrf' or not under(x):
            continue
        grp = bytes(tag.data[x.payload_at:x.payload_at + 4])[::-1].decode('latin1')
        if grp.strip() != 'bitm':
            continue
        name = bytes(tag.data[x.payload_at + 4:x.payload_at + x.length])
        name = name.decode('latin1').rsplit(B, 1)[-1]
        block = x.parent.parent                       # widget struct -> its block
        # a block can hold several widgets; count how many of this block we have seen
        i = seen.get(block.off, 0)
        seen[block.off] = i + 1
        out.append((name, block.payload_at + SEQ_OFF + i * ELEM))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chud', default='assault_rifle')
    ap.add_argument('--bitmap')
    ap.add_argument('--set', type=int)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    p = os.path.join(CHUD, a.chud + '.chud_definition')
    if not os.path.exists(p):
        raise SystemExit('no %s' % p)
    t = h3tag.Tag(p)
    ok, cov, tot = t.check()
    print('%s parses: %s (%d/%d)' % (a.chud, ok, cov, tot))
    got = widgets(t)
    for i, (name, at) in enumerate(got):
        mark = ' <--' if a.bitmap and name == a.bitmap else ''
        print('   [%d] %-20s sprite %-4d @%#x%s' % (i, name, t.data[at], at, mark))

    if a.set is None or not a.bitmap:
        return
    hits = [at for name, at in got if name == a.bitmap]
    if not hits:
        raise SystemExit('no %s widget in this chud' % a.bitmap)
    if len(hits) > 1:
        print('   %d %s widgets -- all set' % (len(hits), a.bitmap))
    if not a.write:
        print('\n(dry run -- pass --write)')
        return
    for at in hits:
        t.data[at] = a.set
    ok, cov, tot = t.check()
    print('after: %s -> %d ; parses %s (%d/%d)' % (a.bitmap, a.set, ok, cov, tot))
    if not ok:
        raise SystemExit('not saved')
    t.save(p)
    print('wrote %s' % p)


if __name__ == '__main__':
    main()
