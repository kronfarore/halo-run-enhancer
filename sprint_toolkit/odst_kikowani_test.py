r"""Kikowani Station diagnostic: split the remaining explanations in ONE load.

Two independent things fail on sc150 and they need separating.

WEAPONS. Starting weapons come from a Player Starting Profile, not from a position,
so the dead spawn has nothing to do with them. The tags are not the problem either:
sc150 carries 16 of the 17 ODST weapons, the same as every other level (only Sniper
Rifle is genuinely absent). What is odd is the block itself -- profile 0 is named
"buck" and the other fifteen are all "a", where working levels use
"player starting profile_N", and the vanilla assault_rifle sits at indices 0, 4, 8
and 12. A stride of 4 across 16 entries looks like 4 players x 4 of something
(difficulty, or insertion point). If the level reads a profile other than 0, writing
profile 0 is simply writing the wrong row.

    --profiles all      write every profile (proves whether ANY row is read)
    --profiles 0,4,8,12 write the stride-4 rows only
    --profiles 0        the current behaviour, as a control

EQUIPMENT. A live scan put the player at (-326, 184, 4.6). The tool now drops items on
a nearby vanilla pickup, which lands ~17 units away -- in the level, but easy to walk
past. This drops a ring right ON the measured position instead, so "did it spawn" is
answered separately from "could I find it".

MCC must be closed: it holds the map open. The .bak is left alone, so the GUI's
baseline is unaffected and a normal patch restores everything.

    python odst_kikowani_test.py --profiles all
    python odst_kikowani_test.py --restore
"""
import argparse
import math
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import halo_patch as HP                                          # noqa: E402

ODST = (r"C:\Program Files (x86)\Steam\steamapps\common"
        r"\Halo The Master Chief Collection\halo3odst\maps")
MAP = os.path.join(ODST, 'sc150.map')
PRISTINE = MAP + '.kikotest'          # our own baseline, so the GUI's .bak is untouched
GAME = 'Halo 3: ODST'
REAL = (-326.0, 184.0, 4.6)           # from odst_poswatch, live

# Deliberately unmistakable: neither is in sc150's vanilla loadout, and both are
# visually obvious the instant the level starts.
PRIMARY = 'objects\\weapons\\support_high\\rocket_launcher\\rocket_launcher'
SECONDARY = 'objects\\weapons\\rifle\\shotgun\\shotgun'
PLUGINS = (r"C:\Program Files (x86)\Steam\steamapps\common\HCEEK"
           r"\Assembly-1-2023-11-29-1702446457\Plugins")


def _profile_block(m, reg):
    plug = reg.get('scnr')
    bf = (plug.find('Starting Health Damage', 'Player Starting Profile')
          or plug.find('Starting Health Modifier', 'Player Starting Profile'))
    if not bf:
        raise SystemExit('Player Starting Profile layout unavailable')
    scnr = HP._scnr_base(m)
    boff, esize = bf['block_offsets'][-1], bf['block_sizes'][-1]
    return scnr, boff, esize, m.i32(scnr + boff)


def write_weapons(m, reg, which):
    scnr, boff, esize, n = _profile_block(m, reg)
    idxs = range(n) if which == 'all' else [i for i in which if 0 <= i < n]
    salt = HP._h3_ident_salt(m, scnr, boff, esize, n)
    done = []
    for slot, path in (('primary', PRIMARY), ('secondary', SECONDARY)):
        datum = HP._h3_tag_datum(m, 'weap', path)
        if datum is None:
            print('  !! %s tag not in this map: %s' % (slot, path))
            continue
        for i in idxs:
            poff = m.follow(scnr, [boff], [esize], i)
            if poff is None:
                continue
            HP._write_starting_weapon(m, poff, slot, datum, 2, 8, GAME)
            done.append(i)
    print('  weapons -> profiles %s  (of %d, salt 0x%04X)'
          % (sorted(set(done)) if len(set(done)) < 17 else 'ALL', n, salt or 0))


def write_equipment(m):
    """A ring of every piece the level stocks, right on the measured position."""
    lay = HP._MAP_EQUIPMENT[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    pc = max(0, m.i32(scnr + poff))
    pbase = HP._block_base(m, scnr + poff)
    tags = []
    for i in range(pc):
        nm = HP._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
        if isinstance(nm, str) and nm not in tags:
            tags.append(nm)
    print('  equipment ring at %s from %d palette entr(ies)' % (REAL, len(tags)))
    res = HP._apply_spawn_equipment(m, GAME, {'groups': [tags]})
    for r in res:
        print('    %s' % {k: v for k, v in r.items() if k != 'effect'})
    # move whatever it just appended onto the real position, in a tight ring
    io, ies = lay['items']
    n = m.i32(scnr + io)
    base = HP._block_base(m, scnr + io)
    mask = HP._h3_mask_at(m, REAL, GAME) or 0x0002
    # TWO rings, because "nothing spawned" and "spawn protection ate it" look
    # identical from one ring. On Halo 3 every item 0-1u from the spawn was deleted
    # while everything 8u out survived, so the inner ring is the one at risk. If only
    # the outer ring appears, that is spawn protection, not a placement failure.
    added = list(range(max(0, n - len(tags)), n))
    inner, outer = added[:2], added[2:]
    for group, radius in ((inner, 1.6), (outer, 8.0)):
        for k, i in enumerate(group):
            e = base + i * ies
            ang = k * (2 * math.pi / max(1, len(group)))
            struct.pack_into('<fff', m.data, e + HP._EQ_POS,
                             REAL[0] + radius * math.cos(ang),
                             REAL[1] + radius * math.sin(ang), REAL[2])
            struct.pack_into('<H', m.data, e + HP._EQ_ATTACH, mask)
    print('    %d placement(s) on the real position: %d at 1.6u, %d at 8u, mask 0x%04X'
          % (len(added), len(inner), len(outer), mask))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--profiles', default='all',
                    help='"all", "none", or a comma list like 0,4,8,12')
    ap.add_argument('--no-equipment', action='store_true')
    ap.add_argument('--restore', action='store_true')
    a = ap.parse_args(argv)

    if not os.path.exists(MAP):
        raise SystemExit('not found: %s' % MAP)
    if a.restore:
        if not os.path.exists(PRISTINE):
            raise SystemExit('no %s to restore from' % PRISTINE)
        shutil.copy2(PRISTINE, MAP)
        print('restored sc150.map')
        return 0
    if not os.path.exists(PRISTINE):
        shutil.copy2(MAP, PRISTINE)
        print('saved a pristine copy: %s' % PRISTINE)
    shutil.copy2(PRISTINE, MAP)        # always build from pristine, never stack patches

    m = HP.open_map(MAP, GAME)
    reg = HP.PluginRegistry(PLUGINS, ['ODSTMCC', 'ODST'])
    print('sc150 diagnostic:')
    if a.profiles != 'none':
        which = 'all' if a.profiles == 'all' else [int(x) for x in a.profiles.split(',')]
        write_weapons(m, reg, which)
    if not a.no_equipment:
        write_equipment(m)
    m.save(MAP)
    print('\nwritten. Load Kikowani Station and report:')
    print('  - rocket launcher + shotgun in hand at the start?')
    print('  - a ring of equipment where you are standing?')
    print('undo with:  python odst_kikowani_test.py --restore')
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
