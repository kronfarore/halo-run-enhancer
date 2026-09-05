r"""Put Halo 3 equipment into an ODST level, to find out whether it can be used.

Why this exists: ODST's Brutes carry the Halo 3 equipment in their char Equipment
Definitions at drop chance 1.0, but the drop does not actually happen in game, so
that route proves nothing. The equipment TAGS are all present in the map
(bubbleshield, regenerator, powerdrain, tripmine, superflare, jammer,
invincibility, gravlift, instantcover, autoturret) — they are simply never placed.

Why it repoints instead of adding: a level's equipment PALETTE lists only health
packs, ammo and grenades, and `_apply_equipment_swaps` refuses anything absent
from it. Adding an entry means growing a scenario tagblock, which in H3-derived
maps has to be relocated into partition slack (see `_h3_reserve`). Repointing an
existing palette entry needs none of that: every placement that referenced the old
tag now spawns the new one, in the same spots, with no block resized.

It is a TEST tool, not a feature. It edits one map in place, keeps a .bak, and can
put it back.

    python odst_equip_test.py sc100 --list
    python odst_equip_test.py sc100 --swap health_pack_medium bubbleshield_equipment
    python odst_equip_test.py sc100 --restore
"""
import argparse
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _vault():
    """map_vault, imported on demand -- it lives in sprint_toolkit, not beside this."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'sprint_toolkit'))
    import map_vault
    return map_vault

MAPS = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\halo3odst\maps")
PAL_OFF, PAL_ELEM, PAL_ID_AT = 0x124, 0x10, 0xC     # scnr Equipment Palette (ODST)
ITEMS_OFF, ITEMS_ELEM, ITEM_PAL_IDX = 0x118, 0x8C, 0x0
CHAR_EQUIP_BLOCK, CHAR_EQUIP_ELEM, CHAR_EQUIP_ID = 0x1D4, 0x24, 0xC


def _open(level):
    from halo3_map import Halo3Map
    path = os.path.join(MAPS, level + '.map')
    if not os.path.exists(path):
        raise SystemExit('no such map: ' + path)
    return path, Halo3Map(path)


def _palette(m, scnr):
    import halo_patch as HP
    out = []
    for i, el in enumerate(m.follow_all(scnr, [PAL_OFF], [PAL_ELEM], 'all')):
        ident = struct.unpack_from('<I', m.data, el + PAL_ID_AT)[0]
        name = HP._tag_name_by_id(m, ident) if ident != 0xFFFFFFFF else None
        out.append((i, el, ident, name))
    return out


def _placement_counts(m, scnr, npal):
    counts = [0] * max(npal, 1)
    for pl in m.follow_all(scnr, [ITEMS_OFF], [ITEMS_ELEM], 'all'):
        idx = struct.unpack_from('<h', m.data, pl + ITEM_PAL_IDX)[0]
        if 0 <= idx < len(counts):
            counts[idx] += 1
    return counts


def _find_ident(m, short):
    """A valid datum id for an eqip tag.

    Uses halo_patch._h3_tag_datum, which builds the ident properly and works on ODST
    maps unchanged. An earlier version borrowed one from a char Equipment Definitions
    tagref, which only reached equipment some character in that map referenced --
    invisibility_equipment has no such carrier in sc100 and was unreachable.
    """
    import halo_patch as HP
    for t in m.tags:
        if t['class'] != 'eqip' or not t.get('name'):
            continue
        if t['name'].rsplit('\\', 1)[-1] != short:
            continue
        datum = HP._h3_tag_datum(m, 'eqip', t['name'])
        if datum is not None:
            return datum, t['name']
    return None, None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('level')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--swap', nargs=2, metavar=('FROM', 'TO'),
                    help='repoint the palette entry holding FROM at TO (short names)')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args(argv)

    import halo_patch as HP
    path, m = _open(a.level)
    bak = _vault().baseline_for('Halo 3: ODST', path)

    if a.restore:
        if not os.path.exists(bak):
            raise SystemExit('no baseline at ' + bak)
        shutil.copy2(bak, path)
        print('restored %s from %s' % (os.path.basename(path), bak))
        return 0

    scnr = HP._scnr_base(m)
    pal = _palette(m, scnr)
    counts = _placement_counts(m, scnr, len(pal))

    if a.list or not a.swap:
        print('%s equipment palette (%d entries), with placement counts:\n'
              % (a.level, len(pal)))
        for i, _el, _id, name in pal:
            print('  [%2d] %-46s %d placement(s)'
                  % (i, (name or '<none>').rsplit('\\', 1)[-1], counts[i]))
        print('\nEquipment tags present in the map but NOT in the palette:')
        inpal = {(n or '').rsplit('\\', 1)[-1] for _, _, _, n in pal}
        for t in sorted({t['name'] for t in m.tags
                         if t['class'] == 'eqip' and t.get('name')}):
            short = t.rsplit('\\', 1)[-1]
            if short not in inpal and 'equipment' in short:
                print('   %s' % short)
        return 0

    src, dst = a.swap
    hit = [(i, el, ident, name) for i, el, ident, name in pal
           if name and name.rsplit('\\', 1)[-1] == src]
    if not hit:
        raise SystemExit('%r is not in this level\'s equipment palette' % src)
    ident, full = _find_ident(m, dst)
    if ident is None:
        raise SystemExit('could not find a usable reference to %r in this map' % dst)

    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print('kept a pristine backup at %s' % os.path.basename(bak))
    i, el, old_ident, old_name = hit[0]
    struct.pack_into('<I', m.data, el + PAL_ID_AT, ident)
    with open(path, 'wb') as f:
        f.write(m.data)
    print('palette[%d]: %s -> %s' % (i, old_name, full))
    print('%d placement(s) in %s now spawn it.' % (counts[i], a.level))
    print('\nLoad the level and look where those pickups normally are.')
    print('Undo with:  python odst_equip_test.py %s --restore' % a.level)
    return 0


if __name__ == '__main__':
    sys.exit(main())
