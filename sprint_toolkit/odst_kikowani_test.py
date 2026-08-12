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


def _palette_path(m, want):
    """Full tag path of the Weapon Palette entry matching `want`, or None."""
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    poff, pes = lay['palette']
    n, base = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)
    for i in range(n) if base else []:
        nm = HP._tag_name_by_id(m, m.u32(base + i * pes + 0xC))
        if nm and str(nm).rsplit('\\', 1)[-1].lower() == want.lower():
            return str(nm)
    return None


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


def carbine_test(m):
    """Repalette every Covenant Carbine placement to the rocket launcher, and move the
    equipment onto the carbine nearest the real start.

    The point is that a vanilla placement is a spot the level definitely streams. If
    the rocket launcher appears where a carbine was, weapon tags render fine on sc150
    and the empty hands are a starting-profile problem. If it does not appear even
    there, the weapon cannot render on this map at all and the profile is innocent --
    which is the same streaming gate that stopped H3's auto turret.

    Repaletting an existing placement needs no block growth; only the palette may have
    to gain one entry."""
    lay = HP._MAP_WEAPONS[GAME]
    scnr = HP._scnr_base(m)
    woff, wes = lay['weapons']
    poff, pes = lay['palette']
    wn, wbase = m.i32(scnr + woff), HP._block_base(m, scnr + woff)
    pc, pbase = max(0, m.i32(scnr + poff)), HP._block_base(m, scnr + poff)

    names = []
    for i in range(pc):
        nm = HP._tag_name_by_id(m, m.u32(pbase + i * pes + lay['pal_id_at']))
        names.append(str(nm) if nm else '')
    rocket = next((i for i, nm in enumerate(names) if 'rocket_launcher' in nm.lower()), None)
    if rocket is None:
        print('  !! rocket launcher is not in the weapon palette; using the shotgun')
        rocket = next((i for i, nm in enumerate(names) if 'shotgun' in nm.lower()), None)
    if rocket is None:
        print('  !! neither rocket launcher nor shotgun in the palette -- skipping')
        return None

    carbines = []
    for i in range(max(0, wn)):
        e = wbase + i * wes
        pi = struct.unpack_from('<h', m.data, e + lay['palette_index'])[0]
        if 0 <= pi < len(names) and 'carbine' in names[pi].lower():
            pos = struct.unpack_from('<fff', m.data, e + HP._EQ_POS)
            att = struct.unpack_from('<H', m.data, e + HP._EQ_ATTACH)[0]
            fl = struct.unpack_from('<I', m.data, e + HP._EQ_FLAGS)[0]
            carbines.append((i, pos, att, fl))
    if not carbines:
        print('  !! no carbine placements found')
        return None

    carbines.sort(key=lambda c: math.dist(c[1], REAL))
    print('  %d carbine placement(s); nearest to the real start:' % len(carbines))
    for i, pos, att, fl in carbines[:5]:
        print('    [%3d] (%8.1f,%8.1f,%6.1f) mask 0x%04X flags 0x%X  %.0f units'
              % (i, pos[0], pos[1], pos[2], att, fl, math.dist(pos, REAL)))

    for i, _pos, _att, fl in carbines:
        e = wbase + i * wes
        struct.pack_into('<h', m.data, e + lay['palette_index'], rocket)
        # clear Not Automatically / Never Placed so it spawns at load
        struct.pack_into('<I', m.data, e + HP._EQ_FLAGS,
                         fl & ~(HP._PLACE_NOT_AUTO | HP._PLACE_NEVER))
    print('  every carbine -> palette[%d] %s' % (rocket, names[rocket].rsplit('\\', 1)[-1]))
    return carbines[0]


