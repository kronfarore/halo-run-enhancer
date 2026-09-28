r"""Read an ODST level's REAL weapon palette and placements -- and why you place in Sapien.

THE SCENARIO TAG'S WEAPON PALETTE IS NOT THE ONE THAT COUNTS. `tool` says so itself:

    WARNING (group_postprocessing 'levels\atlas\sc150\sc150.scenario')
    'scenario_weapon_block' referenced by resource
    'levels\atlas\sc150\resources\sc150.scenario_weapons_resource'
    that is about to be stomped over isn't empty!

Fifteen of a scenario's blocks live in SEPARATE RESOURCE TAGS beside it -- weapons,
vehicles, equipment, scenery, decals, trigger volumes and more -- and at build time the
resource STOMPS the copy inside the .scenario. sc150's scenario tag lists 23 weapons; its
`resources\sc150.scenario_weapons_resource` lists the 17 the map really has, which is the
number the earlier ODST work measured. Editing the scenario's copy changes nothing, and
that is worth knowing on its own: it means a Guerilla edit to the weapon palette is
discarded, which is very likely what
`h3-import-weapon-recipe` recorded as "a palette entry alone got neither geometry nor
residency". The palette was never the problem; the edit never survived.

WHAT THIS FILE NO LONGER DOES. Three builds were spent trying to place the port
headlessly by overwriting a same-length tag reference in place -- a `frgt` chunk carries
its own length, so the swap is exact and nothing has to grow. Every variant WORKED as an
edit and none of them produced geometry:

    profile slot only        every tag present, zero chunks
    + real palette entry     the port's BITMAP arrives, still zero chunks
    + a real placement       identical map, still zero chunks

and `tool` never names the port once in a 134 KB build log -- no error, no warning. The
Halo 3 port, placed in SAPIEN, comes out of its own build with all ten of its chunks
(both models, both graphs, both bitmaps, four shaders), so the difference is the placing,
not the tags. **Place the weapon in Sapien.** Whatever a Sapien placement writes -- the
position, the BSP attachment, the unique id, the zone membership -- is what makes `tool`
gather, and it is the same conclusion the equipment work reached: "place the piece in
SAPIEN ... Sapien writes a valid placement plus its palette entry together, with the
position, BSP attachment, folder and unique ID that a hand-made entry lacks."

WHAT IT STILL DOES, because it was expensive to work out and is worth keeping: it reads
the REAL palette and the placements. The placement records are decoded from the block's
own data -- an 8-byte block header then fixed-size records with the palette index first
-- which reproduces sc150's three spawns as two shotguns and a covenant carbine. A wrong
stride gives indices wildly out of range, so that reading is its own proof.

    PORT_EK=odst python odst_saw_place.py                # the real palette + placements
"""
import argparse
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h3_kit                                                   # noqa: E402

B = os.sep
#: the palette entry this replaces, and the port's weapon tag -- SAME LENGTH by design
DONOR = B.join(['objects', 'weapons', 'turret', 'plasma_cannon', 'plasma_cannon_undeployed'])
PORT = h3_kit.SAW_WEAPON
RESOURCE = 'scenario_weapons_resource'


def resource(level):
    return os.path.join(h3_kit.TAGS, 'levels', 'atlas', level, 'resources',
                        '%s.%s' % (level, RESOURCE))


#: The weapons resource holds the PALETTE and the PLACEMENTS as two blocks. Neither is
#: findable by a marker alone, so they are found by SHAPE: the palette's elements each
#: carry a weapon tag reference, the placement block is the other one. Element sizes are
#: derived from the block's own data rather than assumed -- 8 bytes of block header then
#: a fixed record, which reproduces sc150's three placements as palette[16], [12] and
#: [16], i.e. two shotguns and a covenant carbine. That is the check that says the layout
#: was read correctly; a wrong stride gives indices far out of range.
PLACEMENT_HEADER = 8


def blocks(tag):
    """(palette block, placement block, [palette paths]) of a weapons resource."""
    # The palette is the block EVERY ONE of whose children holds EXACTLY ONE weapon
    # reference. "contains a weapon reference somewhere" is not enough -- the outermost
    # block contains all of them, and matching that one gives a palette of size 1.
    best, pal_blk = 0, None
    for n in tag.nodes():
        if n.marker != 'tgbl':
            continue
        kids = [c for c in n.children if c.marker == 'tgst']
        if not kids:
            continue
        per = [len(refs(bytes(tag.data[c.payload_at:c.off + 12 + c.length]))) for c in kids]
        if all(x == 1 for x in per) and len(kids) > best:
            best, pal_blk = len(kids), n
    if pal_blk is None:
        raise SystemExit('no weapon palette block in this resource')
    names = []
    for c in pal_blk.children:
        if c.marker != 'tgst':
            continue
        seg = bytes(tag.data[c.payload_at:c.off + 12 + c.length])
        i = seg.find(b'paew')
        names.append(seg[i + 4:].decode('latin1'))
    after = [n for n in tag.nodes()
             if n.marker == 'tgbl' and n.parent is pal_blk.parent and n.off > pal_blk.off]
    return pal_blk, (after[0] if after else None), names


