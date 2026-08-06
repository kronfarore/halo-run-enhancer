"""Insert an equipment placement into a built Halo 2 cache map.

Camo in H2 needs a pickup to exist in the world: no campaign map ships the
active_camouflage equipment tag, and every spawn verb either takes a plain
string (`drop`, which creates no tag dependency and finds nothing) or an
<object_name> that must already be in the scenario. Getting the TAG into the map
is solved on the build side with object_type_predict; this handles the other
half, the scenario PLACEMENT, by patching the cache directly the way
h1_loosetag.py does for Halo 1.

Two modes:
  --auto      an ordinary pickup that spawns with the level. Proves placements
              work at all, and needs no script.
  --named N   a non-auto-spawning placement plus an Object Names entry, which is
              what (object_create N) / objects_attach / objects_detach address.
              Note the name must ALSO exist when the scripts are compiled, so a
              named placement only helps if the scenario source carries it too.

The new element is copied verbatim from an existing placement so every field we
don't understand keeps a known-good value; only palette index, flags, position,
name and unique ID are rewritten.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as hp    # noqa: E402

ITEMS, IES = 0x80, 0x38          # scnr Equipment placements
PAL, PES = 0x88, 0x28            # scnr Equipment palette
NAMES, NES = 0x48, 0x24          # scnr Object Names
STARTS, SES = 0x100, 0x34        # scnr Player Starting Locations

FLAG_NOT_AUTOMATICALLY = 0x1
FLAG_CREATE_AT_REST = 0x100      # skip the settle-under-gravity drop
TYPE_EQUIPMENT = 3


def _blk(m, scnr, off):
    return m.i32(scnr + off), hp._block_base(m, scnr + off)


def _elem(m, base, size, i):
    return bytes(m.data[base + i * size:base + (i + 1) * size])


def _max_unique_id(m, scnr):
    """Unique IDs are map-wide, so scan every object block we know the shape of
    rather than just the equipment one."""
    top = 0
    for off, es, uid_at in ((ITEMS, IES, 0x28), (0x50, 0x5C, 0x28), (0x70, 0x54, 0x28)):
        n, b = _blk(m, scnr, off)
        for i in range(n if b else 0):
            top = max(top, struct.unpack_from('<I', m.data, b + i * es + 0x28)[0] & 0xFFFF)
    return top


# Placement blocks by Object Names "Type", so a borrowed name's previous owner can
# be un-named. Only the ones whose layout we've verified are listed; every entry is
# (block offset, element size) and they all carry Name Index at +0x2.
_OWNER_BLOCK = {0: (0x60, 0x50), 1: (0x70, 0x54), 2: (0x78, 0x54),
                3: (ITEMS, IES), 6: (0x50, 0x5C)}


def borrow_name(m, scnr, want):
    """Find an existing Object Names entry by string. object_create resolves names
    at COMPILE time, so a name appended to the cache is invisible to the scripts;
    reusing a name the scenario already declares is what makes a cache-only patch
    work. Caller is responsible for having picked one no .hsc mentions."""
    n, b = _blk(m, scnr, NAMES)
    for i in range(n):
        e = b + i * NES
        if m.data[e:e + 0x20].split(b'\0')[0].decode('latin-1') == want:
            t, pl = struct.unpack_from('<hh', m.data, e + 0x20)
            return i, t, pl
    raise SystemExit('object name %r not found in this scenario' % want)


def insert(map_path, tag_path, out_path=None, name=None, offset=(0.0, 0.0, 0.5),
           at=None, borrow=None, verbose=True):
    m = hp.open_map(map_path, 'Halo 2')
    scnr = hp._scnr_base(m)
    scnr_base = m.scenario_tag()['base']

    tag = next((t for t in m.tags if t['class'] == 'eqip' and t['name'] == tag_path), None)
    if tag is None:
        have = sorted(t['name'] for t in m.tags if t['class'] == 'eqip')
        raise SystemExit("eqip tag %r is not in this map. It has:\n  %s"
                         % (tag_path, '\n  '.join(have)))

    pn, pb = _blk(m, scnr, PAL)
    inx = next((i for i in range(pn)
                if hp._tag_name_by_id(m, m.u32(pb + i * PES + 0x4)) == tag_path), None)
    if inx is None:
        # Copy a working entry so the trailing unknowns keep valid values, then
        # point it at our tag. The class magic at +0x0 is already 'eqip'.
        pal_elem = bytearray(_elem(m, pb, PES, 0))
        struct.pack_into('<I', pal_elem, 0x4, tag['datum'])
        m.grow_block(scnr_base, PAL, PES, [bytes(pal_elem)])
        inx = pn
        if verbose:
            print('palette entry %d -> %s' % (inx, tag_path))
    elif verbose:
        print('palette entry %d already references %s' % (inx, tag_path))

    if at is None:
        sn, sb = _blk(m, scnr, STARTS)
        if not sn:
            raise SystemExit('level has no player starting location to anchor to')
        at = struct.unpack_from('<fff', m.data, sb)
    pos = tuple(a + b for a, b in zip(at, offset))

    n, b = _blk(m, scnr, ITEMS)
    elem = bytearray(_elem(m, b, IES, 0))
    flags = FLAG_CREATE_AT_REST | (FLAG_NOT_AUTOMATICALLY if (name or borrow) else 0)
    struct.pack_into('<hh', elem, 0x0, inx, -1)
    struct.pack_into('<I', elem, 0x4, flags)
    struct.pack_into('<fff', elem, 0x8, *pos)
    struct.pack_into('<I', elem, 0x28, _max_unique_id(m, scnr) + 1)
    elem[0x2E] = TYPE_EQUIPMENT

    if borrow:
        idx, old_type, old_pl = borrow_name(m, scnr, borrow)
        struct.pack_into('<h', elem, 0x2, idx)
        nb = _blk(m, scnr, NAMES)[1]
        struct.pack_into('<hh', m.data, nb + idx * NES + 0x20, TYPE_EQUIPMENT, n)
        # Leaving the old owner pointing at a name that now describes something else
        # would give two placements the same name, so drop its claim.
        ob = _OWNER_BLOCK.get(old_type)
        if ob:
            obase = _blk(m, scnr, ob[0])[1]
            struct.pack_into('<h', m.data, obase + old_pl * ob[1] + 0x2, -1)
        if verbose:
            print('borrowed name %d %r (was type=%d placement=%d) -> placement %d'
                  % (idx, borrow, old_type, old_pl, n))
    elif name:
        nn, nb = _blk(m, scnr, NAMES)
        struct.pack_into('<h', elem, 0x2, nn)
        rec = bytearray(NES)
        rec[0:len(name)] = name.encode('latin-1')
        struct.pack_into('<hh', rec, 0x20, TYPE_EQUIPMENT, n)
        m.grow_block(scnr_base, NAMES, NES, [bytes(rec)])
        if verbose:
            print('object name %d -> %r (placement %d)' % (nn, name, n))

    m.grow_block(scnr_base, ITEMS, IES, [bytes(elem)])
    if verbose:
        print('placement %d  pal=%d flags=0x%X pos=%.2f,%.2f,%.2f'
              % (n, inx, flags, pos[0], pos[1], pos[2]))

    m.update_checksum()
    m.save(out_path or map_path)
    if verbose:
        print('wrote %s' % (out_path or map_path))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('map')
    ap.add_argument('--tag', default=r'objects\powerups\active_camouflage\active_camouflage')
    ap.add_argument('--name', help='object name; omit for an auto-spawning pickup')
    ap.add_argument('--borrow', help='reuse an EXISTING scenario object name (one no '
                                     'script mentions) so object_create can resolve it')
    ap.add_argument('--out')
    ap.add_argument('--offset', default='0,0,0.5',
                    help='metres from the anchor, "x,y,z" (default 0,0,0.5)')
    ap.add_argument('--at', help='absolute "x,y,z"; default is player start 0')
    a = ap.parse_args(argv)
    insert(a.map, a.tag, a.out, a.name,
           tuple(float(v) for v in a.offset.split(',')),
           tuple(float(v) for v in a.at.split(',')) if a.at else None,
           a.borrow)


if __name__ == '__main__':
    main()