def equipment_at(m, spot, label, radius=2.0):
    """Ring the already-appended equipment around a given point."""
    lay = HP._MAP_EQUIPMENT[GAME]
    scnr = HP._scnr_base(m)
    io, ies = lay['items']
    n, base = m.i32(scnr + io), HP._block_base(m, scnr + io)
    pos, mask = spot[1], spot[2]
    count = min(5, n)
    for k, i in enumerate(range(n - count, n)):
        e = base + i * ies
        ang = k * (2 * math.pi / count)
        struct.pack_into('<fff', m.data, e + HP._EQ_POS,
                         pos[0] + radius * math.cos(ang),
                         pos[1] + radius * math.sin(ang), pos[2])
        struct.pack_into('<H', m.data, e + HP._EQ_ATTACH, mask)
    print('  %d equipment moved to the %s carbine at (%.1f, %.1f, %.1f), r=%.1f, mask 0x%04X'
          % (count, label, pos[0], pos[1], pos[2], radius, mask))


# scnr Squads: name @0x0, Team @0x24. Each squad holds Designer Cells @0x54 and
# Templated Cells @0x60 (both 0x84 bytes), and a cell carries its loadout as one-entry
# BLOCKS of a 16-byte tagRef: Initial Weapon @0x20, Secondary @0x2C, Equipment @0x38.
_SQUADS = (0x3B8, 0x6C)
_SQ_NAME, _SQ_TEAM = 0x0, 0x24
_CELL_BLOCKS = ((0x54, 0x84), (0x60, 0x84))
# A cell does NOT hold tagRefs. Character Type / Initial Weapon are one-entry tagblocks
# whose payload is an int16 INDEX at +0xC into a scenario palette: Character Palette
# @0x3E8 for the character, and the same Weapon Palette @0x13C the placements use for
# the weapon. Reading them as tagRefs produced a census of cubemaps and shaders.
_CHAR_PALETTE = (0x3E8, 0x10)
_CELL_IDX_AT = 0xC
_CELL_CHARACTER = 0x14
_CELL_PRIMARY, _CELL_SECONDARY = 0x20, 0x2C
# Every sc150 squad reports team 0 (Default) -- the team comes from the character tag,
# not the squad -- so the squad's Team field cannot pick out friendlies. The character
# tag name can.
_FRIENDLY_CHARS = ('marine', 'odst', 'buck', 'dutch', 'romeo', 'mickey', 'dare',
                   'johnson', 'civilian', 'police')


def _palette_names(m, off, esize):
    """Tag names of a scenario palette, indexed as the cells index it."""
    scnr = HP._scnr_base(m)
    n, base = m.i32(scnr + off), HP._block_base(m, scnr + off)
    out = []
    for i in range(max(0, n)) if base else []:
        nm = HP._tag_name_by_id(m, m.u32(base + i * esize + 0xC))
        out.append(str(nm) if nm else '')
    return out


def _cell_char_name(m, ce, chars):
    """Name of the character a squad cell spawns, or ''."""
    n, base = m.i32(ce + _CELL_CHARACTER), HP._block_base(m, ce + _CELL_CHARACTER)
    if not base or n <= 0:
        return ''
    idx = struct.unpack_from('<h', m.data, base + _CELL_IDX_AT)[0]
    return chars[idx] if 0 <= idx < len(chars) else ''