def placements(tag, blk):
    """[(offset of the palette index, index)] for each placement in `blk`."""
    if blk is None:
        return []
    kids = [c for c in tag.nodes() if c.parent is blk]
    if not kids:
        return []
    own = min(c.off for c in kids) - blk.payload_at
    n = len([c for c in kids if c.marker == 'tgst'])
    if not n or (own - PLACEMENT_HEADER) % n:
        raise SystemExit('cannot size the placement records (%d bytes, %d of them)'
                         % (own, n))
    esz = (own - PLACEMENT_HEADER) // n
    out = []
    for k in range(n):
        at = blk.payload_at + PLACEMENT_HEADER + k * esz
        out.append((at, struct.unpack_from('<h', tag.data, at)[0]))
    return out


def refs(d, group='weap'):
    """[(offset of the path, path)] for every tag reference of `group`.

    Found by the chunk marker rather than by walking the tree: a `frgt` chunk is the
    marker, a u32 of flags, its u32 LENGTH, then the group 4CC stored backwards and the
    path with no terminator. That is enough to read and to overwrite, and it does not
    need the whole file to parse first -- which matters, because h3tag's forward scan
    does not finish on a 6.9 MB scenario inside ten minutes.
    """
    want = group[::-1].encode('latin1')
    out = []
    for m in re.finditer(b'frgt', d):
        at = m.start()
        length = struct.unpack_from('<I', d, at + 8)[0]
        if not (4 <= length <= 250) or d[at + 12:at + 16] != want:
            continue
        path = d[at + 16:at + 12 + length]
        try:
            path = path.decode('latin1')
        except UnicodeDecodeError:
            continue
        if path and not re.match(r'^[ -~]*$', path):
            continue
        out.append((at + 16, path))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--level', default='sc150')
    ap.add_argument('--donor', default=DONOR)
    ap.add_argument('--port', default=PORT)
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--write', action='store_true',
                    help='refused -- see the docstring; place the weapon in Sapien')
    a = ap.parse_args()
    print(h3_kit.banner())
    if not h3_kit.IS_ODST:
        raise SystemExit('this reads an ODST level; run it with PORT_EK=odst')

    p = resource(a.level)
    if not os.path.exists(p):
        raise SystemExit('no %s' % p)
    backup = p + '.before_saw'

    if a.restore:
        if not os.path.exists(backup):
            raise SystemExit('no %s to restore from' % os.path.basename(backup))
        shutil.copy2(backup, p)
        print('restored %s' % os.path.basename(p))
        return

    if a.write:
        raise SystemExit(
            'refused. Overwriting a palette entry here does NOT make tool gather the '
            "port's geometry:\nthree builds gave every tag and zero chunks, from a "
            'profile slot, a real palette entry\nand a real placement in turn. '
            'Place the weapon in Sapien.')

    d = bytearray(open(p, 'rb').read())
    got = refs(d)
    port = [path for _o, path in got if path == a.port]
    print('   %s: %d entries in the REAL weapon palette'
          % (os.path.basename(p), len(got)))
    for _off, path in got:
        print('      %-62s%s' % (path, '   <== the port' if path == a.port else ''))
    if not port:
        print('\n   the port is NOT in this palette yet -- place it in Sapien and rebuild')

    import h3tag
    t = h3tag.Tag(p)
    pal_blk, place_blk, names = blocks(t)
    got_pl = placements(t, place_blk)
    print('\n   %d placement(s):' % len(got_pl))
    for k, (_at, idx) in enumerate(got_pl):
        who = names[idx].rsplit(B, 1)[-1] if 0 <= idx < len(names) else 'OUT OF RANGE'
        print('      placement %d -> palette[%d] %s' % (k, idx, who))
    print('\nTo add the port: place it in SAPIEN, which writes the placement AND '
          'its palette entry together with the\n'
          'position, BSP attachment and unique id that a hand-made one lacks. Then '
          'build, and CHECK with\n'
          'h3_chunk_check before launching: a build that gathers no geometry still '
          'produces every tag and reads as success.')


if __name__ == '__main__':
    main()