def arm_friendlies(m, path):
    """Give every friendly squad's cells the named weapon.

    An NPC gets its weapon from a completely different place than the player does --
    the squad cell's Initial Weapon, not a starting profile -- so if the tag is alive
    on this map a marine will visibly carry it. If nobody carries it either, the tag
    is dead on sc150 the way the Battle Rifle is dead ODST-wide, and no amount of
    fixing the player's loadout path will ever produce it."""
    scnr = HP._scnr_base(m)
    chars = _palette_names(m, *_CHAR_PALETTE)
    weaps = _palette_names(m, *HP._MAP_WEAPONS[GAME]['palette'])
    widx = next((i for i, nm in enumerate(weaps) if path.rsplit('\\', 1)[-1] in nm.lower()),
                None)
    if widx is None:
        print('  !! %s is not in the Weapon Palette' % path.rsplit('\\', 1)[-1])
        return
    print('  weapon palette index %d = %s' % (widx, weaps[widx].rsplit('\\', 1)[-1]))
    soff, ses = _SQUADS
    n, base = m.i32(scnr + soff), HP._block_base(m, scnr + soff)
    if not base or n <= 0:
        print('  !! no squads')
        return
    census, armed, cells, skipped = {}, set(), 0, 0
    for i in range(n):
        se = base + i * ses
        sname = bytes(m.data[se:se + 32]).split(b'\0')[0].decode('latin-1')
        for coff, ces in _CELL_BLOCKS:
            cn, cbase = m.i32(se + coff), HP._block_base(m, se + coff)
            if not cbase or cn <= 0:
                continue
            for c in range(cn):
                ce = cbase + c * ces
                cname = _cell_char_name(m, ce, chars)
                short = cname.rsplit('\\', 1)[-1] or '(none)'
                census[short] = census.get(short, 0) + 1
                if not any(k in cname.lower() for k in _FRIENDLY_CHARS):
                    continue
                # primary only: leaving the secondary alone keeps the change legible
                wn, wbase = m.i32(ce + _CELL_PRIMARY), HP._block_base(m, ce + _CELL_PRIMARY)
                if not wbase or wn <= 0:
                    skipped += 1
                    continue
                for k in range(wn):
                    struct.pack_into('<h', m.data, wbase + k * 0x10 + _CELL_IDX_AT, widx)
                cells += 1
                armed.add(sname)
    print('  characters on this map:')
    for nm, c in sorted(census.items(), key=lambda kv: -kv[1]):
        friendly = any(k in nm.lower() for k in _FRIENDLY_CHARS)
        print('    %-34s %4d %s' % (nm, c, 'FRIENDLY' if friendly else ''))
    print('  armed %d squad(s), %d cell slot(s) -> %s%s'
          % (len(armed), cells, path.rsplit('\\', 1)[-1],
             '  (%d friendly cell(s) have no weapon slot)' % skipped if skipped else ''))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--profiles', default='all',
                    help='"all", "none", or a comma list like 0,4,8,12')
    ap.add_argument('--primary', help='weapon basename for the primary slot')
    ap.add_argument('--secondary', help='weapon basename for the secondary slot')
    ap.add_argument('--no-equipment', action='store_true')
    ap.add_argument('--carbines', action='store_true',
                    help='repalette every carbine to a rocket launcher and put the '
                         'equipment on the carbine nearest the real start')
    ap.add_argument('--arm-friendlies', action='store_true',
                    help='give every friendly squad --friendly-weapon')
    ap.add_argument('--friendly-weapon', default='rocket_launcher',
                    help='what friendlies carry; defaults to a weapon sc150 never '
                         'places or carries, so it stays a control on the player test')
    ap.add_argument('--ring', type=float, default=2.0,
                    help='equipment ring radius in world units (default 2.0)')
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
    global PRIMARY, SECONDARY
    for name, slot in ((a.primary, 'PRIMARY'), (a.secondary, 'SECONDARY')):
        if not name:
            continue
        path = _palette_path(m, name)
        if not path:
            raise SystemExit('%r is not in this map\'s Weapon Palette' % name)
        globals()[slot] = path
        print('  %s slot -> %s' % (slot.lower(), path))
    if a.profiles != 'none':
        which = 'all' if a.profiles == 'all' else [int(x) for x in a.profiles.split(',')]
        write_weapons(m, reg, which)
    if not a.no_equipment:
        write_equipment(m)
    spot = carbine_test(m) if a.carbines else None
    if spot and not a.no_equipment:
        equipment_at(m, spot, 'nearest', a.ring)
    if a.arm_friendlies:
        fw = _palette_path(m, a.friendly_weapon) or a.friendly_weapon
        arm_friendlies(m, fw)
    m.save(MAP)
    print('\nwritten. Load Kikowani Station and report:')
    if a.carbines:
        print('  - is there a ROCKET LAUNCHER where the carbine near the start was?')
        print('  - equipment ringed around that same spot?')
    else:
        print('  - rocket launcher + shotgun in hand at the start?')
        print('  - a ring of equipment where you are standing?')
    print('undo with:  python odst_kikowani_test.py --restore')
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
